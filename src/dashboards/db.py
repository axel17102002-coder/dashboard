import os
import pandas as pd
import streamlit as st
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
import numpy as np

@st.cache_resource
def get_engine():
    user = os.environ.get("POSTGRES_USER", "usuario_basket")
    pwd  = os.environ.get("POSTGRES_PASSWORD", "bskt26")
    db   = os.environ.get("POSTGRES_DB", "basket_db")
    return create_engine(f"postgresql://{user}:{pwd}@db:5432/{db}")


# Usuarios por defecto del sistema (username, password, rol)
USUARIOS_DEFAULT = [
    ("Melina",   "admin",      "admin"),
    ("Yessica",  "entrenador", "entrenador"),
    ("Emiliano", "scout",      "scout"),
    ("Cinthia",  "analista",   "analista"),
    ("Axel",     "directivo",  "directivo"),
    ("admin",    "admin",      "admin"),
]


@st.cache_resource
def ensure_usuarios_table():
    """Crea la tabla de usuarios y siembra los usuarios por defecto si faltan.

    Se ejecuta al iniciar Streamlit, así el login funciona aunque el volumen
    de Postgres ya exista (schema.sql solo corre en la primera inicialización)
    o aunque el pipeline de datos haya recreado el resto de las tablas.
    """
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL,
                rol VARCHAR(30) NOT NULL
            )
        """))
        for username, password, rol in USUARIOS_DEFAULT:
            conn.execute(
                text("""
                    INSERT INTO usuarios (username, password, rol)
                    VALUES (:u, :p, :r)
                    ON CONFLICT (username) DO NOTHING
                """),
                {"u": username, "p": password, "r": rol},
            )
    return True


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


@st.cache_data(ttl=600)
def load_clutch_points(comp: str, season: str) -> pd.DataFrame:
    """Puntos anotados por jugador en los últimos 5 minutos (clutch) de una temporada.

    Se calcula agregando directamente en PostgreSQL sobre game_points.
    'minute' es el minuto transcurrido (1-40 en regulación); los últimos 5
    minutos del 4º cuarto son los minutos 36 a 40. Solo se cuentan conversiones
    (points > 0). Se excluye la prórroga para un criterio uniforme entre partidos.
    """
    where = f"season_code = '{season}' AND minute BETWEEN 36 AND 40 AND points > 0"
    if comp != "Ambas":
        where += f" AND competition = '{comp}'"
    q = f"""
        SELECT player, SUM(points) AS clutch_points
        FROM game_points
        WHERE {where}
        GROUP BY player
    """
    return pd.read_sql(q, get_engine())


def build_winrate_df(df_h: pd.DataFrame) -> pd.DataFrame:
    df_a = df_h[["game_id","season_code","phase","team_id_a","score_a","score_b","competition"]].copy()
    df_a.columns = ["game_id","season_code","phase","team","score_own","score_opp","competition"]
    df_b = df_h[["game_id","season_code","phase","team_id_b","score_b","score_a","competition"]].copy()
    df_b.columns = ["game_id","season_code","phase","team","score_own","score_opp","competition"]
    out = pd.concat([df_a, df_b], ignore_index=True)
    out["won"] = (out["score_own"] > out["score_opp"]).astype(int)
    return out


def dark_layout(fig):
    # Tema claro (se mantiene el nombre por compatibilidad con los llamados)
    fig.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font_color="#14140f",
    )
    fig.update_xaxes(gridcolor="#e3e7ef")
    fig.update_yaxes(gridcolor="#e3e7ef")
    return fig


def draw_shot_map(df_shots: pd.DataFrame, min_intentos: int):
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_facecolor("#ffffff")
    fig.patch.set_facecolor("#ffffff")

    ax.add_patch(patches.Rectangle((-750,-200),1500,1400, lw=2, ec="#444", fc="none"))
    ax.add_patch(patches.Rectangle((-245,-200), 490, 580, lw=2, ec="#444", fc="none"))
    ax.plot([-245,245],[380,380], color="#444", lw=2)
    ax.add_patch(patches.Arc((0,380),490,490,theta1=0,theta2=180,color="#444",lw=2))
    # Línea de triple: tramos laterales + arco superior
    triple_x = 675
    triple_y_inicio = -200
    triple_y_union = 140
    triple_radio = (triple_x**2 + triple_y_union**2) ** 0.5

    theta_union = np.degrees(np.arctan2(triple_y_union, triple_x))

    ax.plot([-triple_x, -triple_x], [triple_y_inicio, triple_y_union], color="#444", lw=2)
    ax.plot([ triple_x,  triple_x], [triple_y_inicio, triple_y_union], color="#444", lw=2)

    ax.add_patch(
        patches.Arc(
            (0, 0),
            2 * triple_radio,
            2 * triple_radio,
            theta1=theta_union,
            theta2=180 - theta_union,
            color="#444",
            lw=2
        )
    )
    ax.add_patch(plt.Circle((0,0),23, color="#E8500A", fill=False, lw=2))
    ax.plot([-90,90],[-52,-52], color="#444", lw=3)

    by_zone = df_shots.groupby("zone").agg(
        intentos=("action_id","count"),
        aciertos=("action_id", lambda x: x.str.endswith("M").sum()),
        cx=("coord_x","mean"),
        cy=("coord_y","mean"),
    ).reset_index()
    by_zone = by_zone[by_zone["intentos"] >= min_intentos]

    if by_zone.empty:
        ax.text(0, 500, "Sin datos suficientes", color="#333", ha="center", fontsize=11)
    else:
        by_zone["pct"] = by_zone["aciertos"] / by_zone["intentos"]
        mx = by_zone["intentos"].max()
        by_zone["sz"] = (by_zone["intentos"] / mx) * 3500 + 500
        
        def _color(p):
            if p < 0.30: return "#e74c3c"
            if p < 0.50: return "#f39c12"
            return "#2ecc71"

        for _, r in by_zone.iterrows():
            ax.scatter(r["cx"], r["cy"], s=r["sz"], color=_color(r["pct"]),
                       alpha=0.75, zorder=5, edgecolors="white", lw=0.5)
            ax.text(
                r["cx"],
                r["cy"],
                f"{r['pct']:.0%}\n{int(r['aciertos'])}/{int(r['intentos'])}",
                color="white",
                ha="center",
                va="center",
                fontsize=8,
                fontweight="bold",
                zorder=6
            )

    for c, lbl in [("#e74c3c","≤29%"),("#f39c12","30–49%"),("#2ecc71","≥50%")]:
        ax.scatter([],[], color=c, s=80, label=lbl)
    ax.legend(loc="lower right", facecolor="#ffffff", edgecolor="#e3e7ef", labelcolor="#333", fontsize=8)

    ax.set_xlim(-820,820); ax.set_ylim(-300,1100)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Mapa de Aciertos — Media Cancha", color="#14140f", fontsize=12, pad=8)
    return fig


@st.cache_data(ttl=600)
def load_league_zone_avg(comp: str, season: str) -> pd.DataFrame:
    """Efectividad promedio de toda la liga por zona (para comparación relativa)."""
    where = (
        "action_id IN ('2FGM','2FGA','3FGM','3FGA') "
        f"AND season_code = '{season}'"
    )
    if comp != "Ambas":
        where += f" AND competition = '{comp}'"
    q = f"""
        SELECT zone,
               SUM(CASE WHEN action_id LIKE '%%M' THEN 1 ELSE 0 END) AS aciertos,
               COUNT(*) AS intentos
        FROM game_points
        WHERE {where}
        GROUP BY zone
    """
    df = pd.read_sql(q, get_engine())
    df["pct_liga"] = df["aciertos"] / df["intentos"]
    return df[["zone", "pct_liga"]]


def _court_shapes():
    """Genera las líneas de la media cancha como trazas de Plotly (sin hover)."""
    line = dict(color="#888", width=1.5)
    traces = []

    def seg(xs, ys):
        traces.append(go.Scatter(x=xs, y=ys, mode="lines", line=line,
                                 hoverinfo="skip", showlegend=False))

    def arc(cx, cy, r, t0, t1, n=80):
        t = np.linspace(np.radians(t0), np.radians(t1), n)
        seg((cx + r * np.cos(t)).tolist(), (cy + r * np.sin(t)).tolist())

    # Límite de cancha y zona pintada
    seg([-750, 750, 750, -750, -750], [-200, -200, 1200, 1200, -200])
    seg([-245, 245, 245, -245, -245], [-200, -200, 380, 380, -200])
    seg([-245, 245], [380, 380])                 # línea de tiros libres
    arc(0, 380, 245, 0, 180)                      # círculo de tiros libres
    # Triple
    triple_x, triple_y_union = 675, 140
    triple_r = (triple_x**2 + triple_y_union**2) ** 0.5
    th = np.degrees(np.arctan2(triple_y_union, triple_x))
    seg([-triple_x, -triple_x], [-200, triple_y_union])
    seg([triple_x, triple_x], [-200, triple_y_union])
    arc(0, 0, triple_r, th, 180 - th)
    arc(0, 0, 23, 0, 360)                          # aro
    seg([-90, 90], [-52, -52])                     # tablero
    return traces


def make_shot_map(df_shots: pd.DataFrame, min_intentos: int, df_liga: pd.DataFrame = None):
    """Mapa de aciertos interactivo (Plotly). Si se pasa df_liga, colorea por
    diferencia respecto al promedio de la liga en cada zona."""
    by_zone = df_shots.groupby("zone").agg(
        intentos=("action_id", "count"),
        aciertos=("action_id", lambda x: x.str.endswith("M").sum()),
        cx=("coord_x", "mean"),
        cy=("coord_y", "mean"),
    ).reset_index()
    by_zone = by_zone[by_zone["intentos"] >= min_intentos].copy()

    fig = go.Figure()
    for t in _court_shapes():
        fig.add_trace(t)

    if by_zone.empty:
        fig.add_annotation(text="Sin zonas con suficientes intentos",
                           x=0, y=500, showarrow=False, font=dict(color="#888", size=13))
    else:
        by_zone["pct"] = by_zone["aciertos"] / by_zone["intentos"]
        relativo = df_liga is not None
        if relativo:
            by_zone = by_zone.merge(df_liga, on="zone", how="left")
            by_zone["pct_liga"] = by_zone["pct_liga"].fillna(by_zone["pct"])
            by_zone["valor"] = by_zone["pct"] - by_zone["pct_liga"]
            cmin, cmax, cbar_title = -0.20, 0.20, "vs liga"
        else:
            by_zone["valor"] = by_zone["pct"]
            cmin, cmax, cbar_title = 0.0, 1.0, "Efectividad"

        # Tamaño proporcional al volumen de intentos
        mx = by_zone["intentos"].max()
        sizes = 20 + (by_zone["intentos"] / mx) * 55

        custom = np.column_stack([
            by_zone["aciertos"], by_zone["intentos"], by_zone["pct"] * 100,
            (by_zone["pct_liga"] * 100 if relativo else by_zone["pct"] * 100),
        ])
        if relativo:
            htmpl = ("<b>%{text}</b><br>Intentos: %{customdata[1]:.0f}<br>"
                     "Aciertos: %{customdata[0]:.0f}<br>Efectividad: %{customdata[2]:.0f}%<br>"
                     "Liga: %{customdata[3]:.0f}%<extra></extra>")
        else:
            htmpl = ("<b>%{text}</b><br>Intentos: %{customdata[1]:.0f}<br>"
                     "Aciertos: %{customdata[0]:.0f}<br>Efectividad: %{customdata[2]:.0f}%<extra></extra>")

        fig.add_trace(go.Scatter(
            x=by_zone["cx"], y=by_zone["cy"], mode="markers+text",
            text=by_zone["zone"],
            texttemplate=by_zone["pct"].apply(lambda p: f"{p:.0%}"),
            textposition="middle center",
            textfont=dict(color="#14140f", size=10, family="sans-serif"),
            marker=dict(
                size=sizes, sizemode="diameter",
                color=by_zone["valor"], colorscale="RdYlGn",
                cmin=cmin, cmax=cmax,
                line=dict(color="#ffffff", width=1.5),
                colorbar=dict(title=cbar_title, tickfont=dict(color="#14140f")),
            ),
            customdata=custom,
            hovertemplate=htmpl,
            showlegend=False,
        ))

    fig.update_xaxes(visible=False, range=[-820, 820],
                     scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False, range=[-300, 1100])
    fig.update_layout(
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        margin=dict(t=10, b=10, l=10, r=10), height=560,
    )
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
            fill="toself",
            name=player,
            line_color=color,
            opacity=0.75,
            marker=dict(size=8),
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "%{theta}: %{r:.2%}"
                "<extra></extra>"
            ),
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0,1], showticklabels=False),
            bgcolor="#f4f6fa",
        ),
        paper_bgcolor="#ffffff", font_color="#14140f",
        legend=dict(bgcolor="#f4f6fa"),
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

def format_season(code) -> str:
    return str(code)[1:]