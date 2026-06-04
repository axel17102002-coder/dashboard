"""
Módulo de Limpieza e Ingesta: Box Scores (EuroLeague / EuroCup)
Optimizado con comando COPY de PostgreSQL y blindado contra texto en columnas numéricas.
"""
import os
import csv
from io import StringIO
import pandas as pd
from sqlalchemy import create_engine

LIGA = os.environ.get("LIGA", "euroleague")
DB_USER = os.environ.get("POSTGRES_USER", "usuario_basket")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "bskt26")
DB_DB = os.environ.get("POSTGRES_DB", "basket_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@db:5432/{DB_DB}"
engine = create_engine(DATABASE_URL)

def pg_bulk_insert(df, table_name, engine):
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, na_rep='NULL', quoting=csv.QUOTE_MINIMAL)
    buffer.seek(0)
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            columnas = ', '.join([f'"{col}"' for col in df.columns])
            sql = f'COPY "{table_name}" ({columnas}) FROM STDIN WITH CSV NULL AS \'NULL\''
            cursor.copy_expert(sql, buffer)
        raw_conn.commit()
    finally:
        raw_conn.close()

print(f"🔄 [BULK COPY] Box Scores: {LIGA.upper()}")
df = pd.read_csv(f"data/{LIGA}_box_score.csv")

# ── BLINDAJE CONTRA FILAS DE TOTALES ───────────────────────────────────────
# Eliminamos cualquier fila donde el dorsal o el nombre sea "TOTAL" o similar
if "dorsal" in df.columns:
    df = df[df["dorsal"].astype(str).str.upper() != "TOTAL"]
    # Limpiamos strings raros para que Postgres no falle si espera números
    df["dorsal"] = pd.to_numeric(df["dorsal"], errors='coerce').fillna(0).astype(int)

df = df[df["is_playing"] == 1].copy()

def parse_minutes(val):
    try:
        partes = str(val).split(":")
        return int(partes[0]) + int(partes[1]) / 60
    except:
        return 0.0

df["minutes_num"] = df["minutes"].apply(parse_minutes)
df["is_starter"] = df["is_starter"].astype(bool)
df["is_playing"] = df["is_playing"].astype(bool)

anomalias = []
mask_faltas = df["fouls_committed"] > 5
if mask_faltas.any():
    df_anomalo = df[mask_faltas][["game_player_id", "game_id", "player", "fouls_committed"]].copy()
    df_anomalo["motivo"] = "fouls_committed > 5"
    anomalias.append(df_anomalo)
    df.loc[mask_faltas, "fouls_committed"] = 5

mask_pts = df["points"] < 0
if mask_pts.any():
    df_anomalo = df[mask_pts][["game_player_id", "game_id", "player", "points"]].copy()
    df_anomalo["motivo"] = "points < 0"
    anomalias.append(df_anomalo)
    df.loc[mask_pts, "points"] = 0

if anomalias:
    df_todas_anomalias = pd.concat(anomalias, ignore_index=True)
    df_todas_anomalias["competition"] = "EuroLeague" if LIGA == "euroleague" else "EuroCup"
    pg_bulk_insert(df_todas_anomalias, "audit_anomalias", engine)

tiros_fallados = (df["two_points_attempted"] - df["two_points_made"]) + (df["three_points_attempted"] - df["three_points_made"])
ft_fallados = df["free_throws_attempted"] - df["free_throws_made"]
df["pir_calculado"] = (df["points"] + df["total_rebounds"] + df["assists"] + df["steals"] + df["blocks_favour"] + df["fouls_received"]) - (tiros_fallados + ft_fallados + df["turnovers"] + df["blocks_against"])

df["competition"] = "EuroLeague" if LIGA == "euroleague" else "EuroCup"

# Alineamos solo con las columnas que Postgres realmente espera
with engine.connect() as conn:
    cols_db = pd.read_sql(f"SELECT * FROM game_box_scores LIMIT 0", conn).columns
df = df[[col for col in df.columns if col in cols_db]]

pg_bulk_insert(df, "game_box_scores", engine)
print(f"✅ Inyectadas {len(df)} filas en 'game_box_scores' ({LIGA})")