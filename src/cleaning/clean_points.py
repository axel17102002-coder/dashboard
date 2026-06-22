"""
Limpieza e ingesta: points (EuroLeague / EuroCup)
Optimizado con comando COPY para transmisión masiva en segundos.
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

print(f"🔄 [BULK COPY] Points masivo: {LIGA.upper()}")
df = pd.read_csv(f"data/{LIGA}_points.csv")

tiro_libre_mask = df["action_id"].isin(["FTM", "FTA"])
df.loc[tiro_libre_mask & df["zone"].isna(), "zone"] = "Free Throw"
df["zone"] = df["zone"].fillna("Unknown")

bool_cols = ["fastbreak", "second_chance", "points_off_turnover"]
df[bool_cols] = df[bool_cols].fillna(0).astype(int)

def tipo_tiro(action_id):
    if action_id in ["FTM", "FTA"]: return "free_throw"
    elif action_id in ["2FGM", "2FGA"]: return "two_point"
    elif action_id in ["3FGM", "3FGA"]: return "three_point"
    else: return "other"

df["shot_type"] = df["action_id"].apply(tipo_tiro)
df["made"] = df["action_id"].str.endswith("M").astype(int)
df["competition"] = "EuroLeague" if LIGA == "euroleague" else "EuroCup"

pg_load(df, "game_points", engine)
print(f"✅ Inyectadas {len(df)} filas en 'game_points' ({LIGA})")