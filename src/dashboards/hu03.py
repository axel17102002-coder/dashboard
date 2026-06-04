import streamlit as st
import plotly.express as px
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from db import load_season_players, load_shot_data, dark_layout, draw_shot_map, make_radar

#prueba-conexion
def render():
    st.header("Dashboard — Analista Deportivo")
    st.caption("Patrones tácticos y eficiencia de equipos")

    comp = st.selectbox("Competición", ["EuroLeague", "EuroCup", "Ambas"], key="h3_comp")

    try:
        df_sp = load_season_players(comp)
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

    c1, c2 = st.columns(2)
    season = c1.selectbox("Temporada", sorted(df_sp["season_code"].unique()), key="h3_sea")
    teams  = sorted(df_sp[df_sp["season_code"]==season]["team_id"].unique())
    team   = c2.selectbox("Equipo", teams, key="h3_team")

    st.divider()
    tabs = st.tabs(["🗺️ Mapa de Aciertos","🕸️ Comparación de Perfiles","📈 Volumen Ofensivo"])

    # Tab 1 — Shot map
    with tabs[0]:
        df_tsp = df_sp[(df_sp["season_code"]==season) & (df_sp["team_id"]==team)]
        jugadores = sorted(df_tsp["player"].unique())
        if not jugadores:
            st.info("Sin jugadores para los filtros seleccionados.")
        else:
            c_jug, c_mint = st.columns([2, 1])
            jug_shot = c_jug.selectbox("Jugador", jugadores, key="h3_sjug")
            min_int  = c_mint.slider("Mín. intentos/zona", 1, 20, 5, key="h3_mint")
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
        modo_radar = st.radio("Modo", ["Ofensivo","Defensivo"], horizontal=True, key="h3_modo")
        radar_cols = ["player","points_per_game","assists_per_game","efg_pct","ts_pct",
                      "offensive_rebounds_per_game","usg_pct","defensive_rebounds_per_game",
                      "steals_per_game","blocks_favour_per_game","ast_to_ratio",
                      "fouls_received_per_game","total_rebounds_per_game"]
        df_radar = df_sp[df_sp["season_code"]==season][radar_cols].dropna()
        all_players = sorted(df_radar["player"].unique())
        if len(all_players) < 2:
            st.info("Sin suficientes jugadores para comparar.")
        else:
            c_pa, c_pb = st.columns(2)
            pa = c_pa.selectbox("Jugador A", all_players, key="h3_pa")
            pb = c_pb.selectbox("Jugador B", [p for p in all_players if p != pa], key="h3_pb")
            df_radar_dedup = df_radar.drop_duplicates(subset="player", keep="first")
            st.plotly_chart(make_radar(df_radar_dedup, pa, pb, modo_radar), use_container_width=True)

    # Tab 3 — Scatter USG% vs TS%
    with tabs[2]:
        st.caption("USG% vs TS% · Color por perfil ofensivo · Líneas = promedios de liga")
        df_sc = df_sp[
            (df_sp["season_code"]==season) &
            (df_sp["usg_pct"]>0) & (df_sp["ts_pct"]>0)
        ].dropna(subset=["usg_pct","ts_pct"])

        if df_sc.empty:
            st.info("Sin datos para los filtros seleccionados.")
        else:
            avg_usg = df_sc["usg_pct"].mean()
            avg_ts  = df_sc["ts_pct"].mean()

            fig_sc = px.scatter(
                df_sc, x="usg_pct", y="ts_pct", color="perfil_ofensivo",
                color_discrete_map={"perimetral":"#3498db","interior":"#e74c3c","mixto":"#2ecc71"},
                hover_data=["player","team_id"],
                labels={"usg_pct":"USG%","ts_pct":"TS%","perfil_ofensivo":"Perfil"},
                opacity=0.75,
            )
            fig_sc.add_vline(x=avg_usg, line_dash="dash", line_color="white",
                             annotation_text=f"Media USG% {avg_usg:.3f}",
                             annotation_font_color="white")
            fig_sc.add_hline(y=avg_ts, line_dash="dash", line_color="white",
                             annotation_text=f"Media TS% {avg_ts:.3f}",
                             annotation_font_color="white")
            fig_sc.update_layout(margin=dict(t=20))
            dark_layout(fig_sc)
            st.plotly_chart(fig_sc, use_container_width=True)
