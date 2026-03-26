"""Tabla de scoring — datos reales con métricas comerciales."""

import streamlit as st
import pandas as pd
from ui.components import render_divider, render_section_label, render_metric_card
from ui.theme import get_score_band
from services.scoring import get_all_scores, get_kpis


def render_page_scoring():
    """Renderiza la tabla de scoring con datos reales."""

    st.markdown("### Scoring por departamento")
    render_divider()

    all_scores = get_all_scores()
    if not all_scores:
        st.info("No hay datos de scoring disponibles.")
        return

    # --- KPIs ---
    kpis = get_kpis()
    c1, c2, c3, c4 = st.columns(4)
    render_metric_card(f"{kpis['total']}", "Total departamentos", c1)
    render_metric_card(f"{kpis['promedio']}", "Score promedio", c2)
    render_metric_card(f"{kpis['alta']}", "Alta prioridad", c3)
    render_metric_card(f"USD {kpis.get('vbp_total_usd', 0)/1_000_000_000:.1f}B", "VBP total", c4)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Filtros ---
    render_section_label("Filtros")
    fc1, fc2, fc3 = st.columns(3)

    provincias = sorted(set(s["provincia"] for s in all_scores))
    with fc1:
        prov_sel = st.multiselect("Provincia", provincias, default=provincias, key="scoring_prov")

    with fc2:
        banda_sel = st.selectbox(
            "Banda",
            ["Todas", "Alta (80-100)", "Media (60-79)", "Observar (40-59)", "Sin prioridad (0-39)"],
            key="scoring_banda",
        )

    tipos_zona = sorted(set(s.get("tipo_zona", "") for s in all_scores))
    with fc3:
        tipo_sel = st.multiselect(
            "Tipo de zona", tipos_zona, default=tipos_zona,
            format_func=lambda x: x.capitalize(),
            key="scoring_tipo",
        )

    # --- Filtrar ---
    filtrado = all_scores

    if prov_sel:
        filtrado = [s for s in filtrado if s["provincia"] in prov_sel]

    if banda_sel != "Todas":
        if "Alta" in banda_sel:
            filtrado = [s for s in filtrado if s["score"] >= 80]
        elif "Media" in banda_sel:
            filtrado = [s for s in filtrado if 60 <= s["score"] < 80]
        elif "Observar" in banda_sel:
            filtrado = [s for s in filtrado if 40 <= s["score"] < 60]
        elif "Sin prioridad" in banda_sel:
            filtrado = [s for s in filtrado if s["score"] < 40]

    if tipo_sel:
        filtrado = [s for s in filtrado if s.get("tipo_zona", "") in tipo_sel]

    filtrado = sorted(filtrado, key=lambda x: x["score"], reverse=True)

    st.markdown(f"**{len(filtrado)}** departamentos encontrados")

    # --- Tabla con datos reales ---
    if filtrado:
        df = pd.DataFrame([
            {
                "Departamento": s["nombre"],
                "Provincia": s["provincia"],
                "Score": s["score"],
                "Etiqueta": s.get("etiqueta", ""),
                "Tipo zona": s.get("tipo_zona", "").capitalize(),
                "Cultivo principal": s.get("cultivo_principal", ""),
                "Superficie (ha)": s.get("superficie_total_ha", 0),
                "Producción (tn)": s.get("produccion_total_tm", 0),
                "VBP (USD M)": round(s.get("vbp_usd", 0) / 1_000_000, 1),
                "Productores est.": s.get("productores_estimados", 0),
                "Var. sup. %": s.get("variacion_superficie_pct", 0),
                "Cabezas": s.get("total_cabezas", 0),
            }
            for s in filtrado
        ])

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=min(500, 40 * len(df) + 40),
            column_config={
                "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
                "Superficie (ha)": st.column_config.NumberColumn(format="%d"),
                "Producción (tn)": st.column_config.NumberColumn(format="%d"),
                "VBP (USD M)": st.column_config.NumberColumn(format="%.1f"),
                "Var. sup. %": st.column_config.NumberColumn(format="%.1f%%"),
                "Cabezas": st.column_config.NumberColumn(format="%d"),
            },
        )

        # --- Exportación ---
        st.markdown("---")
        render_section_label("Exportar")
        ec1, ec2 = st.columns(2)
        with ec1:
            csv_data = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Descargar CSV completo",
                data=csv_data,
                file_name="agrobip_scoring_datos_reales.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with ec2:
            st.caption(
                f"{len(filtrado)} departamentos · "
                f"Fuente: MAGyP (producción), SENASA (ganadería), Matba Rofex (precios)"
            )
