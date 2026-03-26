"""Radar Territorial — mapa coroplético con datos reales."""

import streamlit as st
import folium
from streamlit_folium import st_folium

from ui.components import render_divider, render_section_label
from ui.theme import MAP_COLORS
from services.geo_data import cargar_geojson, filtrar_por_provincias, PROVINCIAS_MVP, get_departamento_id, get_departamento_nombre, get_provincia_nombre
from services.scoring import cargar_scores


def render_page_radar():
    """Renderiza el mapa coroplético interactivo."""

    st.markdown("### Radar Territorial")
    render_divider()

    # --- Filtros ---
    render_section_label("Filtros")
    fc1, fc2 = st.columns(2)

    with fc1:
        provincias_sel = st.multiselect(
            "Provincias", options=PROVINCIAS_MVP,
            default=["Buenos Aires"], key="radar_provincias",
        )

    with fc2:
        banda_sel = st.selectbox(
            "Banda de score",
            ["Todas", "Alta (80-100)", "Media (60-79)", "Observar (40-59)", "Sin prioridad (0-39)"],
            key="radar_banda",
        )

    if not provincias_sel:
        st.info("Seleccioná al menos una provincia.")
        return

    # --- Cargar datos ---
    geojson = cargar_geojson()
    geojson_filtrado = filtrar_por_provincias(geojson, provincias_sel)
    scores = cargar_scores()

    mapa = _crear_mapa(geojson_filtrado, scores, banda_sel)

    st.markdown('<div class="map-container">', unsafe_allow_html=True)
    map_data = st_folium(mapa, width=None, height=550, returned_objects=["last_object_clicked"])
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Leyenda ---
    st.markdown("""
    <div style="display:flex; gap:1.5rem; justify-content:center; margin:1rem 0; font-size:0.8rem;">
        <span>🔴 Alta prioridad (80-100)</span>
        <span>🟠 Media (60-79)</span>
        <span>🟡 Observar (40-59)</span>
        <span>⚪ Sin prioridad (0-39)</span>
    </div>
    """, unsafe_allow_html=True)

    if map_data and map_data.get("last_object_clicked"):
        click = map_data["last_object_clicked"]
        st.caption(f"Click detectado en: lat {click.get('lat', ''):.2f}, lon {click.get('lng', ''):.2f}")

    _render_stats(geojson_filtrado, scores)


def _crear_mapa(geojson_filtrado, scores, banda_sel):
    mapa = folium.Map(location=[-35.5, -60.0], zoom_start=7, tiles="CartoDB positron")

    features_con_score = []
    for feature in geojson_filtrado["features"]:
        depto_id = get_departamento_id(feature)
        score_data = scores.get(depto_id)
        score = score_data["score"] if score_data else 0

        if banda_sel != "Todas":
            if "Alta" in banda_sel and score < 80:
                continue
            elif "Media" in banda_sel and (score < 60 or score >= 80):
                continue
            elif "Observar" in banda_sel and (score < 40 or score >= 60):
                continue
            elif "Sin prioridad" in banda_sel and score >= 40:
                continue

        features_con_score.append((feature, score, score_data))

    for feature, score, score_data in features_con_score:
        nombre = get_departamento_nombre(feature)
        provincia = get_provincia_nombre(feature)
        color = _score_to_color(score)

        # Popup enriquecido con datos reales
        etiqueta = score_data.get("etiqueta", "") if score_data else ""
        cultivo = score_data.get("cultivo_principal", "—") if score_data else "—"
        sup = score_data.get("superficie_total_ha", 0) if score_data else 0
        vbp = score_data.get("vbp_usd", 0) if score_data else 0
        productores = score_data.get("productores_estimados", 0) if score_data else 0

        popup_html = f"""
        <div style="font-family:Montserrat,sans-serif; min-width:220px;">
            <b style="font-size:14px;">{nombre}</b><br>
            <span style="color:#666; font-size:11px;">{provincia}</span><br>
            <hr style="margin:4px 0; border-color:#e0e5ec;">
            <b style="color:{color}; font-size:18px;">{score}</b>
            <span style="font-size:11px; color:#666;"> / 100</span><br>
            <span style="font-size:11px;">{etiqueta}</span><br>
            <hr style="margin:4px 0; border-color:#e0e5ec;">
            <span style="font-size:11px;">🌾 {cultivo} · {sup:,} ha</span><br>
            <span style="font-size:11px;">💰 VBP: USD {vbp/1_000_000:.1f}M</span><br>
            <span style="font-size:11px;">👥 ~{productores} productores</span>
        </div>
        """

        folium.GeoJson(
            feature,
            style_function=lambda f, c=color: {
                "fillColor": c, "color": "#666", "weight": 0.5, "fillOpacity": 0.65,
            },
            highlight_function=lambda f: {
                "weight": 2, "color": "#00A651", "fillOpacity": 0.85,
            },
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"{nombre}: {score} · USD {vbp/1_000_000:.1f}M",
        ).add_to(mapa)

    return mapa


def _score_to_color(score):
    if score >= 80:
        return MAP_COLORS["alta"]
    elif score >= 60:
        return MAP_COLORS["media"]
    elif score >= 40:
        return MAP_COLORS["observar"]
    elif score > 0:
        return MAP_COLORS["baja"]
    else:
        return MAP_COLORS["sin_datos"]


def _render_stats(geojson_filtrado, scores):
    total = len(geojson_filtrado["features"])
    con_score = sum(1 for f in geojson_filtrado["features"] if get_departamento_id(f) in scores)
    st.caption(f"{total} departamentos en el mapa · {con_score} con score calculado desde datos MAGyP + SENASA")
