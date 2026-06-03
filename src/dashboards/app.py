import streamlit as st
import hu01
import hu02
import hu03
import hu04

st.set_page_config(
    page_title="BasketStats Analytics",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.title("🏀 BasketStats Analytics")
    st.divider()
    hu = st.radio("Dashboard", [
        "HU-01 — Entrenador",
        "HU-02 — Scout",
        "HU-03 — Analista",
        "HU-04 — Directivo",
    ])

if hu == "HU-01 — Entrenador":
    hu01.render()
elif hu == "HU-02 — Scout":
    hu02.render()
elif hu == "HU-03 — Analista":
    hu03.render()
elif hu == "HU-04 — Directivo":
    hu04.render()
