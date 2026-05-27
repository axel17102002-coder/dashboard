"""
Limpieza: euroleague_play_by_play.csv
Dataset grande (~1M+ filas). Foco en tipos, plays sin jugador y consistencia.
"""
import pandas as pd
import os

liga = os.environ.get("LIGA", "euroleague")
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

# ── 7. Resultado ─────────────────────────────────────────────────────────────
nulos = df.isnull().sum()
nulos = nulos[nulos > 0]
print(f"\nNulos restantes:\n{nulos if len(nulos) else 'ninguno'}")
print(f"Duplicados: {df.duplicated().sum()}")
df.to_csv(f"data/clean/{liga}_play_by_play_clean.csv", index=False)
print(f"✅ Guardado en data/clean/{liga}_play_by_play_clean.csv")