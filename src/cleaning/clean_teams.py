"""
Limpieza e ingesta: teams (EuroLeague / EuroCup)
Optimizado con comando COPY para carga instantánea y alineación estricta 1:1.
"""
import os
import csv
from io import StringIO
import pandas as pd
from sqlalchemy import create_engine

LIGA        = os.environ.get("LIGA", "euroleague")
DB_USER     = os.environ.get("POSTGRES_USER", "usuario_basket")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "bskt26")
DB_DB       = os.environ.get("POSTGRES_DB", "basket_db")

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

print(f"🔄 [BULK COPY] Teams: {LIGA.upper()}")
df = pd.read_csv(f"data/{LIGA}_teams.csv")

df.columns = df.columns.str.strip()

def parse_minutes(val):
    try:
        partes = str(val).split(":")
        return int(partes[0]) + int(partes[1]) / 60
    except:
        return 0.0

df["minutes_num"] = df["minutes"].apply(parse_minutes)

# Procesar porcentajes base del CSV
pct_cols = ["two_points_percentage", "three_points_percentage", "free_throws_percentage"]
for col in pct_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0).clip(0, 1)

# Variables analíticas requeridas para los cálculos del grupo
fga_pg = df["two_points_attempted_per_game"] + df["three_points_attempted_per_game"]
denom_reb = df["defensive_rebounds_per_game"] + df["offensive_rebounds_per_game"]

df["rebote_ratio"] = (df["offensive_rebounds_per_game"] / (denom_reb + 1e-9)).round(3).fillna(0.0)
df["efg_pct"] = ((df["two_points_made_per_game"] + 1.5 * df["three_points_made_per_game"]) / (fga_pg + 1e-9)).round(3).fillna(0.0)
df["ts_pct"] = (df["points_per_game"] / (2 * (fga_pg + 0.44 * df["free_throws_attempted_per_game"]) + 1e-9)).round(3).fillna(0.0)

# Control matemático estricto para evitar desbordamiento numérico en Postgres
def calcular_ast_to_ratio(row):
    to = row["turnovers_per_game"]
    ast = row["assists_per_game"]
    if to > 0:
        val = round(ast / to, 3)
        return val if val < 9999.0 else 9999.0
    return round(float(ast), 3) if ast < 9999.0 else 9999.0

df["ast_to_ratio"] = df.apply(calcular_ast_to_ratio, axis=1).fillna(0.0)

df["competition"] = "EuroLeague" if LIGA == "euroleague" else "EuroCup"

# Casteo estricto de enteros para que no pasen decimales ".0" de texto
cols_enteras_teams = ["games_played", "games_started", "points", "two_points_made", "two_points_attempted", 
                      "three_points_made", "three_points_attempted", "free_throws_made", "free_throws_attempted", 
                      "offensive_rebounds", "defensive_rebounds", "total_rebounds", "assists", "steals", 
                      "turnovers", "blocks_favour", "blocks_against", "fouls_committed", "fouls_received", 
                      "valuation", "plus_minus"]

for col in cols_enteras_teams:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

# ── 🎯 ORDENAMIENTO ABSOLUTO SEGÚN POSTGRES ──
with engine.connect() as conn:
    cols_db = pd.read_sql("SELECT * FROM season_teams LIMIT 0", conn).columns
df = df[[col for col in cols_db if col in df.columns]]
# ─────────────────────────────────────────────

pg_bulk_insert(df, "season_teams", engine)
print(f"✅ Inyectadas {len(df)} filas en 'season_teams' ({LIGA})")