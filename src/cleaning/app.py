import streamlit as st
import pandas as pd
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

json_path = BASE_DIR / "reporte_datos.json"

with open("reporte_datos.json", "r", encoding="utf-8") as f:
    data = json.load(f)

st.set_page_config(
    page_title="EuroLeague Data Quality",
    layout="wide"
)

st.title("🏀 EuroLeague & EuroCup Data Quality Report")

# ── Resumen general ─────────────────────────────
total_tablas = len(data)
total_filas = sum(d["filas"] for d in data.values())
total_nulos = sum(d["total_nulos"] for d in data.values())

col1, col2, col3 = st.columns(3)

col1.metric("📄 Tablas", total_tablas)
col2.metric("📊 Filas Totales", f"{total_filas:,}")
col3.metric("⚠️ Nulos Totales", f"{total_nulos:,}")

st.divider()

# ── Tabla resumen ─────────────────────────────
resumen = []

for nombre, d in data.items():
    resumen.append({
        "Tabla": nombre,
        "Liga": d["liga"],
        "Filas": d["filas"],
        "Columnas": d["columnas"],
        "Duplicados": d["duplicados"],
        "Completitud %": d["pct_completo"]
    })

df_resumen = pd.DataFrame(resumen)

st.subheader("📋 Resumen de datasets")
st.dataframe(df_resumen, use_container_width=True)

# ── Detalle por dataset ─────────────────────────
st.subheader("🔍 Detalle de columnas")

dataset = st.selectbox(
    "Seleccionar dataset",
    list(data.keys())
)

detalle = data[dataset]["columnas_detalle"]

df_detalle = pd.DataFrame(detalle).T.reset_index()
df_detalle.rename(columns={"index": "Columna"}, inplace=True)

st.dataframe(df_detalle, use_container_width=True)