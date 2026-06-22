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
   
    if df is None or df.empty:
        return

    table = df.copy()

    
    if columns:
        table = table[columns]

    
    if rename_columns:
        table = table.rename(columns=rename_columns)

    
    if style_fn is not None:
        table = style_fn(table)
    else:
        
        styler = table.style
        
        
        float_cols = table.select_dtypes(include=['float64', 'float32']).columns
        if not float_cols.empty:
            styler = styler.format({col: "{:.2f}" for col in float_cols})
            
        
        pct_cols = [c for c in table.columns if "pct" in c.lower() or "porcentaje" in c.lower() or "efectividad" in c.lower()]
        if pct_cols:
            styler = styler.format({col: "{:.1%}" if table[col].max() <= 1.0 else "{:.1f}%" for col in pct_cols})

        
        num_cols = table.select_dtypes(include=['number']).columns
        
        
        if not num_cols.empty:
            
            styler = styler.highlight_max(subset=num_cols, color="rgba(241, 196, 15, 0.15)")

        table = styler

    #  INTERFAZ DESPLEGABLE 
    with st.expander(f"{icon} {title}", expanded=False):
        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True
        )