"""AgroBip — Radar de inteligencia comercial anticipada para banca agropecuaria."""

import streamlit as st
from ui.theme import inject_css
from ui.components import render_header, render_sidebar_brand, render_footer

# --- Config ---
st.set_page_config(
    page_title="AgroBip · Banco Provincia",
    page_icon="assets/agrobiplogo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# --- Sidebar ---
with st.sidebar:
    render_sidebar_brand()

    st.markdown("---")

    pagina = st.radio(
        "Navegación",
        [
            "🏠 Dashboard",
            "🗺️ Radar Territorial",
            "📈 Producción",
            "🔔 Alertas",
            "📊 Scoring",
            "📋 Ficha de Zona",
        ],
        key="nav_pagina",
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Datos del usuario (simulados)
    st.markdown(
        '<p style="font-size:0.7rem; font-weight:700; text-transform:uppercase; '
        'letter-spacing:2px; color:#999; margin-bottom:0.3rem;">Mi perfil</p>',
        unsafe_allow_html=True,
    )
    st.text_input("Nombre", value="Pablo", key="user_nombre", disabled=True)
    st.text_input("Sucursal", value="Casa Matriz", key="user_sucursal", disabled=True)
    st.text_input("Zona asignada", value="Pampa Húmeda", key="user_zona", disabled=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("AgroBip v0.2 · Sprint 2 · Datos MAGyP + SENASA")

# --- Header ---
render_header()

# --- Routing ---
if "Dashboard" in pagina:
    from ui.page_dashboard import render_page_dashboard
    render_page_dashboard()

elif "Radar" in pagina:
    from ui.page_radar import render_page_radar
    render_page_radar()

elif "Alertas" in pagina:
    from ui.page_alertas import render_page_alertas
    render_page_alertas()

elif "Producción" in pagina:
    from ui.page_produccion import render_page_produccion
    render_page_produccion()

elif "Scoring" in pagina:
    from ui.page_scoring import render_page_scoring
    render_page_scoring()

elif "Ficha" in pagina:
    from ui.page_ficha import render_page_ficha
    render_page_ficha()

# --- Footer ---
st.markdown("<br><br>", unsafe_allow_html=True)
render_footer()
