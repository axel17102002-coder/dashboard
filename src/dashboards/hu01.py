import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from db import (
    load_box_scores,
    load_game_headers,
    load_season_players,
    build_winrate_df,
    dark_layout,
)


def render():
    st.header("Dashboard — Entrenador")
    st.caption("Rendimiento individual · Decisiones tácticas")

    comp = st.selectbox("Competición", ["EuroLeague", "EuroCup", "Ambas"], key="h1_comp")

    try:
        df_box = load_box_scores(comp)
        df_hdr = load_game_headers(comp)
        df_sp = load_season_players(comp)
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

    c1, c2, c3 = st.columns(3)

    season = c1.selectbox(
        "Temporada",
        sorted(df_box["season_code"].dropna().unique()),
        key="h1_sea"
    )

    # Mapeo team_id -> nombre completo
    team_a = (
        df_hdr[["team_id_a", "team_a"]]
        .dropna()
        .drop_duplicates()
        .rename(columns={"team_id_a": "team_id", "team_a": "team_name"})
    )

    team_b = (
        df_hdr[["team_id_b", "team_b"]]
        .dropna()
        .drop_duplicates()
        .rename(columns={"team_id_b": "team_id", "team_b": "team_name"})
    )

    df_team_names = (
        pd.concat([team_a, team_b], ignore_index=True)
        .drop_duplicates(subset="team_id")
    )

    teams_ids_temporada = (
        df_box[df_box["season_code"] == season]["team_id"]
        .dropna()
        .unique()
    )

    df_team_names = (
        df_team_names[df_team_names["team_id"].isin(teams_ids_temporada)]
        .sort_values("team_name")
    )

    team_label_to_id = dict(
        zip(df_team_names["team_name"], df_team_names["team_id"])
    )

    team_label = c2.selectbox(
        "Equipo",
        list(team_label_to_id.keys()),
        key="h1_team"
    )

    team = team_label_to_id[team_label]

    fases = ["Todas"] + sorted(df_box["phase"].dropna().unique().tolist())
    fase = c3.selectbox("Fase", fases, key="h1_fase")

    st.divider()


    # MÓDULO 1 — PERFIL DE TIRO POR JUGADOR
    st.subheader("Perfil de Tiro por Jugador")
    st.caption(
        "Evolución por temporada. El eje Y representa el promedio por temporada "
        "de cada métrica seleccionada."
    )

    df_players_team = df_sp[df_sp["team_id"] == team].copy()

    df_players_team = df_players_team[
        df_players_team["player"].notna() &
        (df_players_team["player"].astype(str).str.strip() != "")
    ].copy()

    jugadores_validos = (
        df_players_team
        .groupby("player")["season_code"]
        .nunique()
        .reset_index(name="cantidad_temporadas")
    )

    jugadores = sorted(
        jugadores_validos[
            jugadores_validos["cantidad_temporadas"] >= 3
        ]["player"].tolist()
    )

    if not jugadores:
        st.info(
            "No hay jugadores con al menos 3 temporadas registradas "
            "para los filtros seleccionados."
        )
    else:
        jugador = st.selectbox("Jugador", jugadores, key="h1_jug")

        df_jug = df_players_team[df_players_team["player"] == jugador].copy()

        if df_jug.empty:
            st.info("Sin datos para el jugador seleccionado.")
        else:
            df_jug["fga_per_game"] = (
                df_jug["two_points_attempted_per_game"] +
                df_jug["three_points_attempted_per_game"]
            )

            df_tiro = (
                df_jug
                .groupby("season_code", as_index=False)
                .agg(
                    fga=("fga_per_game", "mean"),
                    two_pm=("two_points_made_per_game", "mean"),
                    three_pm=("three_points_made_per_game", "mean"),
                    fta=("free_throws_attempted_per_game", "mean"),
                )
                .sort_values("season_code")
            )

            if df_tiro.empty:
                st.info("Sin datos suficientes para generar el perfil de tiro.")
            else:
                fig_t = go.Figure()

                metricas = [
                    ("fga", "FGA", "#3498db"),
                    ("two_pm", "2PM", "#2ecc71"),
                    ("three_pm", "3PM", "#e74c3c"),
                    ("fta", "FTA", "#f39c12"),
                ]

                for col, name, color in metricas:
                    fig_t.add_trace(
                        go.Scatter(
                            x=df_tiro["season_code"],
                            y=df_tiro[col],
                            mode="lines+markers",
                            name=name,
                            line=dict(color=color, width=2),
                            marker=dict(size=7),
                            hovertemplate=(
                                "Temporada: %{x}<br>"
                                f"{name}: " + "%{y:.2f}<extra></extra>"
                            )
                        )
                    )

                fig_t.update_layout(
                    xaxis_title="Temporada",
                    yaxis_title="Promedio por temporada",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.05,
                        xanchor="center",
                        x=0.5,
                        font=dict(color="white")
                    ),
                    margin=dict(t=30),
                    height=460
                )

                dark_layout(fig_t)
                st.plotly_chart(fig_t, use_container_width=True)

    st.divider()


    # Módulo 2 — Consistencia competitiva
    st.subheader("Consistencia Competitiva")

    df_wr = build_winrate_df(df_hdr)
    df_tw = df_wr[
        (df_wr["team"] == team) &
        (df_wr["season_code"] == season)
    ]

    col_wr, col_q3 = st.columns(2)

    with col_wr:
        st.markdown("**Win Rate por Fase**")

        if df_tw.empty:
            st.info("Sin datos de resultados.")
        else:
            wr = (
                df_tw
                .groupby("phase")
                .agg(
                    p=("won", "count"),
                    v=("won", "sum")
                )
                .reset_index()
            )

            wr["win_rate"] = (wr["v"] / wr["p"] * 100).round(1)

            fig_wr = px.bar(
                wr,
                x="phase",
                y="win_rate",
                color="phase",
                text="win_rate",
                labels={
                    "phase": "Fase",
                    "win_rate": "Win Rate %"
                }
            )

            fig_wr.update_traces(
                texttemplate="%{text:.1f}%",
                textposition="outside"
            )

            fig_wr.update_layout(
                showlegend=False,
                yaxis=dict(range=[0, 110]),
                margin=dict(t=20)
            )

            dark_layout(fig_wr)
            st.plotly_chart(fig_wr, use_container_width=True)

    with col_q3:
        st.markdown("**Cierre con ventaja en Q3**")

        dh = df_hdr[df_hdr["season_code"] == season].copy()

        for lado in ["a", "b"]:
            dh[f"sq3_{lado}"] = (
                dh[f"score_quarter_1_{lado}"] +
                dh[f"score_quarter_2_{lado}"] +
                dh[f"score_quarter_3_{lado}"]
            )

        da = dh[dh["team_id_a"] == team].copy()
        da["lead_q3"] = da["sq3_a"] - da["sq3_b"]
        da["won"] = (da["score_a"] > da["score_b"]).astype(int)

        db_ = dh[dh["team_id_b"] == team].copy()
        db_["lead_q3"] = db_["sq3_b"] - db_["sq3_a"]
        db_["won"] = (db_["score_b"] > db_["score_a"]).astype(int)

        dq3 = pd.concat(
            [
                da[["lead_q3", "won"]],
                db_[["lead_q3", "won"]]
            ],
            ignore_index=True
        )

        rows = []

        for u in [10, 15, 20]:
            sub = dq3[dq3["lead_q3"] >= u]

            if len(sub):
                rows.append(
                    {
                        "Ventaja Q3": f"+{u} pts",
                        "Partidos": len(sub),
                        "Efectividad %": round(sub["won"].mean() * 100, 1)
                    }
                )

        if not rows:
            st.info("Sin partidos con ventaja ≥10 pts en Q3.")
        else:
            dfq = pd.DataFrame(rows)

            fig_q3 = px.bar(
                dfq,
                x="Ventaja Q3",
                y="Efectividad %",
                color="Ventaja Q3",
                text="Efectividad %",
                hover_data=["Partidos"]
            )

            fig_q3.update_traces(
                texttemplate="%{text:.1f}%",
                textposition="outside"
            )

            fig_q3.update_layout(
                showlegend=False,
                yaxis=dict(range=[0, 110]),
                margin=dict(t=20)
            )

            dark_layout(fig_q3)
            st.plotly_chart(fig_q3, use_container_width=True)