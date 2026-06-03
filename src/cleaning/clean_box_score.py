"""
Módulo de Limpieza e Ingesta: Box Scores (EuroLeague / EuroCup)
Calcula métricas derivadas requeridas (PIR) y carga directamente a PostgreSQL.
"""
import os
import pandas as pd
from sqlalchemy import create_engine

# 1. Leer variables de entorno (En Docker el host es 'db')
LIGA = os.environ.get("LIGA", "euroleague")
DB_USER = os.environ.get("POSTGRES_USER", "usuario_basket")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "bskt26")
DB_DB = os.environ.get("POSTGRES_DB", "basket_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@db:5432/{DB_DB}"
engine = create_engine(DATABASE_URL)

# Cargar el archivo según la competición activa en el pipeline
print(f"🔄 Procesando Box Scores para: {LIGA.upper()}")
df = pd.read_csv(f"data/{LIGA}_box_score.csv")

# ── 1. Filtrar jugadores activos ───────────────────────────────────────────
df = df[df["is_playing"] == 1].copy()

# ── 2. Convertir minutos "MM:SS" a flotante decimal ─────────────────────────
def parse_minutes(val):
    try:
        partes = str(val).split(":")
        return int(partes[0]) + int(partes[1]) / 60
    except:
        return 0.0

df["minutes_num"] = df["minutes"].apply(parse_minutes)

# ── 3. Tipos lógicos y capeo de anomalías ───────────────────────────────────
df["is_starter"] = df["is_starter"].astype(bool)
df["is_playing"] = df["is_playing"].astype(bool)

# ── 4. Verificación de rangos lógicos y auditoría de anomalías ──────────────
anomalias = []

# Regla FIBA: Máximo 5 faltas
mask_faltas = df["fouls_committed"] > 5
if mask_faltas.any():
    print(f"  ⚠️  {mask_faltas.sum()} filas con fouls_committed > 5 → se capean a 5")
    df_anomalo = df[mask_faltas][["game_player_id", "game_id", "player", "fouls_committed"]].copy()
    df_anomalo["motivo"] = "fouls_committed > 5"
    anomalias.append(df_anomalo)
    df.loc[mask_faltas, "fouls_committed"] = 5

# Regla lógica: Puntos no pueden ser negativos
mask_pts = df["points"] < 0
if mask_pts.any():
    print(f"  ⚠️  {mask_pts.sum()} filas con points < 0 → se capean a 0")
    df_anomalo = df[mask_pts][["game_player_id", "game_id", "player", "points"]].copy()
    df_anomalo["motivo"] = "points < 0"
    anomalias.append(df_anomalo)
    df.loc[mask_pts, "points"] = 0

# Si se encontraron anomalías, se guardan en una tabla dedicada de la BD
if anomalias:
    df_todas_anomalias = pd.concat(anomalias, ignore_index=True)
    df_todas_anomalias["competition"] = "EuroLeague" if LIGA == "euroleague" else "EuroCup"
    # Guardamos en la tabla 'audit_anomalias'
    df_todas_anomalias.to_sql("audit_anomalias", con=engine, if_exists="append", index=False)

# ── 5. CU-02: Cálculo de Métrica Derivada: PIR (Valoración) ─────────────────
# Fórmula Oficial Euroliga: (Pts + Reb + Ast + Stl + Blk + Fouls Rec) - (Tiros Fallados + FT Fallados + TO + Blk Ag)
tiros_fallados = (df["two_points_attempted"] - df["two_points_made"]) + (df["three_points_attempted"] - df["three_points_made"])
ft_fallados = df["free_throws_attempted"] - df["free_throws_made"]

df["pir_calculado"] = (
    df["points"] + df["total_rebounds"] + df["assists"] + df["steals"] + df["blocks_favour"] + df["fouls_received"]
) - (tiros_fallados + ft_fallados + df["turnovers"] + df["blocks_against"])


# ── 6. Unificación: Columna de Identificación de Competencia ────────────────
df["competition"] = "EuroLeague" if LIGA == "euroleague" else "EuroCup"

# ── 7. Ingesta a la Base de Datos con SQLAlchemy ────────────────────────────
# Usamos if_exists='append' para que EuroLeague y EuroCup convivan en la misma tabla
df.to_sql("game_box_scores", con=engine, if_exists="append", index=False)
print(f"✅ Inyectadas {len(df)} filas en la tabla 'game_box_scores' ({LIGA})")