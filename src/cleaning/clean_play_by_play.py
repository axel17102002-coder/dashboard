"""
Limpieza e ingesta: play_by_play (EuroLeague / EuroCup)
Dataset grande (~1M+ filas). Foco en tipos, plays sin jugador y consistencia.
"""
import os
import pandas as pd
from sqlalchemy import create_engine

liga        = os.environ.get("LIGA", "euroleague")
DB_USER     = os.environ.get("POSTGRES_USER", "usuario_basket")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "bskt26")
DB_DB       = os.environ.get("POSTGRES_DB", "basket_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@db:5432/{DB_DB}"
engine = create_engine(DATABASE_URL)

print(f"🔄 Procesando Play-by-Play para: {liga.upper()}")
df = pd.read_csv(f"data/{liga}_play_by_play.csv")
print(f"Original: {df.shape}")

# ── 1. Plays sin jugador asignado ────────────────────────────────────────────
df["player_id"] = df["player_id"].fillna("TEAM")
df["player"]    = df["player"].fillna("TEAM")
df["dorsal"]    = df["dorsal"].fillna("-")

# ── 2. Plays sin team_id (jugadas de árbitro/administrativas) ────────────────
df["team_id"] = df["team_id"].fillna("OFFICIAL")

# ── 3. Columna 'comment' y 'play_info': texto libre, rellenar con vacío ──────
df["comment"]   = df["comment"].fillna("") if "comment"   in df.columns else ""
df["play_info"] = df["play_info"].fillna("") if "play_info" in df.columns else ""

# ── 4. Tipo correcto para quarter ───────────────────────────────────────────
# Quarter puede venir como entero (1,2,3,4) o como string ('q1','q2','E1'...)
# 'q1'→1, 'q4'→4, 'E1'→5 (primer tiempo extra), 'E2'→6, etc.
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

print(f"Valores únicos de quarter antes: {df['quarter'].unique()[:10]}")
df["quarter"] = df["quarter"].apply(parse_quarter)
print(f"Valores únicos de quarter después: {sorted(df['quarter'].dropna().unique())}")
df["is_overtime"] = df["quarter"] > 4

# ── 5. Validación: número de jugada debe ser creciente dentro de cada partido ─
problemas = (
    df.sort_values(["game_id","number_of_play"])
    .groupby("game_id")["number_of_play"]
    .apply(lambda x: (x.diff().dropna() < 0).any())
)
print(f"Partidos con orden de jugadas inconsistente: {problemas.sum()}")

# ── 6. Columna auxiliar: minuto como número ──────────────────────────────────
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

# ── 7. Ingesta a PostgreSQL ───────────────────────────────────────────────────
df["competition"] = "EuroLeague" if liga == "euroleague" else "EuroCup"
df.to_sql("play_by_play", con=engine, if_exists="append", index=False, chunksize=5000, method="multi")
print(f"✅ Inyectadas {len(df)} filas en 'play_by_play' ({liga})")