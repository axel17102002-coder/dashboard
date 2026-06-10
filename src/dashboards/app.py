import streamlit as st
import hu01
import hu02
import hu03
import hu04
import hu04_v2
from db import validar_usuario

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

st.set_page_config(
    page_title="BasketStats Analytics",
    page_icon="🏀",
    layout="wide"
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "usuario" not in st.session_state:
    st.session_state.usuario = None

if "rol" not in st.session_state:
    st.session_state.rol = None

st.set_page_config(
    layout="wide"
)
st.title("🏀 BasketStats Analytics")

st.markdown("""
<style>
div[data-testid="stButton"] button {
    background-color: #ff7a00;
    color: white;
}
</style>
""", unsafe_allow_html=True)

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


col1, col2 = st.columns([8, 2])

with col1:
    st.caption("Plataforma de análisis y scouting")

with col2:
    st.write(f"👤 {st.session_state.usuario}")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False



with st.sidebar:
    st.write(f"👤 {st.session_state.usuario.capitalize()}")
    st.write(f"{st.session_state.rol.capitalize()}")

    if st.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

opciones = ROL_PANTALLAS[st.session_state.rol]

hu = st.segmented_control(
    "Dashboard",
    options=opciones,
    default=opciones[0]
)

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