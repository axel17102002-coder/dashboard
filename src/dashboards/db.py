import os
import pandas as pd
import streamlit as st
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from sqlalchemy import create_engine

@st.cache_resource
def get_engine():
    user = os.environ.get("POSTGRES_USER", "usuario_basket")
    pwd  = os.environ.get("POSTGRES_PASSWORD", "bskt26")
    db   = os.environ.get("POSTGRES_DB", "basket_db")
    return create_engine(f"postgresql://{user}:{pwd}@db:5432/{db}")


@st.cache_data(ttl=600)
def load_season_players(comp: str) -> pd.DataFrame:
    where = "" if comp == "Ambas" else f"WHERE competition = '{comp}'"
    return pd.read_sql(f"SELECT * FROM season_players {where}", get_engine())

@st.cache_data(ttl=600)
def load_box_scores(comp: str) -> pd.DataFrame:
    where = "" if comp == "Ambas" else f"WHERE competition = '{comp}'"
    return pd.read_sql(f"SELECT * FROM game_box_scores {where}", get_engine())

@st.cache_data(ttl=600)
def load_game_headers(comp: str) -> pd.DataFrame:
    where = "" if comp == "Ambas" else f"WHERE competition = '{comp}'"
    return pd.read_sql(f"SELECT * FROM game_headers {where}", get_engine())

@st.cache_data(ttl=600)
def load_season_teams(comp: str) -> pd.DataFrame:
    where = "" if comp == "Ambas" else f"WHERE competition = '{comp}'"
    return pd.read_sql(f"SELECT * FROM season_teams {where}", get_engine())

@st.cache_data(ttl=600)
def load_shot_data(player: str, comp: str, season: str) -> pd.DataFrame:
    where = f"""
        WHERE action_id IN ('2FGM','2FGA','3FGM','3FGA')
          AND player = '{player}'
          AND season_code = '{season}'
    """
    if comp != "Ambas":
        where += f" AND competition = '{comp}'"
    return pd.read_sql(f"SELECT * FROM game_points {where}", get_engine())


def build_winrate_df(df_h: pd.DataFrame) -> pd.DataFrame:
    df_a = df_h[["game_id","season_code","phase","team_id_a","score_a","score_b","competition"]].copy()
    df_a.columns = ["game_id","season_code","phase","team","score_own","score_opp","competition"]
    df_b = df_h[["game_id","season_code","phase","team_id_b","score_b","score_a","competition"]].copy()
    df_b.columns = ["game_id","season_code","phase","team","score_own","score_opp","competition"]
    out = pd.concat([df_a, df_b], ignore_index=True)
    out["won"] = (out["score_own"] > out["score_opp"]).astype(int)
    return out


def dark_layout(fig):
    fig.update_layout(
        plot_bgcolor="#1a1a2e",
        paper_bgcolor="#0f0f1a",
        font_color="white",
    )
    fig.update_xaxes(gridcolor="#333")
    fig.update_yaxes(gridcolor="#333")
    return fig


def draw_shot_map(df_shots: pd.DataFrame, min_intentos: int):
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_facecolor("#1a1a2e")
    fig.patch.set_facecolor("#1a1a2e")

    ax.add_patch(patches.Rectangle((-750,-200),1500,1400, lw=2, ec="white", fc="none"))
    ax.add_patch(patches.Rectangle((-245,-200), 490, 580, lw=2, ec="white", fc="none"))
    ax.plot([-245,245],[380,380], color="white", lw=2)
    ax.add_patch(patches.Arc((0,380),490,490,theta1=0,theta2=180,color="white",lw=2))
    ax.add_patch(patches.Arc((0,0),1350,1350,theta1=12,theta2=168,color="white",lw=2))
    ax.plot([-675,-675],[-200,140], color="white", lw=2)
    ax.plot([675, 675],[-200,140], color="white", lw=2)
    ax.add_patch(plt.Circle((0,0),23, color="orange", fill=False, lw=2))
    ax.plot([-90,90],[-52,-52], color="white", lw=3)

    by_zone = df_shots.groupby("zone").agg(
        intentos=("action_id","count"),
        aciertos=("action_id", lambda x: x.str.endswith("M").sum()),
        cx=("coord_x","mean"),
        cy=("coord_y","mean"),
    ).reset_index()
    by_zone = by_zone[by_zone["intentos"] >= min_intentos]

    if by_zone.empty:
        ax.text(0, 500, "Sin datos suficientes", color="white", ha="center", fontsize=11)
    else:
        by_zone["pct"] = by_zone["aciertos"] / by_zone["intentos"]
        mx = by_zone["intentos"].max()
        by_zone["sz"] = (by_zone["intentos"] / mx) * 2700 + 300

        def _color(p):
            if p < 0.30: return "#e74c3c"
            if p < 0.50: return "#f39c12"
            return "#2ecc71"

        for _, r in by_zone.iterrows():
            ax.scatter(r["cx"], r["cy"], s=r["sz"], color=_color(r["pct"]),
                       alpha=0.75, zorder=5, edgecolors="white", lw=0.5)
            ax.text(r["cx"], r["cy"], f"{r['pct']:.0%}\n({int(r['intentos'])})",
                    color="white", ha="center", va="center", fontsize=7,
                    fontweight="bold", zorder=6)

    for c, lbl in [("#e74c3c","≤29%"),("#f39c12","30–49%"),("#2ecc71","≥50%")]:
        ax.scatter([],[], color=c, s=80, label=lbl)
    ax.legend(loc="lower right", facecolor="#1a1a2e", labelcolor="white", fontsize=8)

    ax.set_xlim(-820,820); ax.set_ylim(-300,1100)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Mapa de Aciertos — Media Cancha", color="white", fontsize=12, pad=8)
    return fig


def make_radar(df: pd.DataFrame, pa: str, pb: str, modo: str):
    if modo == "Ofensivo":
        cols   = ["points_per_game","assists_per_game","efg_pct","ts_pct",
                  "offensive_rebounds_per_game","usg_pct"]
        labels = ["PTS/G","AST/G","eFG%","TS%","OREB/G","USG%"]
    else:
        cols   = ["defensive_rebounds_per_game","steals_per_game","blocks_favour_per_game",
                  "ast_to_ratio","fouls_received_per_game","total_rebounds_per_game"]
        labels = ["DREB/G","STL/G","BLK/G","AST/TO","Faltas Rec/G","REB/G"]

    df_norm = df.set_index("player")[cols].copy()
    df_norm = (df_norm - df_norm.min()) / (df_norm.max() - df_norm.min() + 1e-9)

    fig = go.Figure()
    for player, color in [(pa,"#e74c3c"),(pb,"#3498db")]:
        if player not in df_norm.index:
            continue
        vals = df_norm.loc[player, cols].tolist()
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=labels + [labels[0]],
            fill="toself", name=player,
            line_color=color, opacity=0.75,
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0,1], showticklabels=False),
            bgcolor="#1a1a2e",
        ),
        paper_bgcolor="#0f0f1a", font_color="white",
        legend=dict(bgcolor="#1a1a2e"),
        margin=dict(t=40, b=40),
    )
    return fig


# Validar usuarios para el login
def validar_usuario(username, password):
    query = """
        SELECT username, rol
        FROM usuarios
        WHERE username = %(username)s
        AND password = %(password)s
    """

    df = pd.read_sql(
        query,
        get_engine(),
        params={
            "username": username,
            "password": password
        }
    )

    if df.empty:
        return None

    return {
        "username": df.iloc[0]["username"],
        "rol": df.iloc[0]["rol"]
    }