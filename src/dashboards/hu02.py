import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from db import load_box_scores, load_season_players, load_game_headers, dark_layout


def render():
    st.header("Dashboard — Scout")
    st.caption("Evaluación de perfiles y progresión de jugadores")

    comp = st.selectbox("Competición", ["EuroLeague", "EuroCup", "Ambas"], key="h2_comp")

    try:
        df_box = load_box_scores(comp)
        df_sp = load_season_players(comp)
        df_hdr = load_game_headers(comp)
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        st.stop()

    c1, c2, c3 = st.columns(3)

    season = c1.selectbox(
        "Temporada",
        sorted(df_sp["season_code"].dropna().unique()),
        key="h2_sea"
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
        df_sp[df_sp["season_code"] == season]["team_id"]
        .dropna()
        .unique()
    )

    df_team_names = (
        df_team_names[df_team_names["team_id"].isin(teams_ids_temporada)]
        .sort_values("team_name")
    )

    team_label_to_id = {
        "Todos": "Todos",
        **dict(zip(df_team_names["team_name"], df_team_names["team_id"]))
    }

    team_label = c2.selectbox(
        "Equipo",
        list(team_label_to_id.keys()),
        key="h2_team"
    )

    team = team_label_to_id[team_label]

    perfs = ["Todos"] + sorted(
        df_sp["perfil_ofensivo"].dropna().unique().tolist()
    )

    perfil = c3.selectbox("Perfil ofensivo", perfs, key="h2_perf")

    st.divider()

    # Módulo 1 — Ranking TOP 10 para jugadores
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
    st.caption(
        "Relación Asistencias/Pérdidas por jugador · "
        "Solo se muestran jugadores con al menos una pérdida registrada"
    )

    # ── Filtros adicionales del módulo ───────────────────────────────────────
    c4, c5 = st.columns(2)

    min_gp_asto = c4.slider(
        "Mín. partidos jugados",
        1, 20, 5,
        key="h2_asto_mingp",
        help="Evita jugadores con pocos partidos que distorsionan el ratio"
    )

    # Base filtrada
    df_asto_base = df_sp[
        (df_sp["season_code"] == season) &
        (df_sp["turnovers"] > 0) &
        (df_sp["games_played"] >= min_gp_asto)
    ].copy()

    if team != "Todos":
        df_asto_base = df_asto_base[df_asto_base["team_id"] == team]
    if perfil != "Todos":
        df_asto_base = df_asto_base[df_asto_base["perfil_ofensivo"] == perfil]

    jugadores_disponibles = sorted(
        df_asto_base["player"].dropna().unique().tolist()
    )
    jugadores_sel = c5.multiselect(
        "Destacar jugadores",
        jugadores_disponibles,
        default=[],
        max_selections=6,
        key="h2_player",
        help="Seleccioná hasta 6 para resaltarlos en los gráficos y comparar"
    )

    df_asto = df_asto_base.copy()

    # ── Calcular AST/TO ──────────────────────────────────────────────────────
    df_asto["assists"]   = pd.to_numeric(df_asto["assists"],   errors="coerce").fillna(0)
    df_asto["turnovers"] = pd.to_numeric(df_asto["turnovers"], errors="coerce").fillna(0)
    df_asto = df_asto[df_asto["turnovers"] > 0].copy()
    df_asto["ast_to_ratio"] = (df_asto["assists"] / df_asto["turnovers"]).round(2)

    # Merge nombre de equipo
    df_asto = df_asto.merge(
        df_team_names[["team_id", "team_name"]],
        on="team_id",
        how="left"
    )

    if df_asto.empty:
        st.info(
            "No hay jugadores que cumplan los criterios seleccionados. "
            "Recuerde que solo se incluyen jugadores con al menos una pérdida registrada."
        )
    else:
        # ── Métricas resumen ─────────────────────────────────────────────────
        mejor = df_asto.nlargest(1, "ast_to_ratio").iloc[0]
        peor  = df_asto.nsmallest(1, "ast_to_ratio").iloc[0]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Jugadores evaluados", len(df_asto), help="Con al menos 1 pérdida registrada")
        m2.metric("Mejor AST/TO", f"{mejor['ast_to_ratio']:.2f}", help=mejor["player"])
        m3.metric("Promedio AST/TO", f"{df_asto['ast_to_ratio'].mean():.2f}")
        m4.metric("Menor AST/TO", f"{peor['ast_to_ratio']:.2f}", help=peor["player"])

        st.divider()

        # ════════════════════════════════════════════════════════════════════
        # VISTA 1 — Bar chart ranking AST/TO
        # ════════════════════════════════════════════════════════════════════
        tab1, tab2, tab3 = st.tabs([
            "📊 Ranking AST/TO",
            "🎯 Mapa AST vs Pérdidas",
            "⚖️ Comparativa de Jugadores"
        ])

        with tab1:
            max_jugadores = st.slider(
                "Máx. jugadores a mostrar",
                5, min(30, max(5, len(df_asto))), min(15, len(df_asto)),
                key="h2_asto_max"
            )
            df_sorted = df_asto.sort_values("ast_to_ratio", ascending=True)
            df_top = df_sorted.tail(max_jugadores)

            # Garantizar que los jugadores seleccionados aparezcan siempre
            if jugadores_sel:
                # Buscar los seleccionados en el dataset completo (no solo en df_top)
                df_sel_rows = df_asto[df_asto["player"].isin(jugadores_sel)]
                players_ya_en_top = set(df_top["player"].tolist())
                df_faltantes = df_sel_rows[~df_sel_rows["player"].isin(players_ya_en_top)]
                df_plot = pd.concat([df_faltantes, df_top], ignore_index=True)
                df_plot = df_plot.drop_duplicates(subset="player")
                df_plot = df_plot.sort_values("ast_to_ratio", ascending=True)
            else:
                df_plot = df_top

            umbral_alto  = df_plot["ast_to_ratio"].quantile(0.66)
            umbral_medio = df_plot["ast_to_ratio"].quantile(0.33)

            COLORES_SEL = [
                "#f39c12", "#3498db", "#2ecc71",
                "#e74c3c", "#9b59b6", "#1abc9c"
            ]
            color_map = {j: COLORES_SEL[i] for i, j in enumerate(jugadores_sel)}

            def _color_bar(player, ratio):
                if jugadores_sel:
                    if player in color_map:
                        return color_map[player]
                    return "rgba(255,255,255,0.15)"
                if ratio >= umbral_alto:  return "#2ecc71"
                if ratio >= umbral_medio: return "#f39c12"
                return "#e74c3c"

            colores = [
                _color_bar(p, v)
                for p, v in zip(df_plot["player"], df_plot["ast_to_ratio"])
            ]
            opacidades = [
                1.0 if (not jugadores_sel or p in color_map) else 0.4
                for p in df_plot["player"]
            ]

            fig_bar = go.Figure(
                go.Bar(
                    y=df_plot["player"],
                    x=df_plot["ast_to_ratio"],
                    orientation="h",
                    marker=dict(
                        color=colores,
                        opacity=opacidades,
                        line=dict(
                            color=[
                                color_map.get(p, "rgba(0,0,0,0)")
                                for p in df_plot["player"]
                            ],
                            width=[3 if p in color_map else 0 for p in df_plot["player"]]
                        )
                    ),
                    text=df_plot["ast_to_ratio"].apply(lambda v: f"{v:.2f}"),
                    textposition="outside",
                    customdata=df_plot[["assists", "turnovers", "team_name"]].values,
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Equipo: %{customdata[2]}<br>"
                        "Asistencias: %{customdata[0]:.0f}<br>"
                        "Pérdidas: %{customdata[1]:.0f}<br>"
                        "AST/TO: %{x:.2f}"
                        "<extra></extra>"
                    ),
                )
            )
            fig_bar.add_vline(
                x=1.0,
                line_dash="dash",
                line_color="rgba(255,255,255,0.35)",
                annotation_text="AST/TO = 1",
                annotation_font_color="rgba(255,255,255,0.55)",
                annotation_position="top right"
            )
            fig_bar.update_layout(
                xaxis_title="AST/TO Ratio",
                margin=dict(t=20, l=200, r=60),
                height=max(380, len(df_plot) * 32),
                xaxis=dict(range=[0, df_plot["ast_to_ratio"].max() * 1.18]),
            )
            dark_layout(fig_bar)
            st.plotly_chart(fig_bar, use_container_width=True)
            st.caption(
                "🟢 Alta eficiencia (tercil superior)  "
                "🟡 Eficiencia media  "
                "🔴 Baja eficiencia (tercil inferior)"
            )

        # ════════════════════════════════════════════════════════════════════
        # VISTA 2 — Scatter AST vs TO (cuadrantes)
        # ════════════════════════════════════════════════════════════════════
        with tab2:
            st.caption(
                "Cada punto es un jugador. "
                "Arriba a la izquierda = muchas asistencias y pocas pérdidas (perfil ideal)."
            )

            df_scatter = df_asto.copy()

            avg_ast = df_scatter["assists"].mean()
            avg_to  = df_scatter["turnovers"].mean()

            # Tamaño del punto proporcional al AST/TO ratio
            size_vals = (df_scatter["ast_to_ratio"] * 6).clip(lower=8)

            fig_scatter = go.Figure()

            # Sombreado del cuadrante ideal (arriba-izq)
            fig_scatter.add_shape(
                type="rect",
                x0=0, x1=avg_to,
                y0=avg_ast, y1=df_scatter["assists"].max() * 1.1,
                fillcolor="rgba(46,204,113,0.07)",
                line_width=0,
            )

            # Traza base — todos los jugadores (tenues si hay selección)
            base_opacity = 0.25 if jugadores_sel else 0.85
            fig_scatter.add_trace(
                go.Scatter(
                    x=df_scatter["turnovers"],
                    y=df_scatter["assists"],
                    mode="markers+text",
                    name="Jugadores",
                    text=df_scatter["player"].apply(
                        lambda n: n.split()[-1] if isinstance(n, str) else n
                    ),
                    textposition="top center",
                    textfont=dict(size=9, color=f"rgba(255,255,255,{base_opacity})"),
                    marker=dict(
                        size=size_vals,
                        color=df_scatter["ast_to_ratio"],
                        colorscale=[
                            [0.0,  "#e74c3c"],
                            [0.5,  "#f39c12"],
                            [1.0,  "#2ecc71"],
                        ],
                        colorbar=dict(
                            title="AST/TO",
                            tickfont=dict(color="white"),
                            titlefont=dict(color="white"),
                        ),
                        showscale=True,
                        opacity=base_opacity,
                        line=dict(width=0.5, color="rgba(255,255,255,0.2)"),
                    ),
                    customdata=df_scatter[["player", "team_name", "ast_to_ratio"]].values,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Equipo: %{customdata[1]}<br>"
                        "Asistencias: %{y:.0f}<br>"
                        "Pérdidas: %{x:.0f}<br>"
                        "AST/TO: %{customdata[2]:.2f}"
                        "<extra></extra>"
                    ),
                    showlegend=False,
                )
            )

            # Traza resaltada — solo jugadores seleccionados
            if jugadores_sel:
                for i, jug in enumerate(jugadores_sel):
                    df_jug = df_scatter[df_scatter["player"] == jug]
                    if df_jug.empty:
                        continue
                    color_jug = COLORES_SEL[i % len(COLORES_SEL)]
                    sz_jug = (df_jug["ast_to_ratio"] * 6).clip(lower=12)
                    fig_scatter.add_trace(
                        go.Scatter(
                            x=df_jug["turnovers"],
                            y=df_jug["assists"],
                            mode="markers+text",
                            name=jug,
                            text=df_jug["player"].apply(
                                lambda n: n.split()[-1] if isinstance(n, str) else n
                            ),
                            textposition="top center",
                            textfont=dict(size=11, color=color_jug),
                            marker=dict(
                                size=sz_jug + 4,
                                color=color_jug,
                                line=dict(width=2, color="white"),
                                symbol="circle",
                            ),
                            customdata=df_jug[["player", "team_name", "ast_to_ratio"]].values,
                            hovertemplate=(
                                "<b>%{customdata[0]}</b><br>"
                                "Equipo: %{customdata[1]}<br>"
                                "Asistencias: %{y:.0f}<br>"
                                "Pérdidas: %{x:.0f}<br>"
                                "AST/TO: %{customdata[2]:.2f}"
                                "<extra></extra>"
                            ),
                        )
                    )

            # Líneas de promedio
            fig_scatter.add_hline(
                y=avg_ast,
                line_dash="dot",
                line_color="rgba(255,255,255,0.25)",
                annotation_text=f"Prom. AST {avg_ast:.1f}",
                annotation_font_color="rgba(255,255,255,0.45)",
                annotation_position="right"
            )
            fig_scatter.add_vline(
                x=avg_to,
                line_dash="dot",
                line_color="rgba(255,255,255,0.25)",
                annotation_text=f"Prom. TO {avg_to:.1f}",
                annotation_font_color="rgba(255,255,255,0.45)",
                annotation_position="top"
            )

            fig_scatter.update_layout(
                xaxis_title="Pérdidas (TO)",
                yaxis_title="Asistencias (AST)",
                margin=dict(t=30, r=80),
                height=500,
            )
            dark_layout(fig_scatter)
            st.plotly_chart(fig_scatter, use_container_width=True)

        # ════════════════════════════════════════════════════════════════════
        # VISTA 3 — Comparativa entre jugadores seleccionados
        # ════════════════════════════════════════════════════════════════════
        with tab3:
            jugadores_lista = sorted(df_asto["player"].dropna().unique().tolist())
            default_comp = jugadores_sel if jugadores_sel else jugadores_lista[:min(4, len(jugadores_lista))]

            seleccionados = st.multiselect(
                "Seleccioná hasta 6 jugadores para comparar",
                jugadores_lista,
                default=default_comp,
                max_selections=6,
                key="h2_comp_players"
            )

            if not seleccionados:
                st.info("Seleccioná al menos un jugador para ver la comparativa.")
            else:
                df_comp = df_asto[df_asto["player"].isin(seleccionados)].copy()

                metricas = {
                    "AST/TO":       "ast_to_ratio",
                    "Asistencias":  "assists",
                    "Pérdidas":     "turnovers",
                }

                # Gráfico de barras agrupadas
                fig_comp = go.Figure()

                colores_jugadores = [
                    "#f39c12", "#3498db", "#2ecc71",
                    "#e74c3c", "#9b59b6", "#1abc9c"
                ]

                for i, jugador_sel in enumerate(seleccionados):
                    fila = df_comp[df_comp["player"] == jugador_sel]
                    if fila.empty:
                        continue
                    fila = fila.iloc[0]
                    color = colores_jugadores[i % len(colores_jugadores)]

                    fig_comp.add_trace(
                        go.Bar(
                            name=jugador_sel.split()[-1] if isinstance(jugador_sel, str) else jugador_sel,
                            x=list(metricas.keys()),
                            y=[fila[v] for v in metricas.values()],
                            marker_color=color,
                            text=[f"{fila[v]:.2f}" for v in metricas.values()],
                            textposition="outside",
                            hovertemplate=(
                                f"<b>{jugador_sel}</b><br>"
                                "%{x}: %{y:.2f}"
                                "<extra></extra>"
                            ),
                        )
                    )

                fig_comp.update_layout(
                    barmode="group",
                    xaxis_title="Métrica",
                    yaxis_title="Valor",
                    margin=dict(t=20, r=20),
                    height=430,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.28,
                        xanchor="center",
                        x=0.5,
                        font=dict(color="white", size=11)
                    ),
                )
                dark_layout(fig_comp)
                st.plotly_chart(fig_comp, use_container_width=True)

                # Tabla comparativa
                df_tabla_comp = (
                    df_comp[["player", "team_name", "assists", "turnovers", "ast_to_ratio"]]
                    .rename(columns={
                        "player":       "Jugador",
                        "team_name":    "Equipo",
                        "assists":      "Asistencias",
                        "turnovers":    "Pérdidas",
                        "ast_to_ratio": "AST/TO"
                    })
                    .sort_values("AST/TO", ascending=False)
                    .reset_index(drop=True)
                )
                st.dataframe(
                    df_tabla_comp.style.format({
                        "Asistencias": "{:.0f}",
                        "Pérdidas":    "{:.0f}",
                        "AST/TO":      "{:.2f}"
                    }).highlight_max(subset=["AST/TO", "Asistencias"], color="#1a4a2e")
                     .highlight_min(subset=["Pérdidas"], color="#1a4a2e"),
                    use_container_width=True,
                    hide_index=True
                )