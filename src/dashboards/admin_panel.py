"""
Panel de administración — carga y actualización de datos.

Permite al perfil admin:
  1. Ejecutar el pipeline completo de limpieza/ingesta sobre los CSV de data/
  2. Reemplazar el CSV crudo de un dataset subiéndolo desde el navegador
"""
import sys
import subprocess
from pathlib import Path

import pandas as pd
import streamlit as st

from db import get_engine

# Raíz del proyecto: .../src/dashboards/admin_panel.py  →  parents[2]
DIR_PROYECTO = Path(__file__).resolve().parents[2]
DIR_DATA     = DIR_PROYECTO / "data"
SCRIPT_MASTER = DIR_PROYECTO / "src" / "cleaning" / "clean_master.py"

LIGAS    = ["euroleague", "eurocup"]
DATASETS = ["header", "box_score", "players", "teams", "points", "comparison", "play_by_play"]

# Datasets pesados que el dashboard NO usa (se pueden omitir para una carga rápida)
DATASETS_LIVIANOS = ["header", "box_score", "players", "teams", "points"]

# Tablas que consultan los dashboards, para mostrar un resumen del estado actual
TABLAS_RESUMEN = {
    "game_headers":    "Partidos",
    "season_players":  "Jugadores-temporada",
    "game_box_scores": "Box scores",
    "season_teams":    "Equipos-temporada",
    "game_points":     "Tiros (points)",
}


def _correr_pipeline(solo_datasets=None, modo="full"):
    """Ejecuta clean_master.py como subproceso y devuelve (ok, salida)."""
    cmd = [sys.executable, str(SCRIPT_MASTER), "--modo", modo]
    if solo_datasets:
        cmd += ["--datasets", ",".join(solo_datasets)]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(DIR_PROYECTO),
            capture_output=True,
            text=True,
            timeout=60 * 30,  # 30 min máximo
        )
        salida = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, salida
    except subprocess.TimeoutExpired:
        return False, "⏱️ El pipeline superó el tiempo máximo (30 min)."
    except Exception as e:
        return False, f"Error al ejecutar el pipeline: {e}"


def _resumen_tablas():
    """Devuelve un dict tabla→cantidad de filas (0 si la tabla no existe)."""
    engine = get_engine()
    resumen = {}
    for tabla in TABLAS_RESUMEN:
        try:
            df = pd.read_sql(f"SELECT COUNT(*) AS n FROM {tabla}", engine)
            resumen[tabla] = int(df.iloc[0]["n"])
        except Exception:
            resumen[tabla] = 0
    return resumen


def render():
    st.subheader("⚙️ Administración de Datos")
    st.caption("Carga e ingesta de estadísticas a la base de datos")

    # ── Estado actual de la base ──────────────────────────────────────────────
    st.markdown("##### Estado actual de la base de datos")
    resumen = _resumen_tablas()
    cols = st.columns(len(TABLAS_RESUMEN))
    for col, (tabla, label) in zip(cols, TABLAS_RESUMEN.items()):
        col.metric(label, f"{resumen[tabla]:,}".replace(",", "."))

    st.divider()

    tab_pipeline, tab_upload = st.tabs([
        "🔄 Cargar / Actualizar datos",
        "📤 Reemplazar un dataset",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Pipeline sobre los CSV de data/
    # ══════════════════════════════════════════════════════════════════════════
    with tab_pipeline:
        st.markdown(
            "Procesa los CSV ubicados en la carpeta `data/` y los carga en la base."
        )

        modo_label = st.radio(
            "Modo de carga",
            ["Actualizar / Agregar (upsert)", "Recarga completa (borra y recarga)"],
            horizontal=False,
            key="adm_modo",
            help=(
                "Upsert: agrega filas nuevas y actualiza las existentes sin borrar nada. "
                "Recomendado para el día a día.\n\n"
                "Recarga completa: borra todas las tablas de estadísticas y las vuelve "
                "a cargar de cero."
            ),
        )
        modo = "upsert" if modo_label.startswith("Actualizar") else "full"

        carga_rapida = st.checkbox(
            "Carga rápida (omitir play_by_play y comparison)",
            value=True,
            help="Esos datasets pesan cientos de MB y el dashboard no los usa. "
                 "Recomendado para la demo.",
        )

        if modo == "full":
            st.warning(
                "La **recarga completa reemplaza** todos los datos de estadísticas. "
                "La tabla de usuarios no se ve afectada.",
                icon="⚠️",
            )
        else:
            st.info(
                "El modo **upsert** no borra nada: inserta lo nuevo y actualiza lo existente.",
                icon="🔁",
            )

        if st.button("🚀 Ejecutar pipeline", type="primary"):
            datasets = DATASETS_LIVIANOS if carga_rapida else None
            with st.spinner("Procesando datos… esto puede tardar varios minutos."):
                ok, salida = _correr_pipeline(solo_datasets=datasets, modo=modo)

            if ok:
                st.success("✅ Datos cargados correctamente.")
                st.cache_data.clear()  # invalida los DataFrames cacheados de db.py
            else:
                st.error("❌ El pipeline terminó con errores. Revisá el detalle abajo.")

            with st.expander("Ver salida del pipeline", expanded=not ok):
                st.code(salida or "(sin salida)", language="text")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Reemplazar el CSV crudo de un dataset
    # ══════════════════════════════════════════════════════════════════════════
    with tab_upload:
        st.markdown(
            "Subí un CSV para **reemplazar** el archivo crudo de un dataset. "
            "El archivo se guarda en `data/` y los cambios se aplican al correr "
            "el pipeline (botón de abajo o la pestaña anterior)."
        )

        c1, c2 = st.columns(2)
        liga = c1.selectbox("Liga", LIGAS, format_func=str.capitalize, key="adm_liga")
        dataset = c2.selectbox("Dataset", DATASETS, key="adm_dataset")

        nombre_destino = f"{liga}_{dataset}.csv"
        st.caption(f"Se guardará como: `data/{nombre_destino}`")

        archivo = st.file_uploader("Archivo CSV", type=["csv"], key="adm_file")

        if archivo is not None:
            DIR_DATA.mkdir(parents=True, exist_ok=True)
            destino = DIR_DATA / nombre_destino

            if st.button("💾 Guardar archivo en data/", type="primary"):
                try:
                    with open(destino, "wb") as f:
                        f.write(archivo.getbuffer())
                    st.success(
                        f"✅ Guardado en `data/{nombre_destino}` "
                        f"({archivo.size / 1_000_000:.1f} MB)."
                    )
                    st.info(
                        "Para que los cambios impacten en los dashboards, "
                        "corré el pipeline de carga.",
                        icon="ℹ️",
                    )
                except Exception as e:
                    st.error(f"Error al guardar el archivo: {e}")

        st.divider()
        if st.button("🔄 Correr pipeline ahora (upsert)"):
            with st.spinner("Procesando datos…"):
                ok, salida = _correr_pipeline(solo_datasets=DATASETS_LIVIANOS, modo="upsert")
            if ok:
                st.success("✅ Datos cargados correctamente.")
                st.cache_data.clear()
            else:
                st.error("❌ El pipeline terminó con errores.")
            with st.expander("Ver salida del pipeline", expanded=not ok):
                st.code(salida or "(sin salida)", language="text")
