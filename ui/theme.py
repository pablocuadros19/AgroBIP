"""Tokens de diseño y CSS centralizado — Sistema BP para AgroBip."""

import streamlit as st

COLORS = {
    "primary": "#00A651",
    "primary_dark": "#00a34d",
    "secondary": "#00B8D4",
    "bg_primary": "#ffffff",
    "bg_secondary": "#f7f9fc",
    "bg_accent": "#f0f9f4",
    "text_primary": "#1a1a2e",
    "text_secondary": "#555555",
    "text_muted": "#666666",
    "text_very_muted": "#999999",
    "border_default": "#e0e5ec",
    "border_light": "#d0d5dd",
    "border_green": "#c8e6d5",
    "tag_bg": "#e8f5ee",
    "tag_text": "#00A651",
    "hover_bg": "#f0f9f4",
}

# Bandas de score
SCORE_BANDS = {
    "alta": {"min": 80, "max": 100, "color": "#dc3545", "bg": "#fce4ec", "label": "ALTA PRIORIDAD"},
    "media": {"min": 60, "max": 79, "color": "#e65100", "bg": "#fff3e0", "label": "PRIORIDAD MEDIA"},
    "observar": {"min": 40, "max": 59, "color": "#f9a825", "bg": "#fff8e1", "label": "OBSERVAR"},
    "baja": {"min": 0, "max": 39, "color": "#999999", "bg": "#f5f5f5", "label": "SIN PRIORIDAD"},
}

# Tipos de alerta con sus colores
ALERT_TYPES = {
    "estres_hidrico": {"icon": "💧", "color": "#e65100", "bg": "#fff3e0", "label": "Estrés hídrico"},
    "emergencia": {"icon": "🚨", "color": "#c62828", "bg": "#fce4ec", "label": "Emergencia agropecuaria"},
    "cambio_productivo": {"icon": "🔄", "color": "#1565c0", "bg": "#e3f2fd", "label": "Cambio productivo"},
    "oportunidad_inversion": {"icon": "📈", "color": "#00A651", "bg": "#e8f5ee", "label": "Oportunidad inversión"},
    "zona_subasegurada": {"icon": "🛡️", "color": "#6a1b9a", "bg": "#f3e5f5", "label": "Zona subasegurada"},
}

# Colores para mapa coroplético
MAP_COLORS = {
    "alta": "#dc3545",
    "media": "#ff8c00",
    "observar": "#ffc107",
    "baja": "#c8c8c8",
    "sin_datos": "#f0f0f0",
}


def get_score_band(score):
    """Devuelve la banda correspondiente a un score."""
    if score >= 80:
        return SCORE_BANDS["alta"]
    elif score >= 60:
        return SCORE_BANDS["media"]
    elif score >= 40:
        return SCORE_BANDS["observar"]
    else:
        return SCORE_BANDS["baja"]


def inject_css():
    """Inyecta CSS global con estilo BP para AgroBip."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif !important;
    }

    /* Header con gradiente */
    .header-gradient {
        background: linear-gradient(90deg, #ffffff 0%, #00A651 25%, #00B8D4 100%);
        border-radius: 12px;
        padding: 2rem 2rem;
        margin-bottom: 1.5rem;
        color: white;
        text-shadow: 0 1px 3px rgba(0,0,0,.15);
        text-align: center;
    }
    .header-gradient h1 {
        font-weight: 900;
        font-size: 2.8rem;
        margin: 0;
        color: white !important;
    }
    .header-gradient p {
        font-weight: 400;
        font-size: 0.9rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }

    /* Cards */
    .bp-card {
        background: #f7f9fc;
        border: 1px solid #e0e5ec;
        border-radius: 14px;
        padding: 1.2rem;
        transition: all 0.2s ease;
        margin-bottom: 0.8rem;
    }
    .bp-card:hover {
        border-color: #00A651;
        box-shadow: 0 4px 20px rgba(0,132,61,.1);
    }

    /* Metric card */
    .metric-card {
        background: #f7f9fc;
        border: 1px solid #e0e5ec;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #00A651;
        line-height: 1.2;
    }
    .metric-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #666666;
        margin-top: 0.3rem;
    }

    /* Sección destacada */
    .section-highlight {
        background: #f0f9f4;
        border: 1px solid #c8e6d5;
        border-left: 4px solid #00A651;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin: 0.8rem 0;
    }

    /* Badge / Tag */
    .bp-badge {
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.2rem 0.7rem;
        border-radius: 20px;
        display: inline-block;
        margin: 0.1rem 0.2rem;
    }

    /* Score badge */
    .score-badge {
        font-size: 0.85rem;
        font-weight: 700;
        padding: 0.3rem 0.9rem;
        border-radius: 20px;
        display: inline-block;
    }

    /* Divider decorativo */
    .bp-divider {
        width: 60px;
        height: 3px;
        background: linear-gradient(90deg, #00A651, #00B8D4);
        border-radius: 2px;
        margin: 0.8rem 0;
    }

    /* Section label */
    .section-label {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #999999;
        margin-bottom: 0.5rem;
    }

    /* Alert card */
    .alert-card {
        background: #ffffff;
        border: 1px solid #e0e5ec;
        border-left: 4px solid #e65100;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        transition: all 0.2s ease;
    }
    .alert-card:hover {
        box-shadow: 0 2px 12px rgba(0,0,0,.06);
    }
    .alert-card .alert-title {
        font-weight: 700;
        font-size: 0.9rem;
        color: #1a1a2e;
    }
    .alert-card .alert-zone {
        font-size: 0.8rem;
        color: #555;
    }
    .alert-card .alert-action {
        font-size: 0.8rem;
        color: #00A651;
        font-weight: 600;
        margin-top: 0.3rem;
    }

    /* Zone card (mini-card para listados) */
    .zone-card {
        background: #ffffff;
        border: 1px solid #e0e5ec;
        border-radius: 12px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: all 0.2s ease;
    }
    .zone-card:hover {
        border-color: #00A651;
        background: #f0f9f4;
        cursor: pointer;
    }
    .zone-card .zone-name {
        font-weight: 700;
        font-size: 0.9rem;
        color: #1a1a2e;
    }
    .zone-card .zone-detail {
        font-size: 0.78rem;
        color: #666;
    }

    /* Ficha de zona — preguntas */
    .ficha-pregunta {
        background: #f7f9fc;
        border: 1px solid #e0e5ec;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }
    .ficha-pregunta h4 {
        color: #00A651;
        font-size: 0.85rem;
        font-weight: 700;
        margin: 0 0 0.4rem 0;
    }
    .ficha-pregunta p {
        color: #1a1a2e;
        font-size: 0.85rem;
        line-height: 1.6;
        margin: 0;
    }

    /* Producto sugerido */
    .producto-sugerido {
        background: linear-gradient(135deg, #f0f9f4, #e8f5ee);
        border: 2px solid #c8e6d5;
        border-radius: 14px;
        padding: 1.2rem;
        margin: 1rem 0;
    }
    .producto-sugerido h4 {
        color: #00A651;
        font-weight: 700;
        font-size: 0.9rem;
        margin: 0 0 0.5rem 0;
    }
    .producto-sugerido .producto-nombre {
        font-weight: 700;
        font-size: 1rem;
        color: #1a1a2e;
    }
    .producto-sugerido .producto-detalle {
        font-size: 0.8rem;
        color: #555;
        margin-top: 0.3rem;
    }

    /* Score breakdown bar */
    .score-bar-container {
        margin: 0.3rem 0;
    }
    .score-bar-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #555;
        margin-bottom: 0.2rem;
    }
    .score-bar-track {
        background: #e0e5ec;
        border-radius: 4px;
        height: 8px;
        overflow: hidden;
    }
    .score-bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
    }

    /* Progress bar custom */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #00A651, #00B8D4) !important;
    }

    /* Botones Streamlit override */
    .stButton > button {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        box-shadow: 0 4px 15px rgba(0,132,61,.25);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #00A651, #00a34d);
        color: white;
        border: none;
    }

    /* Sidebar */
    .sidebar-logo {
        text-align: center;
        padding: 0.5rem 0 1rem 0;
    }
    .sidebar-logo img {
        max-width: 234px;
    }
    .sidebar-brand {
        text-align: center;
        padding: 1rem 0;
    }
    .sidebar-brand h2 {
        font-weight: 900;
        font-size: 1.6rem;
        color: #00A651;
        margin: 0;
        letter-spacing: 1px;
    }
    .sidebar-brand p {
        font-size: 0.65rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: #999;
        margin: 0.2rem 0 0 0;
    }

    /* Sidebar radio → botones 3D */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div {
        gap: 0.4rem !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div > label {
        background: linear-gradient(180deg, #f7f9fc 0%, #e8ecf1 100%);
        border: 1px solid #d0d5dd;
        border-radius: 10px;
        padding: 0.55rem 0.9rem !important;
        margin: 0 !important;
        cursor: pointer;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,.08), inset 0 1px 0 rgba(255,255,255,.9);
        display: flex !important;
        align-items: center;
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div > label:hover {
        background: linear-gradient(180deg, #e8f5ee 0%, #d4edda 100%);
        border-color: #00A651;
        box-shadow: 0 3px 8px rgba(0,166,81,.15), inset 0 1px 0 rgba(255,255,255,.9);
        transform: translateY(-1px);
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div > label:active {
        transform: translateY(1px);
        box-shadow: inset 0 2px 4px rgba(0,0,0,.1);
    }
    /* Radio seleccionado */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div > label[data-checked="true"],
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div > label:has(input:checked) {
        background: linear-gradient(180deg, #00A651 0%, #008a44 100%);
        border-color: #007a3d;
        color: white !important;
        box-shadow: 0 3px 8px rgba(0,166,81,.3), inset 0 1px 0 rgba(255,255,255,.15);
    }
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div > label:has(input:checked) p,
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div > label:has(input:checked) span,
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div > label:has(input:checked) div {
        color: white !important;
    }
    /* Ocultar el círculo del radio */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div > label > div:first-child {
        display: none !important;
    }
    /* Texto del label */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div > label p {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600;
        font-size: 0.85rem;
        margin: 0;
    }

    /* Mapa container */
    .map-container {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e0e5ec;
    }

    /* Loader perrito */
    @keyframes olfatear {
        0% { transform: translateX(-80px) scaleX(-1); }
        45% { transform: translateX(80px) scaleX(-1); }
        50% { transform: translateX(80px) scaleX(1); }
        95% { transform: translateX(-80px) scaleX(1); }
        100% { transform: translateX(-80px) scaleX(-1); }
    }
    .perrito-loader {
        text-align: center;
        padding: 2rem;
        overflow: hidden;
    }
    .perrito-loader img {
        width: 120px;
        animation: olfatear 3s ease-in-out infinite;
    }
    .perrito-loader p {
        color: #666666;
        font-size: 0.85rem;
        margin-top: 0.8rem;
    }

    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Responsive */
    @media (max-width: 768px) {
        .header-gradient h1 { font-size: 1.5rem; }
        .metric-value { font-size: 1.3rem; }
        .bp-card { padding: 0.8rem; }
    }
    </style>
    """, unsafe_allow_html=True)
