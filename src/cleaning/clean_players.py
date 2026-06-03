"""
Limpieza e ingesta: players (EuroLeague / EuroCup)
Datos completamente limpios (0 nulos). Foco en tipos, rangos y métricas derivadas.
"""
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

LIGA        = os.environ.get("LIGA", "euroleague")
DB_USER     = os.environ.get("POSTGRES_USER", "usuario_basket")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "bskt26")
DB_DB       = os.environ.get("POSTGRES_DB", "basket_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@db:5432/{DB_DB}"
engine = create_engine(DATABASE_URL)

print(f"🔄 Procesando Players para: {LIGA.upper()}")
df = pd.read_csv(f"data/{LIGA}_players.csv")
print(f"Original: {df.shape}")

# ── 1. Convertir minutes acumulados "MM:SS" → float ─────────────────────────
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

# ── 2. Porcentajes: reemplazar NaN por 0 si no hubo intentos ────────────────
# (puede ocurrir si jugador no intentó ningún tiro de ese tipo)
pct_cols = ["two_points_percentage", "three_points_percentage", "free_throws_percentage"]
for col in pct_cols:
    df[col] = df[col].fillna(0.0)
    # Rango válido: 0 a 1
    df[col] = df[col].clip(0, 1)

# ── 3. Validación: puntos deben cuadrar con tiros ───────────────────────────
df["puntos_calculados"] = (
    df["two_points_made"] * 2 +
    df["three_points_made"] * 3 +
    df["free_throws_made"] * 1
)
inconsistentes = df[df["puntos_calculados"] != df["points"]]
print(f"Jugadores con puntos inconsistentes: {len(inconsistentes)}")
df = df.drop(columns=["puntos_calculados"])

# ── 4. Filtrar jugadores con 0 minutos jugados ───────────────────────────────
sin_minutos = df[df["minutes_num"] == 0]
print(f"Jugadores con 0 minutos: {len(sin_minutos)}")
df = df[df["minutes_num"] > 0].copy()

# ── 5. Columna auxiliar: perfil de jugador por rol ofensivo ─────────────────
def perfil(row):
    if row["three_points_attempted_per_game"] >= 3:
        return "perimetral"
    elif row["two_points_attempted_per_game"] >= 4:
        return "interior"
    else:
        return "mixto"

df["perfil_ofensivo"] = df.apply(perfil, axis=1)

# ── 6. CU-02: Métricas derivadas avanzadas ──────────────────────────────────
fga = df["two_points_attempted"] + df["three_points_attempted"]

df["efg_pct"] = (
    (df["two_points_made"] + 1.5 * df["three_points_made"]) /
    (fga + 1e-9)
).round(3)

df["ts_pct"] = (
    df["points"] /
    (2 * (fga + 0.44 * df["free_throws_attempted"]) + 1e-9)
).round(3)

df["ast_to_ratio"] = (
    df["assists"] / (df["turnovers"] + 1e-9)
).round(3)

# USG% simplificado (sin contexto de equipo): tasa de posesiones usadas por minuto
df["usg_pct"] = (
    (fga + 0.44 * df["free_throws_attempted"] + df["turnovers"]) /
    (df["minutes_num"] + 1e-9)
).round(3)

# ── 7. Ingesta a PostgreSQL ──────────────────────────────────────────────────
df["competition"] = "EuroLeague" if LIGA == "euroleague" else "EuroCup"
df.to_sql("season_players", con=engine, if_exists="append", index=False)
print(f"✅ Inyectadas {len(df)} filas en 'season_players' ({LIGA})")
