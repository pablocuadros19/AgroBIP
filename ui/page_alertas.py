"""Feed de alertas — lista filtrable con cards estilizadas."""

import streamlit as st
from ui.components import render_divider, render_section_label, render_alert_card, render_metric_card
from ui.theme import ALERT_TYPES
from services.alerts import get_alertas, get_kpis_alertas


def render_page_alertas():
    """Renderiza el feed de alertas."""

    st.markdown("### Alertas")
    render_divider()

    # --- KPIs (todas las provincias) ---
    kpis = get_kpis_alertas()
    c1, c2, c3, c4 = st.columns(4)
    render_metric_card(f"{kpis['total']}", "Total alertas", c1)
    render_metric_card(f"{kpis['nuevas']}", "Nuevas", c2)
    render_metric_card(f"{kpis['criticas']}", "Críticas / Altas", c3)
    render_metric_card(f"{len(kpis['por_tipo'])}", "Tipos activos", c4)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Filtros ---
    render_section_label("Filtros")
    fc1, fc2, fc3, fc4 = st.columns(4)

    # Provincia — Buenos Aires preseleccionado
    todas_alertas = get_alertas()
    provincias_disponibles = sorted(set(a.get("provincia", "") for a in todas_alertas if a.get("provincia")))

    with fc1:
        prov_sel = st.multiselect(
            "Provincia",
            options=provincias_disponibles,
            default=["Buenos Aires"] if "Buenos Aires" in provincias_disponibles else provincias_disponibles[:1],
            key="alertas_prov",
        )

    tipos_disponibles = list(ALERT_TYPES.keys())
    tipo_labels = {k: f"{v['icon']} {v['label']}" for k, v in ALERT_TYPES.items()}

    with fc2:
        tipo_sel = st.selectbox(
            "Tipo de alerta",
            ["Todas"] + tipos_disponibles,
            format_func=lambda x: "Todas" if x == "Todas" else tipo_labels.get(x, x),
            key="alertas_tipo",
        )

    with fc3:
        nivel_sel = st.selectbox(
            "Nivel",
            ["Todos", "critico", "alto", "medio", "bajo"],
            format_func=lambda x: x.capitalize(),
            key="alertas_nivel",
        )

    with fc4:
        estado_sel = st.selectbox(
            "Estado",
            ["Todos", "nueva", "vista", "asignada", "descartada"],
            format_func=lambda x: x.capitalize(),
            key="alertas_estado",
        )

    # --- Aplicar filtros ---
    tipo_f = None if tipo_sel == "Todas" else tipo_sel
    nivel_f = None if nivel_sel == "Todos" else nivel_sel
    estado_f = None if estado_sel == "Todos" else estado_sel

    alertas = get_alertas(tipo=tipo_f, nivel=nivel_f, estado=estado_f)

    # Filtrar por provincia seleccionada
    if prov_sel:
        alertas = [a for a in alertas if a.get("provincia") in prov_sel]

    # --- Resultados ---
    st.markdown(f"**{len(alertas)}** alertas encontradas")
    st.markdown("<br>", unsafe_allow_html=True)

    if not alertas:
        st.info("No hay alertas que coincidan con los filtros.")
        return

    # --- Cards ---
    for alerta in sorted(alertas, key=lambda a: a["fecha"], reverse=True):
        render_alert_card(alerta)

    st.caption("Fuente: MAGyP — Estimaciones Agrícolas. Alertas generadas desde variación de superficie y ratio cosechada/sembrada.")
