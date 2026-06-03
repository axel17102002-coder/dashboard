import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from db import load_box_scores, load_game_headers, build_winrate_df, dark_layout


def render():
    st.header("Dashboard — Entrenador")
    st.caption("Rendimiento individual · Decisiones tácticas")

    comp = st.selectbox("Competición", ["EuroLeague", "EuroCup", "Ambas"], key="h1_comp")

    try:
        df_box = load_box_scores(comp)
        df_hdr = load_game_headers(comp)
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

    c1, c2, c3 = st.columns(3)
    season = c1.selectbox("Temporada", sorted(df_box["season_code"].unique()), key="h1_sea")
    teams  = sorted(df_box[df_box["season_code"]==season]["team_id"].unique())
    team   = c2.selectbox("Equipo", teams, key="h1_team")
    fases  = ["Todas"] + sorted(df_box["phase"].dropna().unique().tolist())
    fase   = c3.selectbox("Fase", fases, key="h1_fase")

    st.divider()

    # Módulo 1 — Perfil de tiro
    st.subheader("Perfil de Tiro por Jugador")
    df_eq = df_box[(df_box["season_code"]==season) & (df_box["team_id"]==team)]
    if fase != "Todas":
        df_eq = df_eq[df_eq["phase"]==fase]

    jugadores = sorted(df_eq["player"].unique())
    jugador   = st.selectbox("Jugador", jugadores, key="h1_jug")
    df_jug    = df_eq[df_eq["player"]==jugador].sort_values("round").copy()
    df_jug["fga"]        = df_jug["two_points_attempted"] + df_jug["three_points_attempted"]
    df_jug["game_label"] = "R" + df_jug["round"].astype(str)

    if df_jug.empty:
        st.info("Sin datos para los filtros seleccionados.")
    else:
        fig_t = go.Figure()
        for col, name, color in [
            ("fga","FGA","#3498db"),
            ("two_points_made","2PM","#2ecc71"),
            ("three_points_made","3PM","#e74c3c"),
            ("free_throws_attempted","FTA","#f39c12"),
        ]:
            fig_t.add_trace(go.Scatter(
                x=df_jug["game_label"], y=df_jug[col],
                mode="lines+markers", name=name,
                line=dict(color=color, width=2), marker=dict(size=6),
            ))
        fig_t.update_layout(
            xaxis_title="Partido (Ronda)", yaxis_title="Cantidad",
            legend=dict(orientation="h", y=1.1),
            margin=dict(t=20),
        )
        dark_layout(fig_t)
        st.plotly_chart(fig_t, use_container_width=True)

    st.divider()

    # Módulo 2 — Consistencia Competitiva
    st.subheader("Consistencia Competitiva")
    df_wr = build_winrate_df(df_hdr)
    df_tw = df_wr[(df_wr["team"]==team) & (df_wr["season_code"]==season)]

    col_wr, col_q3 = st.columns(2)

    with col_wr:
        st.markdown("**Win Rate por Fase**")
        if df_tw.empty:
            st.info("Sin datos de resultados.")
        else:
            wr = df_tw.groupby("phase").agg(p=("won","count"), v=("won","sum")).reset_index()
            wr["win_rate"] = (wr["v"]/wr["p"]*100).round(1)
            fig_wr = px.bar(wr, x="phase", y="win_rate", color="phase", text="win_rate",
                            labels={"phase":"Fase","win_rate":"Win Rate %"})
            fig_wr.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig_wr.update_layout(showlegend=False, yaxis=dict(range=[0,110]), margin=dict(t=20))
            dark_layout(fig_wr)
            st.plotly_chart(fig_wr, use_container_width=True)

    with col_q3:
        st.markdown("**Cierre con ventaja en Q3**")
        dh = df_hdr[df_hdr["season_code"]==season].copy()
        for lado in ["a","b"]:
            dh[f"sq3_{lado}"] = (dh[f"score_quarter_1_{lado}"] +
                                  dh[f"score_quarter_2_{lado}"] +
                                  dh[f"score_quarter_3_{lado}"])
        da = dh[dh["team_id_a"]==team].copy()
        da["lead_q3"] = da["sq3_a"] - da["sq3_b"]
        da["won"]     = (da["score_a"] > da["score_b"]).astype(int)
        db_ = dh[dh["team_id_b"]==team].copy()
        db_["lead_q3"] = db_["sq3_b"] - db_["sq3_a"]
        db_["won"]     = (db_["score_b"] > db_["score_a"]).astype(int)
        dq3 = pd.concat([da[["lead_q3","won"]], db_[["lead_q3","won"]]])

        rows = []
        for u in [10, 15, 20]:
            sub = dq3[dq3["lead_q3"]>=u]
            if len(sub):
                rows.append({"Ventaja Q3":f"+{u} pts","Partidos":len(sub),
                              "Efectividad %":round(sub["won"].mean()*100,1)})
        if not rows:
            st.info("Sin partidos con ventaja ≥10 pts en Q3.")
        else:
            dfq = pd.DataFrame(rows)
            fig_q3 = px.bar(dfq, x="Ventaja Q3", y="Efectividad %",
                            color="Ventaja Q3", text="Efectividad %",
                            hover_data=["Partidos"])
            fig_q3.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig_q3.update_layout(showlegend=False, yaxis=dict(range=[0,110]), margin=dict(t=20))
            dark_layout(fig_q3)
            st.plotly_chart(fig_q3, use_container_width=True)
