import pandas as pd
import streamlit as st
import plotly.express as px
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from db import (
    load_season_players,
    load_shot_data,
    load_game_headers,
    dark_layout,
    draw_shot_map,
    make_radar,
    format_season
)


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
        team_label = st.selectbox(
            "Equipo", list(team_label_to_id.keys()), key="h3_team",
        )
        team = team_label_to_id[team_label]

    pass  # divider removed

    tabs = st.tabs([
        "🗺️ Mapa de Aciertos",
        "🕸️ Comparación de Perfiles",
        "📈 Volumen Ofensivo"
    ])

    # Tab 1 — Shot map
    with tabs[0]:
        df_tsp = df_sp[
            (df_sp["season_code"] == season) &
            (df_sp["team_id"] == team)
        ]

        jugadores = sorted(df_tsp["player"].dropna().unique())

        if not jugadores:
            st.info("Sin jugadores para los filtros seleccionados.")
        else:
            col_filtros, col_mapa = st.columns([1, 2])

            with col_filtros:
                st.markdown("##### Filtros")
                jug_shot = st.selectbox(
                    "Jugador", jugadores, key="h3_sjug",
                    help="Jugador a analizar",
                )
                min_int = st.slider(
                    "Mín. intentos por zona", 1, 20, 5, key="h3_mint",
                    help="Zonas con menos intentos se ocultan del mapa",
                )
                pass  # divider removed
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
                        fig_court = draw_shot_map(df_shots, min_int)
                        st.pyplot(fig_court, use_container_width=True)
                        plt.close(fig_court)
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

        df_radar = (
            df_sp[
                (df_sp["season_code"] == season) &
                (df_sp["team_id"] == team)
            ][radar_cols]
            .dropna()
        )

        all_players = sorted(df_radar["player"].dropna().unique())

        if len(all_players) < 2:
            st.info("Sin suficientes jugadores para comparar.")
        else:
            c_pa, c_pb = st.columns(2)

            pa = c_pa.selectbox("Jugador A", all_players, key="h3_pa")
            pb = c_pb.selectbox(
                "Jugador B",
                [p for p in all_players if p != pa],
                key="h3_pb"
            )

            df_radar_dedup = df_radar.drop_duplicates(subset="player", keep="first")

            st.plotly_chart(
                make_radar(df_radar_dedup, pa, pb, modo_radar),
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

            df_norm_tabla = df_radar_dedup.set_index("player")[cols_tabla].copy()
            df_norm_tabla = (df_norm_tabla - df_norm_tabla.min()) / (df_norm_tabla.max() - df_norm_tabla.min() + 1e-9)

            tabla_comparativa = pd.DataFrame({
                "Estadística": labels_tabla,
                pa: [f"{v * 100:.2f}%" for v in df_norm_tabla.loc[pa, cols_tabla]],
                pb: [f"{v * 100:.2f}%" for v in df_norm_tabla.loc[pb, cols_tabla]],
            })

            st.markdown("#### Tabla comparativa")
            st.dataframe(tabla_comparativa, use_container_width=True, hide_index=True)

            csv = tabla_comparativa.to_csv(index=False).encode("utf-8-sig")

            st.download_button(
                label="⬇️ Descargar",
                data=csv,
                file_name=f"comparacion_radar_{pa}_vs_{pb}_{modo_radar}.csv",
                mime="text/csv"
            )

    # Tab 3 — Scatter USG% vs TS%
    with tabs[2]:
        st.caption(
            "USG% vs TS% · Color por posición de juego · Líneas = promedios de liga"
        )

        df_sc = df_sp[
            (df_sp["season_code"] == season) &
            (df_sp["usg_pct"] > 0) &
            (df_sp["ts_pct"] > 0)
        ].dropna(subset=["usg_pct", "ts_pct"]).copy()

        if df_sc.empty:
            st.info("No existen datos suficientes para generar la visualización seleccionada.")
        else:
            avg_usg = df_sc["usg_pct"].mean()
            avg_ts  = df_sc["ts_pct"].mean()

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
                    "usg_pct": ":.3f",
                    "ts_pct": ":.3f",
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
                line_color="white",
                annotation_text=f"Media USG% {avg_usg:.3f}",
                annotation_font_color="white"
            )

            fig_sc.add_hline(
                y=avg_ts,
                line_dash="dash",
                line_color="white",
                annotation_text=f"Media TS% {avg_ts:.3f}",
                annotation_font_color="white"
            )

            fig_sc.update_traces(
                marker=dict(size=8)
            )

            dark_layout(fig_sc)

            fig_sc.update_layout(
                margin=dict(t=20),
                legend_title_text="Perfil ofensivo",
                legend=dict(
                    font=dict(
                        color="white",
                        size=12
                    ),
                    title=dict(
                        font=dict(
                            color="white",
                            size=13
                        )
                    )
                )
            )

            st.plotly_chart(fig_sc, use_container_width=True)