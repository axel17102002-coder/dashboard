"""
Limpieza: euroleague_box_score.csv
Problema principal: 'minutes' como string "MM:SS" y 10 nulos en 'minutes'
"""
import pandas as pd

df = pd.read_csv("data/euroleague_box_score.csv")
print(f"Original: {df.shape}")

# ── 1. Jugadores que no jugaron ─────────────────────────────────────────────
# Los 10 nulos en 'minutes' son jugadores convocados pero que no entraron.
# is_playing == 0 los identifica. Se eliminan porque no aportan stats.
df = df[df["is_playing"] == 1].copy()
print(f"Tras eliminar no jugadores: {df.shape}")

# ── 2. Convertir minutes "MM:SS" → float (minutos decimales) ────────────────
def parse_minutes(val):
    try:
        partes = str(val).split(":")
        return int(partes[0]) + int(partes[1]) / 60
    except:
        return 0.0

df["minutes_num"] = df["minutes"].apply(parse_minutes)

# ── 3. Tipos correctos ──────────────────────────────────────────────────────
df["is_starter"] = df["is_starter"].astype(bool)
df["is_playing"] = df["is_playing"].astype(bool)

# ── 4. Verificación de rangos lógicos ───────────────────────────────────────
# EuroLeague usa reglas FIBA: máximo 5 faltas personales
anomalias = []

mask_faltas = df["fouls_committed"] > 5
if mask_faltas.any():
    print(f"  ⚠️  {mask_faltas.sum()} filas con fouls_committed > 5 → se capean a 5")
    anomalias.append(df[mask_faltas][["game_player_id","game_id","player","fouls_committed"]].assign(motivo="fouls>5"))
    df.loc[mask_faltas, "fouls_committed"] = 5

mask_pts = df["points"] < 0
if mask_pts.any():
    print(f"  ⚠️  {mask_pts.sum()} filas con points < 0 → se capean a 0")
    df.loc[mask_pts, "points"] = 0

mask_min = df["minutes_num"] > 65
if mask_min.any():
    print(f"  ⚠️  {mask_min.sum()} filas con minutes_num > 65 → revisar")

if anomalias:
    import pandas as pd
    pd.concat(anomalias, ignore_index=True).to_csv(
        "data/clean/box_score_anomalias.csv", index=False
    )

# ── 5. Columna auxiliar: tipo de jugador ────────────────────────────────────
df["role"] = df["is_starter"].map({True: "starter", False: "bench"})

# ── 6. Resultado ────────────────────────────────────────────────────────────
print(f"\nNulos restantes:\n{df.isnull().sum()[df.isnull().sum() > 0]}")
print(f"Duplicados: {df.duplicated().sum()}")
df.to_csv("data/clean/euroleague_box_score_clean.csv", index=False)
print("✅ Guardado en data/clean/euroleague_box_score_clean.csv")