import streamlit as st
import hu01
import hu02
import hu03
import hu04
import hu04_v2
from db import validar_usuario

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:

    st.title("Login")

    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        # validar contra PostgreSQL
        user = validar_usuario(usuario, password)

        if user:
            st.session_state.logged_in = True
            st.session_state.usuario = usuario
            st.session_state.rol = user["rol"]
            st.rerun()

    st.stop()

with st.sidebar:
    st.write(f"👤 {st.session_state.usuario}")

    if st.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

ROL_PANTALLAS = {
    "entrenador": ["HU-01 — Entrenador"],
    "scout": ["HU-02 — Scout"],
    "analista": ["HU-03 — Analista"],
    "directivo": [
        "HU-04 — Directivo",
        "HU-04_v2 — Directivo"
    ],
    "admin": [
        "HU-01 — Entrenador",
        "HU-02 — Scout",
        "HU-03 — Analista",
        "HU-04 — Directivo",
        "HU-04_v2 — Directivo"
    ]
}

opciones = ROL_PANTALLAS[st.session_state.rol]

with st.sidebar:
    hu = st.radio("Dashboard", opciones)

if hu == "HU-01 — Entrenador":
    hu01.render()

elif hu == "HU-02 — Scout":
    hu02.render()

elif hu == "HU-03 — Analista":
    hu03.render()

elif hu == "HU-04 — Directivo":
    hu04.render()

elif hu == "HU-04_v2 — Directivo":
    hu04_v2.render()