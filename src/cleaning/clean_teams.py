"""
Limpieza: euroleague_teams.csv
Datos completamente limpios. Foco en tipos, porcentajes y columnas derivadas.
"""
import pandas as pd

df = pd.read_csv("data/euroleague_teams.csv")
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

# ── 4. Columnas auxiliares ──────────────────────────────────────────────────
# Ratio ofensivo/defensivo de rebotes
df["rebote_ratio"] = (
    df["offensive_rebounds_per_game"] /
    (df["defensive_rebounds_per_game"] + df["offensive_rebounds_per_game"] + 1e-9)
).round(3)

# Eficiencia de tiro ponderada (eFG%)
df["efg_pct"] = (
    (df["two_points_made_per_game"] + 1.5 * df["three_points_made_per_game"]) /
    (df["two_points_attempted_per_game"] + df["three_points_attempted_per_game"] + 1e-9)
).round(3)

# ── 5. Resultado ────────────────────────────────────────────────────────────
print(f"\nNulos restantes:\n{df.isnull().sum()[df.isnull().sum() > 0]}")
print(f"Duplicados: {df.duplicated().sum()}")
df.to_csv("data/clean/euroleague_teams_clean.csv", index=False)
print("✅ Guardado en data/clean/euroleague_teams_clean.csv")
