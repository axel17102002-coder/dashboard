import streamlit as st
import plotly.graph_objects as go
from db import load_box_scores, load_season_players, dark_layout


def render():
    st.header("Dashboard — Scout")
    st.caption("Evaluación de perfiles y progresión de jugadores")

    comp = st.selectbox("Competición", ["EuroLeague", "EuroCup", "Ambas"], key="h2_comp")

    try:
        df_box = load_box_scores(comp)
        df_sp = load_season_players(comp)
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

    c1, c2, c3 = st.columns(3)

    season = c1.selectbox(
        "Temporada",
        sorted(df_sp["season_code"].dropna().unique()),
        key="h2_sea"
    )

    teams = ["Todos"] + sorted(
        df_sp[df_sp["season_code"] == season]["team_id"].dropna().unique()
    )

    team = c2.selectbox("Equipo", teams, key="h2_team")

    perfs = ["Todos"] + sorted(
        df_sp["perfil_ofensivo"].dropna().unique().tolist()
    )

    perfil = c3.selectbox("Perfil ofensivo", perfs, key="h2_perf")

    st.divider()


    # Módulo 1 — Ranking TOP 10 aara jugadores
    st.subheader("Ranking de Valuación — Top 10 Jugadores")

    modo_pir = st.radio(
        "Vista",
        ["Ranking general", "Composición ofensiva/defensiva"],
        horizontal=True,
        key="h2_modo_pir"
    )

    min_gp = st.slider("Mín. partidos jugados", 1, 20, 5, key="h2_mingp")

    df_pir = df_sp[df_sp["season_code"] == season].copy()

    if team != "Todos":
        df_pir = df_pir[df_pir["team_id"] == team]

    if perfil != "Todos":
        df_pir = df_pir[df_pir["perfil_ofensivo"] == perfil]

    df_pir = df_pir[
        df_pir["player"].notna() &
        (df_pir["player"].astype(str).str.strip() != "") &
        (df_pir["player"].astype(str).str.upper() != "TEAM") &
        (df_pir["player"].astype(str).str.upper() != "TOTAL")
    ].copy()

    df_pir = df_pir[df_pir["games_played"] >= min_gp].copy()

    df_pir["pir_total"] = df_pir["valuation"]

    df_pir["offensive_raw"] = (
        df_pir["points"] +
        df_pir["assists"] +
        df_pir["offensive_rebounds"] +
        df_pir["fouls_received"]
    )

    df_pir["defensive_raw"] = (
        df_pir["defensive_rebounds"] +
        df_pir["steals"] +
        df_pir["blocks_favour"]
    )

    df_pir["total_raw"] = df_pir["offensive_raw"] + df_pir["defensive_raw"]
    df_pir = df_pir[df_pir["total_raw"] > 0].copy()

    df_pir["offensive_valuation"] = (
        df_pir["pir_total"] * df_pir["offensive_raw"] / df_pir["total_raw"]
    )

    df_pir["defensive_valuation"] = (
        df_pir["pir_total"] * df_pir["defensive_raw"] / df_pir["total_raw"]
    )

    top10 = df_pir.nlargest(10, "pir_total").sort_values("pir_total")

    if top10.empty:
        st.info("Sin datos suficientes.")
    else:
        fig_pir = go.Figure()

        if modo_pir == "Ranking general":
            fig_pir.add_trace(
                go.Bar(
                    y=top10["player"],
                    x=top10["pir_total"],
                    orientation="h",
                    marker_color="#f39c12",
                    name="PIR total",
                    text=top10["pir_total"].round(0).astype(int),
                    textposition="outside",
                    hovertemplate=(
                        "Jugador: %{y}<br>"
                        "Equipo: %{customdata}<br>"
                        "PIR total: %{x:.0f}<extra></extra>"
                    ),
                    customdata=top10["team_id"]
                )
            )

            fig_pir.update_layout(xaxis_title="PIR total")

        else:
            fig_pir.add_trace(
                go.Bar(
                    y=top10["player"],
                    x=top10["offensive_valuation"],
                    orientation="h",
                    marker_color="#e74c3c",
                    name="PIR ofensivo",
                    hovertemplate=(
                        "Jugador: %{y}<br>"
                        "PIR ofensivo: %{x:.1f}<extra></extra>"
                    )
                )
            )

            fig_pir.add_trace(
                go.Bar(
                    y=top10["player"],
                    x=top10["defensive_valuation"],
                    orientation="h",
                    marker_color="#3498db",
                    name="PIR defensivo",
                    hovertemplate=(
                        "Jugador: %{y}<br>"
                        "PIR defensivo: %{x:.1f}<extra></extra>"
                    )
                )
            )

            fig_pir.add_trace(
                go.Scatter(
                    x=top10["pir_total"] + 10,
                    y=top10["player"],
                    mode="text",
                    text=top10["pir_total"].round(0).astype(int),
                    textposition="middle center",
                    textfont=dict(color="white", size=12),
                    showlegend=False,
                    hoverinfo="skip"
                )
            )

            fig_pir.update_layout(
                barmode="stack",
                xaxis_title="PIR total"
            )

        max_pir = top10["pir_total"].max()

        fig_pir.update_xaxes(
            range=[0, max_pir * 1.15]
        )

        fig_pir.update_layout(
            margin=dict(t=20, l=180),
            height=430,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.25,
                xanchor="center",
                x=0.5,
                font=dict(
                    color="white",
                    size=12
                )
            )
        )

        dark_layout(fig_pir)
        st.plotly_chart(fig_pir, use_container_width=True)

    st.divider()

    # Módulo 2 — AST/TO
    st.subheader("Análisis de Creación de Juego — AST/TO")

    df_asto = df_sp[
        (df_sp["season_code"] == season) &
        (df_sp["turnovers"] > 0)
    ].copy()

    if team != "Todos":
        df_asto = df_asto[df_asto["team_id"] == team]

    if perfil != "Todos":
        df_asto = df_asto[df_asto["perfil_ofensivo"] == perfil]

    df_asto["ast_to_ratio"] = df_asto["ast_to_ratio"].astype(float)
    df_asto = df_asto.nlargest(15, "ast_to_ratio")

    if df_asto.empty:
        st.info("Sin datos para los filtros seleccionados.")
    else:
        fig_asto = go.Figure(
            go.Bar(
                y=df_asto["player"],
                x=df_asto["ast_to_ratio"],
                orientation="h",
                marker_color="#f39c12",
                text=df_asto["ast_to_ratio"].round(2),
                textposition="outside",
            )
        )

        fig_asto.update_layout(
            xaxis_title="AST/TO Ratio",
            margin=dict(t=20, l=180),
            height=440
        )

        dark_layout(fig_asto)
        st.plotly_chart(fig_asto, use_container_width=True)