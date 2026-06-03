import streamlit as st
import plotly.graph_objects as go
from db import load_box_scores, load_season_players, dark_layout


def render():
    st.header("Dashboard — Scout")
    st.caption("Evaluación de perfiles y progresión de jugadores")

    comp = st.selectbox("Competición", ["EuroLeague", "EuroCup", "Ambas"], key="h2_comp")

    try:
        df_box = load_box_scores(comp)
        df_sp  = load_season_players(comp)
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

    c1, c2, c3 = st.columns(3)
    season = c1.selectbox("Temporada", sorted(df_box["season_code"].unique()), key="h2_sea")
    teams  = ["Todos"] + sorted(df_box[df_box["season_code"]==season]["team_id"].unique())
    team   = c2.selectbox("Equipo", teams, key="h2_team")
    perfs  = ["Todos"] + sorted(df_sp["perfil_ofensivo"].dropna().unique().tolist())
    perfil = c3.selectbox("Perfil ofensivo", perfs, key="h2_perf")

    st.divider()

    # Módulo 1 — Ranking PIR Top 10
    st.subheader("Ranking de Valuación — Top 10")
    toggle = st.radio("Rendimiento", ["General","Ofensivo","Defensivo"], horizontal=True)
    min_gp = st.slider("Mín. partidos jugados", 1, 20, 5, key="h2_mingp")

    df_pir = df_box[df_box["season_code"]==season].copy()
    if team != "Todos":
        df_pir = df_pir[df_pir["team_id"]==team]

    agg = df_pir.groupby(["player","team_id"]).agg(
        partidos =("game_id","nunique"),
        pir_total=("pir_calculado","sum"),
        pts      =("points","sum"),
        ast      =("assists","sum"),
        oreb     =("offensive_rebounds","sum"),
        dreb     =("defensive_rebounds","sum"),
        stl      =("steals","sum"),
        blk      =("blocks_favour","sum"),
        pm       =("plus_minus","sum"),
    ).reset_index()
    agg = agg[agg["partidos"] >= min_gp]

    if toggle == "General":
        agg["valor"] = agg["pir_total"]
        xlabel, bar_color = "PIR Total", "#3498db"
    elif toggle == "Ofensivo":
        agg["valor"] = agg["pts"] + agg["ast"] + agg["oreb"]
        xlabel, bar_color = "PIR Ofensivo (PTS+AST+OREB)", "#e74c3c"
    else:
        agg["valor"] = agg["dreb"] + agg["stl"] + agg["blk"]
        xlabel, bar_color = "PIR Defensivo (DREB+STL+BLK)", "#2ecc71"

    top10 = agg.nlargest(10,"valor").sort_values("valor")
    if top10.empty:
        st.info("Sin datos suficientes.")
    else:
        fig_pir = go.Figure(go.Bar(
            y=top10["player"], x=top10["valor"], orientation="h",
            marker_color=bar_color,
            text=top10["valor"].round(0).astype(int), textposition="outside",
        ))
        fig_pir.update_layout(xaxis_title=xlabel, margin=dict(t=20, l=160), height=400)
        dark_layout(fig_pir)
        st.plotly_chart(fig_pir, use_container_width=True)

    st.divider()

    # Módulo 2 — AST/TO
    st.subheader("Análisis de Creación de Juego — AST/TO")
    df_asto = df_sp[(df_sp["season_code"]==season) & (df_sp["turnovers"]>0)].copy()
    if team != "Todos":
        df_asto = df_asto[df_asto["team_id"]==team]
    if perfil != "Todos":
        df_asto = df_asto[df_asto["perfil_ofensivo"]==perfil]

    df_asto["ast_to_ratio"] = df_asto["ast_to_ratio"].astype(float)
    df_asto = df_asto.nlargest(15, "ast_to_ratio")

    if df_asto.empty:
        st.info("Sin datos para los filtros seleccionados.")
    else:
        fig_asto = go.Figure(go.Bar(
            y=df_asto["player"], x=df_asto["ast_to_ratio"], orientation="h",
            marker_color="#f39c12",
            text=df_asto["ast_to_ratio"].round(2), textposition="outside",
        ))
        fig_asto.update_layout(xaxis_title="AST/TO Ratio", margin=dict(t=20, l=160), height=440)
        dark_layout(fig_asto)
        st.plotly_chart(fig_asto, use_container_width=True)
