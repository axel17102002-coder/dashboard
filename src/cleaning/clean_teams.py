"""
Limpieza e ingesta: teams (EuroLeague / EuroCup)
Datos completamente limpios. Foco en tipos, porcentajes y métricas derivadas.
"""
import os
import pandas as pd
from sqlalchemy import create_engine

LIGA        = os.environ.get("LIGA", "euroleague")
DB_USER     = os.environ.get("POSTGRES_USER", "usuario_basket")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "bskt26")
DB_DB       = os.environ.get("POSTGRES_DB", "basket_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@db:5432/{DB_DB}"
engine = create_engine(DATABASE_URL)

print(f"🔄 Procesando Teams para: {LIGA.upper()}")
df = pd.read_csv(f"data/{LIGA}_teams.csv")
print(f"Original: {df.shape}")

# ── 1. Convertir minutes acumulados "MM:SS" → float ─────────────────────────
def parse_minutes(val):
    try:
        partes = str(val).split(":")
        return int(partes[0]) + int(partes[1]) / 60
    except:
        return 0.0

df["minutes_num"] = df["minutes"].apply(parse_minutes)

# ── 2. Porcentajes en rango válido ──────────────────────────────────────────
pct_cols = ["two_points_percentage", "three_points_percentage", "free_throws_percentage"]
for col in pct_cols:
    df[col] = df[col].clip(0, 1)

# ── 3. Validación: puntos por partido deben ser razonables ──────────────────
fuera_de_rango = df[~df["points_per_game"].between(50, 120)]
print(f"Equipos con puntos/partido fuera de rango (50-120): {len(fuera_de_rango)}")
if len(fuera_de_rango) > 0:
    print(fuera_de_rango[["team_id","season_code","points_per_game"]])

# ── 4. Métricas derivadas ───────────────────────────────────────────────────
fga_pg = df["two_points_attempted_per_game"] + df["three_points_attempted_per_game"]

df["rebote_ratio"] = (
    df["offensive_rebounds_per_game"] /
    (df["defensive_rebounds_per_game"] + df["offensive_rebounds_per_game"] + 1e-9)
).round(3)

df["efg_pct"] = (
    (df["two_points_made_per_game"] + 1.5 * df["three_points_made_per_game"]) /
    (fga_pg + 1e-9)
).round(3)

df["ts_pct"] = (
    df["points_per_game"] /
    (2 * (fga_pg + 0.44 * df["free_throws_attempted_per_game"]) + 1e-9)
).round(3)

df["ast_to_ratio"] = (
    df["assists_per_game"] / (df["turnovers_per_game"] + 1e-9)
).round(3)

# ── 5. Ingesta a PostgreSQL ──────────────────────────────────────────────────
df["competition"] = "EuroLeague" if LIGA == "euroleague" else "EuroCup"
df.to_sql("season_teams", con=engine, if_exists="append", index=False)
print(f"✅ Inyectadas {len(df)} filas en 'season_teams' ({LIGA})")
