import streamlit as st
import hu01
import hu02
import hu03
import hu04
import hu04_v2
from db import validar_usuario

ROL_CONFIG = {
    "entrenador": {
        "icon": "🏋️",
        "label": "Entrenador",
        "caption": "Rendimiento individual · Decisiones tácticas",
        "opciones": ["Entrenador"],
    },
    "scout": {
        "icon": "🔍",
        "label": "Scout",
        "caption": "Evaluación de perfiles · PIR · Creación de juego",
        "opciones": ["Scout"],
    },
    "analista": {
        "icon": "📊",
        "label": "Analista Deportivo",
        "caption": "Patrones tácticos · Eficiencia de equipos",
        "opciones": ["Analista"],
    },
    "directivo": {
        "icon": "🏆",
        "label": "Directivo",
        "caption": "Consistencia competitiva · Planificación institucional",
        "opciones": ["Directivo", "Directivo v2"],
    },
    "admin": {
        "icon": "⚙️",
        "label": "Administrador",
        "caption": "Acceso completo a todos los módulos",
        "opciones": ["Entrenador", "Scout", "Analista", "Directivo", "Directivo v2"],
    },
}

st.set_page_config(
    page_title="BasketStats Analytics",
    page_icon="🏀",
    layout="wide",
)

st.markdown("""
<style>
/* Sidebar más oscuro */
section[data-testid="stSidebar"] {
    background-color: #0a0e1a;
}
/* Cards de métricas */
div[data-testid="metric-container"] {
    background-color: #1a1f2e;
    border: 1px solid #2d3553;
    border-radius: 10px;
    padding: 12px 16px;
}
/* Tabs más marcados */
div[data-testid="stTabs"] button {
    font-size: 14px;
    font-weight: 600;
}
/* Separador de color */
hr {
    border-color: #f39c12 !important;
    opacity: 0.3;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for key, val in [("logged_in", False), ("usuario", None), ("rol", None)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Pantalla de login ─────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    col_login, _ = st.columns([1, 1])
    with col_login:
        st.markdown("## 🏀 BasketStats Analytics")
        st.markdown("##### Plataforma de análisis estadístico para básquet europeo")
        st.divider()
        usuario  = st.text_input("Usuario", placeholder="Tu nombre de usuario")
        password = st.text_input("Contraseña", type="password", placeholder="••••••••")
        if st.button("Ingresar", use_container_width=True):
            user = validar_usuario(usuario, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.usuario   = usuario
                st.session_state.rol       = user["rol"]
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
rol_cfg = ROL_CONFIG.get(st.session_state.rol, ROL_CONFIG["admin"])

with st.sidebar:
    st.markdown(f"## 🏀 BasketStats")
    st.divider()
    st.markdown(f"**{rol_cfg['icon']} {rol_cfg['label']}**")
    st.caption(st.session_state.usuario)
    st.divider()
    if st.button("🚪 Cerrar sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ── Header principal ──────────────────────────────────────────────────────────
col_title, col_badge = st.columns([9, 1])
with col_title:
    st.markdown(f"# {rol_cfg['icon']} {rol_cfg['label']}")
    st.caption(rol_cfg["caption"])

# ── Navegación entre dashboards ───────────────────────────────────────────────
opciones = rol_cfg["opciones"]

if len(opciones) > 1:
    hu_sel = st.segmented_control("Dashboard", options=opciones, default=opciones[0])
else:
    hu_sel = opciones[0]

st.divider()

# ── Routing ───────────────────────────────────────────────────────────────────
if hu_sel == "Entrenador":
    hu01.render()
elif hu_sel == "Scout":
    hu02.render()
elif hu_sel == "Analista":
    hu03.render()
elif hu_sel == "Directivo":
    hu04.render()
elif hu_sel == "Directivo v2":
    hu04_v2.render()
