"""
Limpieza e ingesta: play_by_play (EuroLeague / EuroCup)
Optimizado al extremo con streaming COPY de PostgreSQL. Procesa 1M de filas en segundos.
"""
import os
import csv
from io import StringIO
import pandas as pd
from sqlalchemy import create_engine

liga        = os.environ.get("LIGA", "euroleague")
DB_USER     = os.environ.get("POSTGRES_USER", "usuario_basket")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "bskt26")
DB_DB       = os.environ.get("POSTGRES_DB", "basket_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@db:5432/{DB_DB}"
engine = create_engine(DATABASE_URL)

from ingest import pg_load

print(f"🔄 [BULK COPY] Play-by-Play masivo: {liga.upper()}")
df = pd.read_csv(f"data/{liga}_play_by_play.csv")

df["player_id"] = df["player_id"].fillna("TEAM")
df["player"]    = df["player"].fillna("TEAM")

if "dorsal" in df.columns:
    df["dorsal"] = pd.to_numeric(df["dorsal"], errors='coerce').fillna(0).astype(int)

#casteo para que los puntos pasen como enteros limpios sin el punto decimal:
if "points_a" in df.columns:
    df["points_a"] = pd.to_numeric(df["points_a"], errors='coerce').fillna(0).astype(int)
if "points_b" in df.columns:
    df["points_b"] = pd.to_numeric(df["points_b"], errors='coerce').fillna(0).astype(int)

df["dorsal"]    = df["dorsal"].fillna("-")
df["team_id"]   = df["team_id"].fillna("OFFICIAL")
df["comment"]   = df["comment"].fillna("") if "comment"   in df.columns else ""
df["play_info"] = df["play_info"].fillna("") if "play_info" in df.columns else ""

def parse_quarter(val):
    s = str(val).strip().lower()
    if s.startswith("q"):
        try: return int(s[1:])
        except: pass
    if s.startswith("e"):
        try: return 4 + int(s[1:])
        except: pass
    try: return int(float(s))
    except: return None

df["quarter"] = df["quarter"].apply(parse_quarter)
df["is_overtime"] = df["quarter"] > 4

def parse_marker(val):
    try:
        if ":" in str(val):
            partes = str(val).split(":")
            return int(partes[0]) + int(partes[1]) / 60
        return float(val)
    except:
        return None

if "marker_time" in df.columns:
    df["marker_time_num"] = df["marker_time"].apply(parse_marker)

df["competition"] = "EuroLeague" if liga == "euroleague" else "EuroCup"

pg_load(df, "play_by_play", engine)
print(f"✅ Inyectadas {len(df)} filas en 'play_by_play' ({liga})")