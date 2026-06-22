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
    format_season,
)


def _build_team_name_map(df_hdr):
    team_a = (
        df_hdr[["team_id_a", "team_a"]].dropna().drop_duplicates()
        .rename(columns={"team_id_a": "team_id", "team_a": "team_name"})
    )
    team_b = (
        df_hdr[["team_id_b", "team_b"]].dropna().drop_duplicates()
        .rename(columns={"team_id_b": "team_id", "team_b": "team_name"})
    )
    return pd.concat([team_a, team_b]).drop_duplicates(subset="team_id")


def render():
    # ── Filtros en sidebar ────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### Filtros")
        comp = st.selectbox(
            "Competición", ["EuroLeague", "EuroCup", "Ambas"], key="h1_comp",
            help="Filtra todos los módulos por competición",
        )

    try:
        df_box = load_box_scores(comp)
        df_hdr = load_game_headers(comp)
        df_sp  = load_season_players(comp)
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

    df_team_names = _build_team_name_map(df_hdr)
    season_codes  = sorted(df_box["season_code"].dropna().unique())
    season_labels = {format_season(s): s for s in season_codes}

    if not season_labels:
        st.warning("No hay datos disponibles para la competición seleccionada.")
        st.stop()

    with st.sidebar:
        season = season_labels[st.selectbox(
            "Temporada", list(season_labels.keys()), key="h1_sea",
            help="Temporada a analizar",
        )]

        teams_en_temporada = (
            df_box[df_box["season_code"] == season]["team_id"].dropna().unique()
        )
        df_teams_sel = (
            df_team_names[df_team_names["team_id"].isin(teams_en_temporada)]
            .sort_values("team_name")
        )
        team_label_to_id = dict(zip(df_teams_sel["team_name"], df_teams_sel["team_id"]))
        team_label = st.selectbox("Equipo", list(team_label_to_id.keys()), key="h1_team")
        team       = team_label_to_id[team_label]

        fases = ["Todas"] + sorted(df_box["phase"].dropna().unique().tolist())
        st.selectbox("Fase", fases, key="h1_fase", help="Filtra por fase del torneo")

    # ── Tabs de módulos ───────────────────────────────────────────────────────
    tab1, tab2 = st.tabs(["📈 Perfil de Tiro", "🏆 Consistencia Competitiva"])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Perfil de Tiro por Jugador
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.subheader("Perfil de Tiro por Jugador")
        st.caption("Evolución temporal de métricas de tiro · promedio por temporada")

        col_filtros, col_graf = st.columns([1, 3])

        with col_filtros:
            st.markdown("##### Filtros")
            df_players_team = df_sp[df_sp["team_id"] == team].copy()
            df_players_team = df_players_team[
                df_players_team["player"].notna() &
                (df_players_team["player"].astype(str).str.strip() != "")
            ]
            posiciones = ["Todas"] + sorted(
                df_players_team["perfil_ofensivo"].dropna().unique().tolist()
            )
            pos_sel = st.selectbox(
                "Posición / Perfil", posiciones, key="h1_pos",
                help="Filtrá por posición antes de seleccionar jugador",
            )
            if pos_sel != "Todas":
                df_players_team = df_players_team[df_players_team["perfil_ofensivo"] == pos_sel]

            jugadores_validos = (
                df_players_team.groupby("player")["season_code"]
                .nunique().reset_index(name="n_temporadas")
            )
            jugadores = sorted(
                jugadores_validos[jugadores_validos["n_temporadas"] >= 2]["player"].tolist()
            )
            if jugadores:
                jugador = st.selectbox("Jugador", jugadores, key="h1_jug")

        with col_graf:
            if not jugadores:
                st.info("No hay jugadores con al menos 2 temporadas registradas para los filtros seleccionados.")
            else:
                df_jug = df_players_team[df_players_team["player"] == jugador].copy()
                if df_jug.empty:
                    st.info("Sin datos para el jugador seleccionado.")
                else:
                    df_jug["fga_per_game"] = (
                        df_jug["two_points_attempted_per_game"] +
                        df_jug["three_points_attempted_per_game"]
                    )
                    df_tiro = (
                        df_jug.groupby("season_code", as_index=False)
                        .agg(
                            fga=("fga_per_game", "mean"),
                            two_pm=("two_points_made_per_game", "mean"),
                            three_pm=("three_points_made_per_game", "mean"),
                            fta=("free_throws_attempted_per_game", "mean"),
                        )
                        .sort_values("season_code")
                    )

                    ultima = df_tiro.iloc[-1]
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("FGA",  f"{ultima['fga']:.1f}",      help="Intentos de campo por partido")
                    k2.metric("2PM",  f"{ultima['two_pm']:.1f}",   help="Dobles convertidos por partido")
                    k3.metric("3PM",  f"{ultima['three_pm']:.1f}", help="Triples convertidos por partido")
                    k4.metric("FTA",  f"{ultima['fta']:.1f}",      help="Tiros libres intentados por partido")

                    pass  # divider removed

                    fig_t = go.Figure()
                    for col, name, color in [
                        ("fga",      "FGA",  "#3498db"),
                        ("two_pm",   "2PM",  "#2ecc71"),
                        ("three_pm", "3PM",  "#e74c3c"),
                        ("fta",      "FTA",  "#f39c12"),
                    ]:
                        fig_t.add_trace(go.Scatter(
                            x=df_tiro["season_code"], y=df_tiro[col],
                            mode="lines+markers", name=name,
                            line=dict(color=color, width=2), marker=dict(size=7),
                            hovertemplate=f"Temporada: %{{x}}<br>{name}: %{{y:.2f}}<extra></extra>",
                        ))

                    fig_t.update_layout(
                        xaxis_title="Temporada", yaxis_title="Promedio por temporada",
                        legend=dict(
                            orientation="h", yanchor="bottom", y=1.05,
                            xanchor="center", x=0.5, font=dict(color="#14140f"),
                        ),
                        margin=dict(t=30), height=420,
                    )
                    dark_layout(fig_t)
                    st.plotly_chart(fig_t, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Consistencia Competitiva
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.subheader("Consistencia Competitiva")
        st.caption("Win Rate por fase · Capacidad de cierre con ventaja en Q3")

        df_wr = build_winrate_df(df_hdr)
        df_tw = df_wr[(df_wr["team"] == team) & (df_wr["season_code"] == season)]

        if not df_tw.empty:
            total_partidos  = len(df_tw)
            total_victorias = df_tw["won"].sum()
            wr_global       = round(total_victorias / total_partidos * 100, 1) if total_partidos else 0
            k1, k2, k3 = st.columns(3)
            k1.metric("Partidos jugados", total_partidos,       help=f"Temporada {format_season(season)}")
            k2.metric("Victorias",        int(total_victorias))
            k3.metric("Win Rate global",  f"{wr_global}%")
            pass  # divider removed

        col_filtros2, col_wr, col_q3 = st.columns([1, 2, 2])

        with col_filtros2:
            st.markdown("##### Filtros")
            umbral = st.selectbox(
                "Ventaja mínima en Q3",
                [10, 15, 20],
                format_func=lambda x: f"+{x} puntos",
                key="h1_q3_umbral",
                help="Solo se consideran partidos donde el equipo tuvo esta ventaja al terminar el Q3",
            )

        with col_wr:
            st.markdown("##### Win Rate por Fase")
            if df_tw.empty:
                st.info("Sin datos de resultados para la temporada seleccionada.")
            else:
                wr = (
                    df_tw.groupby("phase")
                    .agg(p=("won", "count"), v=("won", "sum"))
                    .reset_index()
                )
                wr["win_rate"] = (wr["v"] / wr["p"] * 100).round(1)
                fig_wr = px.bar(
                    wr, x="phase", y="win_rate", color="phase", text="win_rate",
                    labels={"phase": "Fase", "win_rate": "Win Rate %"},
                    color_discrete_sequence=["#f39c12", "#3498db", "#2ecc71"],
                )
                fig_wr.update_traces(
                    texttemplate="%{text:.1f}%", textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Win Rate: %{y:.1f}%<extra></extra>",
                )
                fig_wr.update_layout(showlegend=False, yaxis=dict(range=[0, 115]), margin=dict(t=20))
                dark_layout(fig_wr)
                st.plotly_chart(fig_wr, use_container_width=True)

        with col_q3:
            st.markdown("##### Cierre con ventaja en Q3")
            dh = df_hdr[df_hdr["season_code"] == season].copy()
            for lado in ["a", "b"]:
                dh[f"sq3_{lado}"] = (
                    dh[f"score_quarter_1_{lado}"] +
                    dh[f"score_quarter_2_{lado}"] +
                    dh[f"score_quarter_3_{lado}"]
                )
            da  = dh[dh["team_id_a"] == team].copy()
            da["lead_q3"] = da["sq3_a"] - da["sq3_b"]
            da["won"]     = (da["score_a"] > da["score_b"]).astype(int)
            db_ = dh[dh["team_id_b"] == team].copy()
            db_["lead_q3"] = db_["sq3_b"] - db_["sq3_a"]
            db_["won"]     = (db_["score_b"] > db_["score_a"]).astype(int)
            dq3 = pd.concat([da[["lead_q3", "won"]], db_[["lead_q3", "won"]]], ignore_index=True)
            sub = dq3[dq3["lead_q3"] >= umbral]

            if sub.empty:
                st.info(f"Sin partidos con ventaja ≥{umbral} pts en Q3 esta temporada.")
            else:
                victorias   = int(sub["won"].sum())
                derrotas    = len(sub) - victorias
                efectividad = round(sub["won"].mean() * 100, 1)
                m1, m2, m3  = st.columns(3)
                m1.metric("Partidos", len(sub),          help=f"Con ≥{umbral} pts al cierre del Q3")
                m2.metric("Victorias", victorias)
                m3.metric("Efectividad", f"{efectividad}%")
                fig_q3 = px.bar(
                    pd.DataFrame({"Resultado": ["Victoria", "Derrota"], "Partidos": [victorias, derrotas]}),
                    x="Resultado", y="Partidos", color="Resultado",
                    color_discrete_map={"Victoria": "#2ecc71", "Derrota": "#e74c3c"},
                    text="Partidos",
                )
                fig_q3.update_traces(textposition="outside")
                fig_q3.update_layout(
                    showlegend=False,
                    yaxis=dict(range=[0, max(victorias, derrotas) * 1.3]),
                    margin=dict(t=20),
                )
                dark_layout(fig_q3)
                st.plotly_chart(fig_q3, use_container_width=True)
