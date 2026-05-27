"""
Limpieza: euroleague_players.csv
Datos completamente limpios (0 nulos). Foco en tipos, rangos y columnas útiles.
"""
import pandas as pd
import numpy as np

df = pd.read_csv("data/euroleague_players.csv")
print(f"Original: {df.shape}")

# ── 1. Convertir minutes acumulados "MM:SS" → float ─────────────────────────
def parse_minutes(val):
    try:
        partes = str(val).split(":")
        return int(partes[0]) + int(partes[1]) / 60
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
if len(inconsistentes) > 0:
    inconsistentes[["player","season_code","points","puntos_calculados"]].to_csv(
        "data/clean/players_puntos_inconsistentes.csv", index=False
    )
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

# ── 6. Resultado ────────────────────────────────────────────────────────────
print(f"\nNulos restantes:\n{df.isnull().sum()[df.isnull().sum() > 0]}")
print(f"Duplicados: {df.duplicated().sum()}")
print(f"Filas finales: {df.shape[0]}")
df.to_csv("data/clean/euroleague_players_clean.csv", index=False)
print("✅ Guardado en data/clean/euroleague_players_clean.csv")
