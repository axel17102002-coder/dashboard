import pandas as pd
import streamlit as st

def render_table_report(
    df: pd.DataFrame,
    title: str = "Datos del gráfico",
    columns: list[str] | None = None,
    rename_columns: dict | None = None,
    style_fn=None,
    icon: str = "📊",
):
    """
    Renderiza una tabla de reporte analítico dentro de un contenedor colapsable (expander).
    Aplica formatos profesionales de manera automática si no se provee una función de estilo.
    """
    if df is None or df.empty:
        return

    table = df.copy()

    # 1. Filtrado de columnas originales
    if columns:
        table = table[columns]

    # 2. Renombrado de columnas original
    if rename_columns:
        table = table.rename(columns=rename_columns)

    # 3. MEJORA VISUAL: Estilizado automático si no se provee una función externa
    if style_fn is not None:
        table = style_fn(table)
    else:
        # Creamos un formateo por defecto de nivel profesional
        styler = table.style
        
        # Identificamos columnas numéricas flotantes para redondearlas a 2 decimales automáticamente
        float_cols = table.select_dtypes(include=['float64', 'float32']).columns
        if not float_cols.empty:
            styler = styler.format({col: "{:.2f}" for col in float_cols})
            
        # Identificamos columnas de porcentaje para darles un acabado limpio (ej. 45.2%)
        pct_cols = [c for c in table.columns if "pct" in c.lower() or "porcentaje" in c.lower() or "efectividad" in c.lower()]
        if pct_cols:
            styler = styler.format({col: "{:.1%}" if table[col].max() <= 1.0 else "{:.1f}%" for col in pct_cols})

        # 🎯 CORRECCIÓN DEL NAMEERROR: Definimos num_cols antes de usarla en la condición
        num_cols = table.select_dtypes(include=['number']).columns
        
        # Evaluamos y aplicamos el resaltado de manera segura
        if not num_cols.empty:
            # Usamos un tono dorado/amarillo translúcido premium muy sutil para destacar el máximo rendimiento
            styler = styler.highlight_max(subset=num_cols, color="rgba(241, 196, 15, 0.15)")

        table = styler

    # 4. INTERFAZ DESPLEGABLE CON ESTILO UNIFICADO (UX LIMPIA)
    with st.expander(f"{icon} {title}", expanded=False):
        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True
        )