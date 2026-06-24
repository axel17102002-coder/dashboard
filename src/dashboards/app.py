from pathlib import Path
import streamlit as st
import hu01
import hu02
import hu03
import hu04
import admin_panel
from db import validar_usuario, ensure_usuarios_table

_LOGO_PATH = Path(__file__).parent / "assets" / "logo.svg"


@st.cache_data
def _logo_svg() -> str:
    """Devuelve el SVG del logo como texto (para embeberlo inline)."""
    try:
        return _LOGO_PATH.read_text(encoding="utf-8")
    except Exception:
        return ""

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
        "opciones": ["Directivo"],
    },
    "admin": {
        "icon": "⚙️",
        "label": "Administrador",
        "caption": "Carga de datos y acceso completo a todos los módulos",
        "opciones": ["Administración", "Entrenador", "Scout", "Analista", "Directivo"],
    },
}

st.set_page_config(
    page_title="BasketStats Analytics",
    page_icon="🏀",
    layout="wide",
)

st.markdown("""
<style>
/* Sidebar claro */
section[data-testid="stSidebar"] {
    background-color: #f4f6fa;
    border-right: 1px solid #e3e7ef;
}
/* Cards de métricas — bloques de colores */
div[data-testid="stMetric"], div[data-testid="metric-container"] {
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid #e3e7ef;
    background-color: #f4f6fa;
}
div[data-testid="stMetricValue"] {
    font-size: 26px;
    font-weight: 600;
}
div[data-testid="stMetricLabel"] p {
    font-weight: 600;
    color: #5f5e5a;
}
/* Acento de color por posición de columna (cicla cada 4) */
div[data-testid="stHorizontalBlock"] > div:nth-of-type(4n+1) div[data-testid="stMetric"] {
    background-color: #eaf2fb; border-color: #cfe3f7;
}
div[data-testid="stHorizontalBlock"] > div:nth-of-type(4n+1) div[data-testid="stMetricValue"] { color: #185FA5; }
div[data-testid="stHorizontalBlock"] > div:nth-of-type(4n+2) div[data-testid="stMetric"] {
    background-color: #eaf6ee; border-color: #cfe9d8;
}
div[data-testid="stHorizontalBlock"] > div:nth-of-type(4n+2) div[data-testid="stMetricValue"] { color: #2e7d32; }
div[data-testid="stHorizontalBlock"] > div:nth-of-type(4n+3) div[data-testid="stMetric"] {
    background-color: #fdecea; border-color: #f7cfca;
}
div[data-testid="stHorizontalBlock"] > div:nth-of-type(4n+3) div[data-testid="stMetricValue"] { color: #A32D2D; }
div[data-testid="stHorizontalBlock"] > div:nth-of-type(4n+4) div[data-testid="stMetric"] {
    background-color: #fef5e7; border-color: #f7e3c2;
}
div[data-testid="stHorizontalBlock"] > div:nth-of-type(4n+4) div[data-testid="stMetricValue"] { color: #B26A00; }
/* Tabs más marcados */
div[data-testid="stTabs"] button {
    font-size: 14px;
    font-weight: 600;
}
/* Separador de color */
hr {
    border-color: #E8500A !important;
    opacity: 0.25;
}
</style>
""", unsafe_allow_html=True)

# ── Asegurar tabla de usuarios al iniciar la app ────────────────────────────────
try:
    ensure_usuarios_table()
except Exception as e:
    st.error(f"No se pudo inicializar la tabla de usuarios: {e}")
    st.stop()

# ── Session state ─────────────────────────────────────────────────────────────
for key, val in [("logged_in", False), ("usuario", None), ("rol", None)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Pantalla de login ─────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display: none; }
    .login-logo { text-align: center; margin: 8px 0 4px 0; }
    .login-logo svg { max-width: 340px; height: auto; }
    .login-sub {
        text-align: center; color: #73726c; font-size: 14px;
        margin-top: 0; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col_login, _ = st.columns([1, 1.3, 1])
    with col_login:
        st.markdown(f'<div class="login-logo">{_logo_svg()}</div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="login-sub">Plataforma de análisis estadístico · EuroLeague & EuroCup</p>',
            unsafe_allow_html=True,
        )

        with st.form("login_form"):
            usuario  = st.text_input("Usuario", placeholder="Tu nombre de usuario")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••")
            ingresar = st.form_submit_button("Ingresar  →", use_container_width=True, type="primary")

        if ingresar:
            user = validar_usuario(usuario, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.usuario   = usuario
                st.session_state.rol       = user["rol"]
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

        with st.expander("👤 Usuarios de prueba"):
            st.markdown("""
            | Usuario | Contraseña | Rol |
            |---|---|---|
            | `admin` | `admin` | Administrador |
            | `Yessica` | `entrenador` | Entrenador |
            | `Emiliano` | `scout` | Scout |
            | `Cinthia` | `analista` | Analista |
            | `Axel` | `directivo` | Directivo |
            """)

    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
rol_cfg = ROL_CONFIG.get(st.session_state.rol, ROL_CONFIG["admin"])

with st.sidebar:
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:10px; margin:4px 0 8px 0;">
          <svg width="38" height="38" viewBox="55 55 210 210" xmlns="http://www.w3.org/2000/svg">
            <defs><clipPath id="bclip"><circle cx="160" cy="160" r="100"/></clipPath></defs>
            <circle cx="160" cy="160" r="100" fill="#E8500A"/>
            <path d="M62 130 Q160 155 258 130" fill="none" stroke="#C23E00" stroke-width="3.5" stroke-linecap="round"/>
            <path d="M62 190 Q160 165 258 190" fill="none" stroke="#C23E00" stroke-width="3.5" stroke-linecap="round"/>
            <line x1="160" y1="60" x2="160" y2="260" stroke="#C23E00" stroke-width="3.5" stroke-linecap="round"/>
            <g clip-path="url(#bclip)" opacity="0.92">
              <rect x="88"  y="175" width="18" height="45" rx="3" fill="#1A1A2E"/>
              <rect x="112" y="148" width="18" height="72" rx="3" fill="#1A1A2E"/>
              <rect x="136" y="128" width="18" height="92" rx="3" fill="#FFFFFF"/>
              <rect x="160" y="140" width="18" height="80" rx="3" fill="#1A1A2E"/>
              <rect x="184" y="158" width="18" height="62" rx="3" fill="#1A1A2E"/>
            </g>
            <circle cx="160" cy="160" r="100" fill="none" stroke="#C23E00" stroke-width="2.5"/>
          </svg>
          <span style="font-size:20px; font-weight:800; color:#14140f; letter-spacing:-0.5px;">
            Basket<span style="color:#E8500A;">Stats</span>
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
if hu_sel == "Administración":
    admin_panel.render()
elif hu_sel == "Entrenador":
    hu01.render()
elif hu_sel == "Scout":
    hu02.render()
elif hu_sel == "Analista":
    hu03.render()
elif hu_sel == "Directivo":
    hu04.render()
