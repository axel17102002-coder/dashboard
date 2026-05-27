import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(".matplotlib-cache").resolve()))

import pandas as pd
from ydata_profiling import ProfileReport

ARCHIVOS = {
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

for nombre, ruta in ARCHIVOS.items():
    df = pd.read_csv(ruta)
    profile = ProfileReport(
        df,
        title=nombre,
        explorative=True
    )
    profile.to_file("src/cleaning/reports/" + nombre)


