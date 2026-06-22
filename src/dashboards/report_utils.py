import pandas as pd
import streamlit as st


def render_table_report(
    df: pd.DataFrame,
    title: str = "Datos del gráfico",
    columns: list[str] | None = None,
    rename_columns: dict | None = None,
):
    if df is None or df.empty:
        return

    table = df.copy()

    if columns:
        table = table[columns]

    if rename_columns:
        table = table.rename(columns=rename_columns)

    st.markdown(f"#### {title}")
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True
    )


def render_styled_table_report(
    df: pd.DataFrame,
    title: str = "Datos del gráfico",
    columns: list[str] | None = None,
    rename_columns: dict | None = None,
    style_fn=None,
):
    if df is None or df.empty:
        return

    table = df.copy()

    if columns:
        table = table[columns]

    if rename_columns:
        table = table.rename(columns=rename_columns)

    st.markdown(f"#### {title}")

    if style_fn is not None:
        table = style_fn(table)

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True
    )
