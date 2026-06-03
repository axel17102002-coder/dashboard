import pandas as pd
import streamlit as st
import plotly.express as px
from db import load_game_headers, load_season_players, load_season_teams, build_winrate_df, dark_layout


def render():
    st.header("Dashboard — Directivo del Club")
    st.caption("Consistencia competitiva · Crecimiento institucional · Planificación a largo plazo")

    comp = st.selectbox("Competición", ["EuroLeague", "EuroCup", "Ambas"], key="h4_comp")

    try:
        df_hdr   = load_game_headers(comp)
        df_sp    = load_season_players(comp)
        df_teams = load_season_teams(comp)
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

    all_teams   = sorted(df_sp["team_id"].unique())
    all_seasons = sorted(df_sp["season_code"].unique())

    c1, c2, c3 = st.columns(3)
    team         = c1.selectbox("Equipo", all_teams, key="h4_team")
    season_desde = c2.selectbox("Desde temporada", all_seasons, key="h4_desde")
    opciones_hasta = [s for s in all_seasons if s >= season_desde]
    season_hasta = c3.selectbox(
        "Hasta temporada",
        opciones_hasta,
        index=len(opciones_hasta)-1,
        key="h4_hasta",
    )
    seasons_sel = [s for s in all_seasons if season_desde <= s <= season_hasta]

    st.divider()

    col_l, col_r = st.columns(2)

    # Win Rate histórico
    with col_l:
        st.subheader("Win Rate Histórico por Fase")
        df_wr  = build_winrate_df(df_hdr)
        df_twh = df_wr[(df_wr["team"]==team) & (df_wr["season_code"].isin(seasons_sel))]
        if df_twh.empty:
            st.info("Sin datos de resultados para este equipo en el rango seleccionado.")
        else:
            wrh = df_twh.groupby(["season_code","phase"]).agg(
                p=("won","count"), v=("won","sum")
            ).reset_index()
            wrh["win_rate"] = (wrh["v"]/wrh["p"]*100).round(1)
            fig_wrh = px.line(wrh, x="season_code", y="win_rate", color="phase", markers=True,
                              labels={"season_code":"Temporada","win_rate":"Win Rate %","phase":"Fase"})
            fig_wrh.update_layout(xaxis=dict(tickangle=45), yaxis=dict(range=[0,110]),
                                   legend=dict(bgcolor="#1a1a2e"), margin=dict(t=20))
            dark_layout(fig_wrh)
            st.plotly_chart(fig_wrh, use_container_width=True)

    # PIR global del equipo
    with col_r:
        st.subheader("Evolución Anual — PIR Global del Equipo")
        df_tpir = df_teams[
            (df_teams["team_id"]==team) & (df_teams["season_code"].isin(seasons_sel))
        ].sort_values("season_code")
        if df_tpir.empty:
            st.info("Sin datos de equipo para el rango seleccionado.")
        else:
            fig_pir = px.line(df_tpir, x="season_code", y="valuation_per_game", markers=True,
                              labels={"season_code":"Temporada","valuation_per_game":"PIR promedio/partido"})
            fig_pir.update_traces(line_color="#f39c12", marker_color="#f39c12")
            fig_pir.update_layout(xaxis=dict(tickangle=45), margin=dict(t=20))
            dark_layout(fig_pir)
            st.plotly_chart(fig_pir, use_container_width=True)

    st.divider()

    # Disponibilidad histórica
    st.subheader("Disponibilidad Histórica de Jugadores")
    st.caption("% partidos jugados sobre el total de la temporada")

    dh_sel = df_hdr[df_hdr["season_code"].isin(seasons_sel)]
    tot_a  = dh_sel[dh_sel["team_id_a"]==team].groupby("season_code").size().reset_index(name="n")
    tot_b  = dh_sel[dh_sel["team_id_b"]==team].groupby("season_code").size().reset_index(name="n")
    df_tot = pd.concat([tot_a, tot_b]).groupby("season_code")["n"].sum().reset_index(name="total")

    df_disp = df_sp[(df_sp["team_id"]==team) & (df_sp["season_code"].isin(seasons_sel))][
        ["player","season_code","games_played"]
    ].merge(df_tot, on="season_code", how="left")

    df_disp["games_played"] = pd.to_numeric(df_disp["games_played"], errors="coerce")
    df_disp["total"]        = pd.to_numeric(df_disp["total"], errors="coerce")
    df_disp["disponibilidad"] = (df_disp["games_played"] / df_disp["total"] * 100).clip(0,100).round(1)

    if df_disp.empty:
        st.info("Sin datos de jugadores para el equipo y rango seleccionados.")
    else:
        pivot = df_disp.pivot_table(index="player", columns="season_code",
                                     values="disponibilidad", aggfunc="mean").fillna(0)
        fig_heat = px.imshow(
            pivot,
            color_continuous_scale=[(0,"#e74c3c"),(0.85,"#f39c12"),(1,"#2ecc71")],
            zmin=0, zmax=100,
            labels=dict(x="Temporada", y="Jugador", color="Disp. %"),
            text_auto=".0f", aspect="auto",
        )
        fig_heat.update_layout(paper_bgcolor="#0f0f1a", font_color="white", margin=dict(t=20))
        fig_heat.update_traces(textfont_color="white")
        st.plotly_chart(fig_heat, use_container_width=True)
