import pandas as pd
import streamlit as st
import plotly.express as px
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from db import (
    load_season_players,
    load_shot_data,
    load_league_zone_avg,
    load_game_headers,
    dark_layout,
    make_shot_map,
    make_radar,
    format_season
)
from report_utils import render_table_report


def render():
    with st.sidebar:
        st.markdown("### Filtros")
        comp = st.selectbox(
            "Competición", ["EuroLeague", "EuroCup", "Ambas"], key="h3_comp",
            help="Filtra todos los módulos por competición",
        )

    try:
        df_sp = load_season_players(comp)
        df_hdr = load_game_headers(comp)
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

    season_codes  = sorted(df_sp["season_code"].dropna().unique())
    season_labels = {format_season(s): s for s in season_codes}

    if not season_labels:
        st.warning(
            "No hay datos disponibles. Pedile al administrador que cargue los datos "
            "desde el panel de Administración."
        )
        st.stop()

    with st.sidebar:
        season = season_labels[st.selectbox(
            "Temporada", list(season_labels.keys()), key="h1_sea",
        )]

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
        df_sp[df_sp["season_code"] == season]["team_id"]
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

    with st.sidebar:
        _opts_team = ["Todos"] + list(team_label_to_id.keys())
        team_label = st.selectbox(
            "Equipo", _opts_team,
            index=_opts_team.index("REAL MADRID") if "REAL MADRID" in _opts_team else 0,
            format_func=str.title,
            key="h3_team",
        )
        team = None if team_label == "Todos" else team_label_to_id[team_label]

    pass  # divider removed

    tabs = st.tabs([
        "🗺️ Mapa de Aciertos",
        "🕸️ Comparación de Perfiles",
        "📈 Volumen Ofensivo"
    ])

    # Tab 1 — Shot map
    with tabs[0]:
        df_tsp = df_sp[
            (df_sp["season_code"] == season)
        ]

        if team is not None:
            df_tsp = df_tsp[df_tsp["team_id"] == team]

        jugadores = sorted(df_tsp["player"].dropna().unique())

        if not jugadores:
            st.info("Sin jugadores para los filtros seleccionados.")
        else:
            col_filtros, col_mapa = st.columns([1, 2])

            with col_filtros:
                st.markdown("##### Filtros")
                jug_shot = st.selectbox(
                    "Jugador", jugadores,
                    index=jugadores.index("MUMBRU, ALEX") if "MUMBRU, ALEX" in jugadores else 0,
                    format_func=str.title,
                    key="h3_sjug",
                    help="Jugador a analizar",
                )
                min_int = st.slider(
                    "Mín. intentos por zona", 1, 20, 5, key="h3_mint",
                    help="Zonas con menos intentos se ocultan del mapa",
                )
                vs_liga = st.toggle(
                    "Comparar vs promedio de liga", value=False, key="h3_vsliga",
                    help="Colorea cada zona según cuánto mejor/peor tira el jugador "
                         "respecto a la media de la liga",
                )
                pass  # divider removed
                if vs_liga:
                    st.caption("🟢 Tira mejor que la liga")
                    st.caption("🟡 Cerca de la media")
                    st.caption("🔴 Tira peor que la liga")
                else:
                    st.caption("🔴 Efectividad ≤ 29%")
                    st.caption("🟡 Efectividad 30% – 49%")
                    st.caption("🟢 Efectividad ≥ 50%")
                st.caption("Tamaño del círculo = volumen de intentos")

            with col_mapa:
                try:
                    df_shots = load_shot_data(jug_shot, comp, season)
                    if df_shots.empty:
                        st.info("Sin datos de tiros para este jugador/temporada.")
                    else:
                        df_liga = load_league_zone_avg(comp, season) if vs_liga else None
                        fig_court = make_shot_map(df_shots, min_int, df_liga)
                        st.plotly_chart(fig_court, use_container_width=True)

                        tabla_shot = (
                            df_shots.groupby("zone")
                            .agg(
                                intentos=("action_id", "count"),
                                aciertos=("action_id", lambda x: x.str.endswith("M").sum()),
                            )
                            .reset_index()
                        )
                        tabla_shot = tabla_shot[tabla_shot["intentos"] >= min_int].copy()

                        if not tabla_shot.empty:
                            tabla_shot["efectividad"] = (
                                tabla_shot["aciertos"] / tabla_shot["intentos"] * 100
                            ).round(1)
                            tabla_shot = tabla_shot.sort_values(
                                ["efectividad", "intentos"],
                                ascending=[False, False]
                            )

                            render_table_report(
                                tabla_shot,
                                title="Datos del mapa de aciertos",
                                columns=["zone", "intentos", "aciertos", "efectividad"],
                                rename_columns={
                                    "zone": "Zona",
                                    "intentos": "Intentos",
                                    "aciertos": "Aciertos",
                                    "efectividad": "Efectividad %",
                                },
                            )
                except Exception as e:
                    st.error(f"Error cargando tiros: {e}")

    # Tab 2 — Radar
    with tabs[1]:
        modo_radar = st.radio(
            "Modo",
            ["Ofensivo", "Defensivo"],
            horizontal=True,
            key="h3_modo"
        )

        radar_cols = [
            "player",
            "points_per_game",
            "assists_per_game",
            "efg_pct",
            "ts_pct",
            "offensive_rebounds_per_game",
            "usg_pct",
            "defensive_rebounds_per_game",
            "steals_per_game",
            "blocks_favour_per_game",
            "ast_to_ratio",
            "fouls_received_per_game",
            "total_rebounds_per_game"
        ]

        # Toda la liga/competición de la temporada: se usa para normalizar
        df_radar_all = (
            df_sp[
                (df_sp["season_code"] == season)
            ][radar_cols]
            .dropna()
        )

        # Datos filtrados: solo se usan para limitar la selección de jugadores
        df_radar = df_radar_all.copy()

        if team is not None:
            df_radar = df_sp[
                (df_sp["season_code"] == season) &
                (df_sp["team_id"] == team)
            ][radar_cols].dropna()

        all_players = sorted(df_radar["player"].dropna().unique())

        if len(all_players) < 2:
            st.info("Sin suficientes jugadores para comparar.")
        else:
            c_pa, c_pb = st.columns(2)

            pa = c_pa.selectbox("Jugador A", all_players, format_func=str.title, key="h3_pa")
            pb = c_pb.selectbox(
                "Jugador B",
                [p for p in all_players if p != pa],
                format_func=str.title,
                key="h3_pb"
            )

            df_radar_dedup = df_radar.drop_duplicates(subset="player", keep="first")
            df_radar_all_dedup = df_radar_all.drop_duplicates(subset="player", keep="first")

            st.plotly_chart(
                make_radar(df_radar_all_dedup, pa, pb, modo_radar),
                use_container_width=True
            )

            if modo_radar == "Ofensivo":
                cols_tabla = [
                    "points_per_game",
                    "assists_per_game",
                    "efg_pct",
                    "ts_pct",
                    "offensive_rebounds_per_game",
                    "usg_pct"
                ]
                labels_tabla = ["PTS/G", "AST/G", "eFG%", "TS%", "OREB/G", "USG%"]
            else:
                cols_tabla = [
                    "defensive_rebounds_per_game",
                    "steals_per_game",
                    "blocks_favour_per_game",
                    "ast_to_ratio",
                    "fouls_received_per_game",
                    "total_rebounds_per_game"
                ]
                labels_tabla = ["DREB/G", "STL/G", "BLK/G", "AST/TO", "Faltas Rec/G", "REB/G"]

            df_norm_tabla = df_radar_all_dedup.set_index("player")[cols_tabla].copy()
            df_norm_tabla = (df_norm_tabla - df_norm_tabla.min()) / (df_norm_tabla.max() - df_norm_tabla.min() + 1e-9)

            tabla_comparativa = pd.DataFrame({
                "Estadística": labels_tabla,
                pa: [f"{v * 100:.2f}%" for v in df_norm_tabla.loc[pa, cols_tabla]],
                pb: [f"{v * 100:.2f}%" for v in df_norm_tabla.loc[pb, cols_tabla]],
            })

            st.markdown("#### Tabla comparativa")
            st.dataframe(tabla_comparativa, use_container_width=True, hide_index=True)

            

    # Tab 3 — Scatter USG% vs TS%
    with tabs[2]:
        st.caption(
            "USG% vs TS% · Color por perfil ofensivo · Líneas = promedios de liga"
        )

        # Toda la liga/competición de la temporada: se usa para calcular las medias
        df_sc_all = df_sp[
            (df_sp["season_code"] == season) &
            (df_sp["usg_pct"] > 0) &
            (df_sp["ts_pct"] > 0)
        ].dropna(subset=["usg_pct", "ts_pct"]).copy()

        # Datos mostrados: se filtran por equipo solo si corresponde
        df_sc = df_sc_all.copy()

        if team is not None:
            df_sc = df_sc[df_sc["team_id"] == team]

        if df_sc.empty:
            st.info("No existen datos suficientes para generar la visualización seleccionada.")
        else:
            avg_usg = df_sc_all["usg_pct"].mean()
            avg_ts  = df_sc_all["ts_pct"].mean()

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Jugadores analizados", len(df_sc))
            k2.metric("USG% promedio liga",  f"{avg_usg:.1%}", help="Usage Rate promedio")
            k3.metric("TS% promedio liga",   f"{avg_ts:.1%}",  help="True Shooting promedio")
            estrellas = df_sc[(df_sc["usg_pct"] >= avg_usg) & (df_sc["ts_pct"] >= avg_ts)]
            k4.metric("Alto vol. + alta ef.", len(estrellas),  help="Jugadores en el cuadrante superior derecho")
            pass  # divider removed

            def clasificar_perfil_ofensivo(row):
                if row["usg_pct"] >= avg_usg and row["ts_pct"] >= avg_ts:
                    return "Estrella eficiente"
                elif row["usg_pct"] < avg_usg and row["ts_pct"] >= avg_ts:
                    return "Especialista eficiente"
                elif row["usg_pct"] >= avg_usg and row["ts_pct"] < avg_ts:
                    return "Alto volumen ineficiente"
                else:
                    return "Bajo impacto ofensivo"

            df_sc["perfil_scatter"] = df_sc.apply(clasificar_perfil_ofensivo, axis=1)

            orden_perfiles = [
                "Estrella eficiente",
                "Especialista eficiente",
                "Alto volumen ineficiente",
                "Bajo impacto ofensivo"
            ]

            colores_perfiles = {
                "Estrella eficiente": "#2ecc71",
                "Especialista eficiente": "#3498db",
                "Alto volumen ineficiente": "#f1c40f",
                "Bajo impacto ofensivo": "#e74c3c"
            }

            fig_sc = px.scatter(
                df_sc,
                x="usg_pct",
                y="ts_pct",
                color="perfil_scatter",
                category_orders={
                    "perfil_scatter": orden_perfiles
                },
                color_discrete_map=colores_perfiles,
                hover_data={
                    "player": True,
                    "team_id": True,
                    "usg_pct": ":.1%",
                    "ts_pct": ":.1%",
                    "perfil_scatter": True,
                    "perfil_ofensivo": False
                },
                labels={
                    "usg_pct": "USG%",
                    "ts_pct": "TS%",
                    "perfil_scatter": "Perfil ofensivo",
                    "player": "Jugador",
                    "team_id": "Equipo"
                },
                opacity=0.75,
            )

            fig_sc.add_vline(
                x=avg_usg,
                line_dash="dash",
                line_color="#14140f",
                annotation_text=f"Media USG% {avg_usg:.1%}",
                annotation_font_color="#14140f"
            )

            fig_sc.add_hline(
                y=avg_ts,
                line_dash="dash",
                line_color="#14140f",
                annotation_text=f"Media TS% {avg_ts:.1%}",
                annotation_font_color="#14140f"
            )

            fig_sc.update_traces(
                marker=dict(size=8)
            )
            fig_sc.update_xaxes(tickformat=".0%")
            fig_sc.update_yaxes(tickformat=".0%")
            dark_layout(fig_sc)

            fig_sc.update_layout(
                margin=dict(t=20),
                legend_title_text="Perfil ofensivo",
                legend=dict(
                    font=dict(
                        color="#14140f",
                        size=12
                    ),
                    title=dict(
                        font=dict(
                            color="#14140f",
                            size=13
                        )
                    )
                )
            )

            st.plotly_chart(fig_sc, use_container_width=True)
            tabla_scatter = df_sc.copy()
            tabla_scatter["usg_pct"] = (tabla_scatter["usg_pct"] * 100).round(1)
            tabla_scatter["ts_pct"] = (tabla_scatter["ts_pct"] * 100).round(1)
            render_table_report(
                tabla_scatter,
                title="Datos de volumen ofensivo",
                columns=["player", "team_id", "usg_pct", "ts_pct", "perfil_scatter"],
                rename_columns={
                    "player": "Jugador",
                    "team_id": "Equipo",
                    "usg_pct": "USG%",
                    "ts_pct": "TS%",
                    "perfil_scatter": "Perfil ofensivo",
                },
            )