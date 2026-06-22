"""
Limpieza e ingesta: players (EuroLeague / EuroCup)
Optimizado con comando COPY y blindado contra desbordamientos numéricos.
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

from ingest import pg_load

print(f"🔄 [BULK COPY] Players: {LIGA.upper()}")
df = pd.read_csv(f"data/{LIGA}_players.csv")

def parse_minutes(val):
    try:
        s = str(val)
        if ":" in s:
            partes = s.split(":")
            return int(partes[0]) + int(partes[1]) / 60
        return float(val)
    except:
        return 0.0

df["minutes_num"] = df["minutes"].apply(parse_minutes)

pct_cols = ["two_points_percentage", "three_points_percentage", "free_throws_percentage"]
for col in pct_cols:
    if col in df.columns:
        df[col] = df[col].fillna(0.0).clip(0, 1)

df = df[df["minutes_num"] > 0].copy()

def perfil(row):
    if row["three_points_attempted_per_game"] >= 3: return "perimetral"
    elif row["two_points_attempted_per_game"] >= 4: return "interior"
    else: return "mixto"

df["perfil_ofensivo"] = df.apply(perfil, axis=1)

fga = df["two_points_attempted"] + df["three_points_attempted"]
df["efg_pct"] = ((df["two_points_made"] + 1.5 * df["three_points_made"]) / (fga + 1e-9)).round(3)
df["ts_pct"] = (df["points"] / (2 * (fga + 0.44 * df["free_throws_attempted"]) + 1e-9)).round(3)

# ── BLINDAJE MATEMÁTICO: Evitar los mil millones si turnovers es 0 ──
df["ast_to_ratio"] = df.apply(
    lambda r: round(r["assists"] / r["turnovers"], 3) if r["turnovers"] > 0 else float(r["assists"]), axis=1
)

df["usg_pct"] = ((fga + 0.44 * df["free_throws_attempted"] + df["turnovers"]) / (df["minutes_num"] + 1e-9)).round(3)

df["competition"] = "EuroLeague" if LIGA == "euroleague" else "EuroCup"

cols_enteras = ["games_played", "games_started", "points", "two_points_made", "two_points_attempted", 
                "three_points_made", "three_points_attempted", "free_throws_made", "free_throws_attempted", 
                "offensive_rebounds", "defensive_rebounds", "total_rebounds", "assists", "steals", 
                "turnovers", "blocks_favour", "blocks_against", "fouls_committed", "fouls_received", 
                "valuation", "plus_minus"]

for col in cols_enteras:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

pg_load(df, "season_players", engine)
print(f"✅ Inyectadas {len(df)} filas en 'season_players' ({LIGA})")