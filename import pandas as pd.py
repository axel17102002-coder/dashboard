import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import db

# ── Carga de datos (fuera de render, para que @cache_data funcione) ──────────

@st.cache_data
def load_box_scores(comp: str) -> pd.DataFrame:
    if comp == "EuroLeague":
        return pd.read_csv("data/euroleague_box_score.csv")
    elif comp == "EuroCup":
        return pd.read_csv("data/eurocup_box_score.csv")
    else:
        el = pd.read_csv("data/euroleague_box_score.csv")
        ec = pd.read_csv("data/eurocup_box_score.csv")
        return pd.concat([el, ec], ignore_index=True)


@st.cache_data
def load_all_headers(comp: str) -> pd.DataFrame:
    if comp == "EuroLeague":
        df = pd.read_csv("data/euroleague_header.csv")
        df["competition"] = "EuroLeague"
        return df
    elif comp == "EuroCup":
        df = pd.read_csv("data/eurocup_header.csv")
        df["competition"] = "EuroCup"
        return df
    else:
        el = pd.read_csv("data/euroleague_header.csv")
        ec = pd.read_csv("data/eurocup_header.csv")
        el["competition"] = "EuroLeague"
        ec["competition"] = "EuroCup"