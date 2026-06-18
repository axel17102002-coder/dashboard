import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np
import plotly.graph_objects as go
from db import load_game_headers, load_season_players, load_season_teams, build_winrate_df, dark_layout

_NO_WR   = "No hay datos suficientes para calcular el porcentaje de victorias."
_NO_DISP = "No hay datos suficientes para calcular la disponibilidad del jugador."


def _render_winrate(df_hdr, team, seasons_sel):
    st.subheader("Win Rate por Temporada y Fase")
    st.caption("Solo se muestran temporadas con datos completos (Regular + Playoffs)")

    df_wr = build_winrate_df(df_hdr)
    wrh = (
        df_wr[(df_wr["team"] == team) & (df_wr["season_code"].isin(seasons_sel))]
        .groupby(["season_code", "phase"])
        .agg(partidos=("won", "count"), victorias=("won", "sum"))
        .reset_index()
    )
    if wrh.empty:
        return st.warning(_NO_WR)

    wrh["win_rate"] = (wrh["victorias"] / wrh["partidos"] * 100).round(1)
    temporadas_ok   = wrh.groupby("season_code")["phase"].nunique()
    wrh = wrh[wrh["season_code"].isin(temporadas_ok[temporadas_ok >= 2].index)].sort_values("season_code")

    if wrh.empty:
        return st.warning(_NO_WR)

    # KPI: promedios globales
    total_p  = wrh["partidos"].sum()
    total_v  = wrh["victorias"].sum()
    wr_global = round(total_v / total_p * 100, 1) if total_p else 0
    k1, k2, k3 = st.columns(3)
    k1.metric("Partidos totales",    int(total_p))
    k2.metric("Victorias totales",   int(total_v))
    k3.metric("Win Rate promedio",   f"{wr_global}%")
    pass  # divider removed

    fig = px.bar(
        wrh, x="season_code", y="win_rate", color="phase", barmode="group",
        text="win_rate",
        labels={"season_code": "Temporada", "win_rate": "Win Rate (%)", "phase": "Fase"},
        color_discrete_sequence=px.colors.qualitative.Set2,
        custom_data=["victorias", "partidos"],
    )
    fig.update_traces(
        texttemplate="%{text:.1f}%", textposition="outside",
        textfont=dict(color="white"),
        hovertemplate=(
            "<b>%{x}</b><br>Fase: %{fullData.name}<br>"
            "Win Rate: %{y:.1f}%<br>Victorias: %{customdata[0]} / %{customdata[1]}<extra></extra>"
        ),
    )
    fig.update_layout(
        xaxis=dict(tickangle=45, categoryorder="category ascending"),
        yaxis=dict(range=[0, 115], title="Win Rate (%)"),
        legend=dict(bgcolor="#1a1a2e", font=dict(color="white", size=13)),
        margin=dict(t=30),
    )
    dark_layout(fig)
    st.plotly_chart(fig, use_container_width=True)


def _render_pir(df_teams, team, seasons_sel):
    st.subheader("Evolución Anual — PIR Global del Equipo")
    st.caption("Performance Index Rating promedio por partido a lo largo de las temporadas")

    df_tpir = (
        df_teams[(df_teams["team_id"] == team) & (df_teams["season_code"].isin(seasons_sel))]
        .sort_values("season_code")
    )
    if df_tpir.empty:
        return st.info("Sin datos de equipo para el rango seleccionado.")

    ultimo_pir = df_tpir["valuation_per_game"].iloc[-1]
    primer_pir = df_tpir["valuation_per_game"].iloc[0]
    delta_pir  = round(ultimo_pir - primer_pir, 1)
    k1, k2, k3 = st.columns(3)
    k1.metric("PIR últ. temporada",   f"{ultimo_pir:.1f}")
    k2.metric("PIR primer temporada", f"{primer_pir:.1f}")
    k3.metric("Variación",            f"{delta_pir:+.1f}", delta=delta_pir)
    pass  # divider removed

    fig = px.line(
        df_tpir, x="season_code", y="valuation_per_game", markers=True,
        labels={"season_code": "Temporada", "valuation_per_game": "PIR promedio/partido"},
    )
    fig.update_traces(line_color="#f39c12", marker_color="#f39c12", marker_size=8)
    fig.update_layout(xaxis=dict(tickangle=45), margin=dict(t=20))
    dark_layout(fig)
    st.plotly_chart(fig, use_container_width=True)


def _render_disponibilidad(df_sp, df_hdr, team, seasons_sel):
    st.subheader("Disponibilidad Histórica de Jugadores")
    st.caption("% de partidos jugados sobre el total de la temporada")

    dh = df_hdr[df_hdr["season_code"].isin(seasons_sel)]
    df_tot = (
        pd.concat([
            dh[dh["team_id_a"] == team].groupby("season_code").size().reset_index(name="n"),
            dh[dh["team_id_b"] == team].groupby("season_code").size().reset_index(name="n"),
        ])
        .groupby("season_code")["n"].sum()
        .reset_index(name="total")
    )

    df_disp = (
        df_sp[(df_sp["team_id"] == team) & (df_sp["season_code"].isin(seasons_sel))]
        [["player", "season_code", "games_played"]]
        .merge(df_tot, on="season_code", how="left")
        .assign(
            games_played=lambda d: pd.to_numeric(d["games_played"], errors="coerce"),
            total=lambda d: pd.to_numeric(d["total"], errors="coerce"),
        )
    )
    df_disp = df_disp[df_disp["games_played"] > 0].copy()
    df_disp["disponibilidad"] = (df_disp["games_played"] / df_disp["total"] * 100).clip(0, 100).round(1)

    if df_disp.empty:
        return st.warning(_NO_DISP)

    # KPI disponibilidad
    avg_disp   = df_disp["disponibilidad"].mean()
    alta_disp  = (df_disp["disponibilidad"] >= 80).sum()
    baja_disp  = (df_disp["disponibilidad"] < 50).sum()
    k1, k2, k3 = st.columns(3)
    k1.metric("Disponibilidad promedio", f"{avg_disp:.1f}%")
    k2.metric("Alta disponibilidad (≥80%)", int(alta_disp),  help="Filas jugador-temporada con ≥80%")
    k3.metric("Baja disponibilidad (<50%)", int(baja_disp),  help="Filas jugador-temporada con <50%")
    pass  # divider removed

    jugador_sel = st.multiselect(
        "Filtrar por jugador (opcional — vacío = todos)",
        options=sorted(df_disp["player"].unique()), default=[],
        key="h4_jugador",
    )
    if jugador_sel:
        df_disp = df_disp[df_disp["player"].isin(jugador_sel)]
    if df_disp.empty:
        return st.warning(_NO_DISP)

    pivot     = df_disp.pivot_table(index="player", columns="season_code", values="disponibilidad", aggfunc="mean").fillna(0)
    pivot_gp  = df_disp.pivot_table(index="player", columns="season_code", values="games_played",   aggfunc="sum").fillna(0).reindex_like(pivot).fillna(0)
    pivot_tot = df_disp.pivot_table(index="player", columns="season_code", values="total",           aggfunc="mean").fillna(0).reindex_like(pivot).fillna(0)

    fig = go.Figure(go.Heatmap(
        z=pivot.values.tolist(),
        x=list(pivot.columns.astype(str)),
        y=list(pivot.index),
        customdata=np.dstack([pivot_gp.values, pivot_tot.values]),
        colorscale=[(0, "#e74c3c"), (0.5, "#f39c12"), (0.85, "#2ecc71"), (1, "#27ae60")],
        zmin=0, zmax=100,
        text=[[f"{v:.0f}" for v in row] for row in pivot.values.tolist()],
        texttemplate="%{text}", textfont=dict(color="white"),
        colorbar=dict(
            title=dict(text="Disp. %", font=dict(color="white")),
            tickfont=dict(color="white"),
        ),
        hovertemplate=(
            "<b>%{y}</b><br>Temporada: %{x}<br>"
            "Partidos disputados: <b>%{customdata[0]:.0f}</b><br>"
            "Partidos totales: <b>%{customdata[1]:.0f}</b><br>"
            "Disponibilidad: <b>%{z:.1f}%</b><extra></extra>"
        ),
    ))
    fig.update_layout(
        paper_bgcolor="#0f0f1a", font_color="white", margin=dict(t=20),
        xaxis=dict(tickfont=dict(color="white")),
        yaxis=dict(tickfont=dict(color="white"), autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True)


def render():
    with st.sidebar:
        st.markdown("### Filtros")
        comp = st.selectbox(
            "Competición", ["EuroLeague", "EuroCup", "Ambas"], key="h4_comp",
            help="Filtra todos los módulos por competición",
        )
    try:
        df_hdr   = load_game_headers(comp)
        df_sp    = load_season_players(comp)
        df_teams = load_season_teams(comp)
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

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

    team_label_to_id = dict(
        zip(df_team_names["team_name"], df_team_names["team_id"])
    )

    all_seasons = sorted(df_sp["season_code"].unique())
    with st.sidebar:
        team_label = st.selectbox("Equipo", sorted(team_label_to_id.keys()), key="h4_team")
        team = team_label_to_id[team_label]
        season_desde = st.selectbox("Desde temporada", all_seasons, key="h4_desde",
                                    help="Inicio del rango a analizar")
        opciones_hasta = [s for s in all_seasons if s >= season_desde]
        season_hasta   = st.selectbox("Hasta temporada", opciones_hasta,
                                      index=len(opciones_hasta) - 1, key="h4_hasta",
                                      help="Fin del rango a analizar")
    seasons_sel = [s for s in all_seasons if season_desde <= s <= season_hasta]

    if not seasons_sel:
        st.warning("Seleccioná al menos una temporada para visualizar los módulos.")
        st.stop()

    pass  # divider removed

    tab1, tab2, tab3 = st.tabs(["📊 Win Rate", "📈 Evolución PIR", "🗓️ Disponibilidad"])

    with tab1:
        _render_winrate(df_hdr, team, seasons_sel)

    with tab2:
        _render_pir(df_teams, team, seasons_sel)

    with tab3:
        _render_disponibilidad(df_sp, df_hdr, team, seasons_sel)