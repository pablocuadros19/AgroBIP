"""Ficha de zona — detalle completo con datos reales."""

import streamlit as st
from ui.components import (
    render_divider, render_section_label, render_score_badge,
    render_ficha_pregunta, render_producto_sugerido, render_score_breakdown,
    render_alert_card, render_badge, render_section_highlight, render_metric_card,
)
from ui.theme import get_score_band
from services.scoring import get_score, get_all_scores
from services.zone_profile import get_perfil, sugerir_productos
from services.alerts import get_alertas_por_zona


_AGRO_PARQUET = "data/licitarg/agro-proveedores-estado.parquet"

@st.cache_data(ttl=3600, show_spinner=False)
def _cargar_agro_parquet():
    import os, pandas as pd
    if not os.path.exists(_AGRO_PARQUET):
        return None
    return pd.read_parquet(_AGRO_PARQUET)


def _render_empresas_zona(nombre_depto: str, provincia: str):
    """Muestra empresas agro del sector en la zona seleccionada."""
    import pandas as pd

    df = _cargar_agro_parquet()
    if df is None:
        st.caption("Base de empresas no disponible.")
        return

    # Filtrar por localidad que contenga el nombre del departamento
    termino = nombre_depto.upper().strip()
    mask = (
        df["dom_fiscal_localidad"].fillna("").str.upper().str.contains(termino, regex=False) |
        df["dom_fiscal_provincia"].fillna("").str.upper().str.contains("BUENOS AIRES", regex=False)
        & df["dom_fiscal_localidad"].fillna("").str.upper().str.contains(termino[:6], regex=False)
    )
    df_zona = df[mask].copy()

    if df_zona.empty:
        st.caption(f"Sin empresas registradas en {nombre_depto}.")
        return

    total = len(df_zona)
    prov_estado = int(df_zona["es_proveedor_estado"].sum())

    # KPIs rápidos
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="background:#f7f9fc;border:1px solid #e0e5ec;border-radius:10px;padding:0.8rem;text-align:center"><p style="font-size:1.5rem;font-weight:700;color:#00A651;margin:0">{total:,}</p><p style="font-size:0.7rem;font-weight:700;text-transform:uppercase;color:#555;margin:0">Empresas agro</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div style="background:#f7f9fc;border:1px solid #e0e5ec;border-radius:10px;padding:0.8rem;text-align:center"><p style="font-size:1.5rem;font-weight:700;color:#00A651;margin:0">{prov_estado}</p><p style="font-size:0.7rem;font-weight:700;text-transform:uppercase;color:#555;margin:0">Proveedoras del estado</p></div>', unsafe_allow_html=True)
    with c3:
        tipos = df_zona["tipo_societario"].value_counts().head(1)
        tipo_top = tipos.index[0] if len(tipos) > 0 else "—"
        st.markdown(f'<div style="background:#f7f9fc;border:1px solid #e0e5ec;border-radius:10px;padding:0.8rem;text-align:center"><p style="font-size:1rem;font-weight:700;color:#00A651;margin:0">{tipo_top}</p><p style="font-size:0.7rem;font-weight:700;text-transform:uppercase;color:#555;margin:0">Forma jurídica frecuente</p></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabla top empresas (priorizando proveedoras del estado)
    df_tabla = df_zona.sort_values(
        ["es_proveedor_estado", "monto_total_adj"], ascending=[False, False]
    ).head(15)

    for _, row in df_tabla.iterrows():
        es_prov = bool(row.get("es_proveedor_estado", False))
        monto = row.get("monto_total_adj")
        monto_str = ""
        if pd.notna(monto) and float(monto) > 0:
            v = float(monto)
            monto_str = f"${v/1_000_000:.1f}M adj." if v >= 1_000_000 else f"${v/1_000:.0f}K adj."

        actividad = str(row.get("actividad_descripcion", "")).strip()[:50]
        localidad = str(row.get("dom_fiscal_localidad", "")).strip()
        cuit = str(row.get("cuit", "")).strip()
        if len(cuit) == 11:
            cuit_fmt = f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"
        else:
            cuit_fmt = cuit

        badge_estado = '<span style="background:#e8f5ee;color:#00A651;font-size:0.65rem;font-weight:700;padding:0.15rem 0.5rem;border-radius:20px;margin-left:0.4rem">PROV. ESTADO</span>' if es_prov else ""
        st.markdown(f"""
        <div style="background:#f7f9fc;border:1px solid {'#c8e6d5' if es_prov else '#e0e5ec'};border-left:3px solid {'#00A651' if es_prov else '#e0e5ec'};border-radius:8px;padding:0.6rem 0.9rem;margin:0.25rem 0">
            <span style="font-size:0.88rem;font-weight:700;color:#1a1a2e">{row.get('razon_social','').strip()}</span>{badge_estado}
            <span style="float:right;font-size:0.82rem;font-weight:700;color:#00A651">{monto_str}</span>
            <br><span style="font-size:0.75rem;color:#888">{cuit_fmt} · {localidad} · {actividad}</span>
        </div>
        """, unsafe_allow_html=True)


def render_page_ficha():
    """Renderiza la ficha de zona con datos reales."""

    st.markdown("### Ficha de zona")
    render_divider()

    # --- Selector de departamento ---
    all_scores = get_all_scores()
    opciones = {s["id"]: f"{s['nombre']} ({s['provincia']}) — Score: {s['score']}" for s in sorted(all_scores, key=lambda x: -x["score"])}

    if not opciones:
        st.info("No hay departamentos con score calculado.")
        return

    depto_id = st.selectbox(
        "Seleccioná un departamento",
        options=list(opciones.keys()),
        format_func=lambda x: opciones[x],
        key="ficha_depto_sel",
    )

    if not depto_id:
        return

    score_data = get_score(depto_id)
    perfil = get_perfil(depto_id)

    if not score_data:
        st.warning("No hay datos de scoring para este departamento.")
        return

    # --- Header ---
    band = get_score_band(score_data["score"])
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin:1rem 0;">
        <div>
            <span style="font-size:1.4rem; font-weight:900; color:#1a1a2e;">{score_data['nombre']}</span>
            <br><span style="font-size:0.85rem; color:#666;">{score_data['provincia']} · {score_data.get('tipo_zona', '').capitalize()} · {score_data.get('cultivo_principal', '')}</span>
        </div>
        <div style="text-align:right;">
            <span style="font-size:2.5rem; font-weight:900; color:{band['color']};">{score_data['score']}</span>
            <br>{render_score_badge(score_data['score'])}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Etiqueta
    etiqueta = score_data.get("etiqueta", "")
    if etiqueta:
        st.markdown(f"""
        <div style="margin-bottom:1rem;">
            {render_badge(etiqueta, band['color'], band['bg'])}
        </div>
        """, unsafe_allow_html=True)

    # --- KPIs comerciales reales ---
    render_section_label("Datos comerciales")
    c1, c2, c3, c4 = st.columns(4)
    sup = score_data.get("superficie_total_ha", 0)
    prod = score_data.get("produccion_total_tm", 0)
    vbp = score_data.get("vbp_usd", 0)
    productores = score_data.get("productores_estimados", 0)

    render_metric_card(f"{sup:,} ha", "Superficie sembrada", c1)
    render_metric_card(f"{prod:,} tn", "Producción", c2)
    render_metric_card(f"USD {vbp/1_000_000:.1f}M", "VBP estimado", c3)
    render_metric_card(f"~{productores}", "Productores est.", c4)

    variacion = score_data.get("variacion_superficie_pct", 0)
    cabezas = score_data.get("total_cabezas", 0)
    if variacion != 0 or cabezas > 0:
        c1, c2, c3 = st.columns(3)
        if variacion != 0:
            signo = "+" if variacion > 0 else ""
            render_metric_card(f"{signo}{variacion:.1f}%", "Var. superficie", c1)
        if cabezas > 0:
            render_metric_card(f"{cabezas:,}", "Cabezas bovinas (SENASA)", c2)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Desglose de score ---
    render_section_label("Desglose del score")
    if score_data.get("componentes"):
        labels = {
            "perfil_productivo": "Perfil productivo (35%) — MAGyP",
            "dinamica_cambio": "Dinámica de cambio (25%) — MAGyP",
            "estres_hidrico": "Pérdida de cosecha (20%) — MAGyP",
            "emergencia_riesgo": "Emergencia / riesgo (20%) — decretos",
        }
        componentes_display = {labels.get(k, k): v for k, v in score_data["componentes"].items()}
        render_score_breakdown(componentes_display)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Las 4 preguntas ---
    if perfil and perfil.get("ficha"):
        ficha = perfil["ficha"]
        render_section_label("Análisis de zona")

        render_ficha_pregunta("¿Qué pasa en esta zona?", ficha.get("que_pasa", "Sin datos."))
        render_ficha_pregunta("¿Por qué importa?", ficha.get("por_que_importa", "Sin datos."))
        render_ficha_pregunta("¿Qué producto ofrecer?", ficha.get("que_producto", "Sin datos."))
        render_ficha_pregunta("¿Qué prioridad tiene?", ficha.get("que_prioridad", "Sin datos."))

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Productos BP sugeridos ---
    render_section_label("Productos BP sugeridos para esta zona")
    productos = sugerir_productos(depto_id, score_data)
    for producto in productos:
        render_producto_sugerido(producto)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Producción agrícola real ---
    if perfil and perfil.get("cultivos"):
        render_section_label(f"Producción agrícola — Campaña {perfil.get('campania', '—')}")

        for cultivo in perfil["cultivos"]:
            sup_ha = cultivo.get("superficie_ha", 0)
            prod_tm = cultivo.get("produccion_tm", 0)
            rend = cultivo.get("rendimiento_kgxha", 0)
            vbp_cult = cultivo.get("vbp_usd", 0)
            pct = cultivo.get("pct_superficie", 0)
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center;
                        padding:0.5rem 0.8rem; margin:0.2rem 0; background:#f7f9fc;
                        border-radius:8px; border:1px solid #e0e5ec;">
                <div>
                    <span style="font-weight:700; font-size:0.85rem;">{cultivo['nombre']}</span>
                    <span style="color:#999; font-size:0.75rem;"> ({pct}%)</span>
                </div>
                <div style="text-align:right; font-size:0.8rem;">
                    <span style="color:#00A651; font-weight:700;">{sup_ha:,} ha</span>
                    <span style="color:#666;"> · {prod_tm:,} tn · {rend:,} kg/ha</span>
                    <span style="color:#1565c0; font-weight:600;"> · USD {vbp_cult/1000:,.0f}k</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # --- Perfil ganadero ---
    if perfil and perfil.get("bovinos"):
        st.markdown("<br>", unsafe_allow_html=True)
        render_section_label("Stock ganadero — SENASA")
        bovinos = perfil["bovinos"]
        cols = st.columns(min(len(bovinos), 4))
        for i, (cat, cantidad) in enumerate(bovinos.items()):
            if cantidad > 0:
                render_metric_card(f"{cantidad:,}", cat.capitalize(), cols[i % len(cols)])

    # --- Emergencia activa ---
    if perfil and perfil.get("emergencia_activa"):
        st.markdown("<br>", unsafe_allow_html=True)
        render_section_highlight(
            "🚨 <b>Emergencia agropecuaria activa.</b> "
            "Aplican condiciones especiales de refinanciación y prórroga."
        )

    # --- Tendencia de superficie ---
    if perfil and perfil.get("tendencia"):
        st.markdown("<br>", unsafe_allow_html=True)
        render_section_label("Evolución de superficie sembrada (últimas campañas)")
        tend = perfil["tendencia"]
        import pandas as pd
        df_tend = pd.DataFrame(tend)
        if not df_tend.empty and "campania" in df_tend.columns:
            df_tend = df_tend.set_index("campania")
            st.bar_chart(df_tend[["superficie_total_ha"]], use_container_width=True, height=200)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Alertas de la zona ---
    alertas_zona = get_alertas_por_zona(depto_id)
    if alertas_zona:
        render_section_label(f"Alertas activas ({len(alertas_zona)})")
        for alerta in alertas_zona:
            render_alert_card(alerta)

    # --- Empresas del sector (LICITARG) ---
    st.markdown("<br>", unsafe_allow_html=True)
    render_section_label("Empresas del sector en esta zona")
    _render_empresas_zona(score_data.get("nombre", ""), score_data.get("provincia", ""))

    # --- Fuentes ---
    if perfil and perfil.get("fuentes"):
        st.markdown("<br>", unsafe_allow_html=True)
        fuentes = perfil["fuentes"]
        fuentes_text = " · ".join(v for v in fuentes.values() if v)
        st.caption(f"Fuentes: {fuentes_text}")
