"""Dashboard — KPIs reales, oportunidades, top zonas, alertas."""

import streamlit as st
from ui.components import (
    render_metric_card, render_divider, render_section_label,
    render_zone_summary_card, render_alert_card, render_section_highlight,
)
from services.scoring import get_kpis, get_top_zonas
from services.alerts import get_alertas_recientes, get_kpis_alertas
from services.precios import get_precios, get_fecha_precios


def render_page_dashboard():
    """Renderiza el dashboard principal con datos reales."""

    st.markdown("### Resumen ejecutivo")
    render_divider()

    # --- KPIs principales (datos reales) ---
    render_section_label("Indicadores generales")
    kpis = get_kpis()
    kpis_alertas = get_kpis_alertas()

    c1, c2, c3, c4 = st.columns(4)
    render_metric_card(f"{kpis['total']}", "Departamentos monitoreados", c1)
    render_metric_card(f"{kpis['alta']}", "Alta prioridad", c2)
    render_metric_card(f"{kpis_alertas['nuevas']}", "Alertas nuevas", c3)
    render_metric_card(f"{kpis['promedio']}", "Score promedio", c4)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- KPIs comerciales reales ---
    render_section_label("Datos productivos reales — Fuente: MAGyP")
    c1, c2, c3, c4 = st.columns(4)
    sup_ha = kpis.get("superficie_total_ha", 0)
    prod_tm = kpis.get("produccion_total_tm", 0)
    vbp_usd = kpis.get("vbp_total_usd", 0)
    productores = kpis.get("productores_estimados", 0)

    render_metric_card(f"{sup_ha/1_000_000:.1f} M ha", "Superficie monitoreada", c1)
    render_metric_card(f"{prod_tm/1_000_000:.1f} M tn", "Producción total", c2)
    render_metric_card(f"USD {vbp_usd/1_000_000_000:.1f} B", "VBP estimado", c3)
    render_metric_card(f"~{productores:,}", "Productores estimados", c4)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Precios de referencia ---
    precios = get_precios()
    if precios:
        render_section_label(f"Precios de referencia — {get_fecha_precios()}")
        cols = st.columns(len(precios))
        for col, (grano, info) in zip(cols, precios.items()):
            render_metric_card(
                f"USD {info['precio_tn_usd']}",
                f"{grano.capitalize()} / tn",
                col,
            )
        st.markdown("<br>", unsafe_allow_html=True)

    # --- Distribución por prioridad ---
    render_section_label("Distribución por prioridad")
    c1, c2, c3, c4 = st.columns(4)
    render_metric_card(f"{kpis['alta']}", "Alta (80-100)", c1)
    render_metric_card(f"{kpis['media']}", "Media (60-79)", c2)
    render_metric_card(f"{kpis['observar']}", "Observar (40-59)", c3)
    render_metric_card(f"{kpis['baja']}", "Sin prioridad (0-39)", c4)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Layout dos columnas ---
    col_left, col_right = st.columns([1, 1])

    with col_left:
        render_section_label("Top 5 zonas por score")
        top_zonas = get_top_zonas(5)
        for zona in top_zonas:
            render_zone_summary_card(zona)

    with col_right:
        render_section_label("Alertas recientes")
        alertas = get_alertas_recientes(5)
        for alerta in alertas:
            render_alert_card(alerta)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Mensaje de contexto ---
    render_section_highlight(
        "<b>Test de lunes a la mañana:</b> ¿Sabés a dónde ir esta semana? "
        "Mirá las zonas en rojo en el <b>Radar Territorial</b> y revisá las alertas activas."
    )

    st.caption(
        "Datos de producción: MAGyP — Estimaciones Agrícolas. "
        "Datos ganaderos: SENASA — Existencias bovinas. "
        "Precios: referencia Matba Rofex. "
        "Productores: estimados desde superficie / tamaño promedio de explotación."
    )
