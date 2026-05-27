import pandas as pd

# Cargar y hacer un diagnóstico rápido de cada archivo
archivos = {
    "l_box_score": "data/euroleague_box_score.csv",
    "l_header": "data/euroleague_header.csv",
    "l_players": "data/euroleague_players.csv",
    "l_teams": "data/euroleague_teams.csv",
    "l_points": "data/euroleague_points.csv",
    "l_play_by_play":"data/euroleague_play_by_play.csv",
    "l_comparison": "data/euroleague_comparison.csv",
    
    "c_box_score": "data/eurocup_box_score.csv",
    "c_header": "data/eurocup_header.csv",
    "c_players": "data/eurocup_players.csv",
    "c_teams": "data/eurocup_teams.csv",
    "c_points": "data/eurocup_points.csv",
    "c_play_by_play":"data/eurocup_play_by_play.csv",
    "c_comparison": "data/eurocup_comparison.csv",
}

for nombre, ruta in archivos.items():
    df = pd.read_csv(ruta)
    print(f"\n{'='*40}")
    print(f"📄 {nombre}: {df.shape[0]} filas x {df.shape[1]} columnas")
    print(f"Nulos:\n{df.isnull().sum()[df.isnull().sum() > 0]}")
    print(f"Duplicados: {df.duplicated().sum()}")

df_header = pd.read_csv("data/euroleague_header.csv")
df_box = pd.read_csv("data/euroleague_box_score.csv")
# ¿Los game_id del box_score existen todos en header?
ids_header = set(df_header["game_id"])
ids_box    = set(df_box["game_id"])

huerfanos = ids_box - ids_header
print(f"Partidos en box_score sin header: {len(huerfanos)}")  # Debería ser 0

