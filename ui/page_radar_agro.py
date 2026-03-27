"""Radar Agro — Bandeja de prospectos agropecuarios con scoring y clasificación."""

import streamlit as st
import pandas as pd
import json
from datetime import datetime

from ui.theme import CLASIFICACION_COLORS, SEMAFORO_COLORS
from ui.components import (
    render_metric_card, render_section_label, render_divider,
    render_score_breakdown, render_prospect_card, render_clasificacion_badge,
    render_semaforo_badge, render_evolucion_badge, render_ficha_pregunta,
    render_producto_sugerido, render_perrito_loader,
)


def render_page_radar_agro():
    st.markdown('<h2 style="font-weight:700;color:#1a1a2e;margin-bottom:0.2rem">🎯 Radar Agro</h2>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:0.85rem;color:#666;margin-bottom:1.5rem">Bandeja de prospectos agropecuarios — clasificación, scoring y priorización comercial</p>', unsafe_allow_html=True)

    from services.radar_models import get_kpis, get_prospectos, get_prospecto, get_top_bancos_competencia, exportar_df, get_partidos_distintos

    kpis = get_kpis()

    # Si no hay datos, mostrar panel de importación directo
    if kpis["total"] == 0:
        _render_panel_importacion()
        return

    # --- KPIs principales ---
    render_section_label("Resumen del universo")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_metric_card(f"{kpis['total']:,}", "Total prospectos")
    with c2:
        render_metric_card(str(kpis["contactar"]), "Para contactar")
    with c3:
        render_metric_card(str(kpis["score_promedio"]), "Score promedio")
    with c4:
        render_metric_card(str(kpis["clientes_bp"]), "Clientes BP")
    with c5:
        render_metric_card(str(kpis["pendientes_bcra"]), "Pendientes BCRA")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Distribución por clasificación ---
    render_section_label("Distribución por clasificación")
    cols_clas = st.columns(len(CLASIFICACION_COLORS) - 1)  # sin 'pendiente'
    for i, (clas_key, clas_info) in enumerate(CLASIFICACION_COLORS.items()):
        if clas_key == "pendiente":
            continue
        idx = min(i, len(cols_clas) - 1)
        with cols_clas[idx]:
            n = kpis["por_clasificacion"].get(clas_key, 0)
            st.markdown(
                f'<div style="text-align:center;background:{clas_info["bg"]};border:1px solid {clas_info["color"]}30;'
                f'border-radius:10px;padding:0.5rem">'
                f'<span style="font-size:1.3rem;font-weight:700;color:{clas_info["color"]}">{n}</span><br>'
                f'<span style="font-size:0.65rem;font-weight:600;color:{clas_info["color"]}">{clas_info["icon"]} {clas_info["label"]}</span>'
                f'</div>', unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Top 5 del día ---
    top5 = get_prospectos(
        filtros={"semaforo": ["contactar"]},
        orden="score_total DESC",
        limite=5,
    )
    if top5:
        render_section_label("Oportunidades destacadas")
        for p in top5:
            render_prospect_card(p)
        st.markdown("<br>", unsafe_allow_html=True)

    render_divider()

    # --- Mapa de concentración competitiva ---
    bancos = get_top_bancos_competencia(5)
    if bancos:
        render_section_label("Concentración competitiva — Top bancos")
        for banco in bancos:
            entidad = banco["entidad"][:35]
            cantidad = banco["cantidad"]
            pct = banco["pct_promedio"]
            ancho = min(cantidad / max(b["cantidad"] for b in bancos) * 100, 100)
            st.markdown(
                f'<div style="margin:0.2rem 0">'
                f'<span style="font-size:0.78rem;font-weight:600;color:#1a1a2e">{entidad}</span>'
                f'<span style="font-size:0.7rem;color:#888;margin-left:0.5rem">{cantidad} prospectos · {pct}% conc. prom.</span>'
                f'<div style="background:#e0e5ec;border-radius:4px;height:6px;margin-top:0.15rem">'
                f'<div style="background:linear-gradient(90deg,#00A651,#00B8D4);width:{ancho}%;height:6px;border-radius:4px"></div>'
                f'</div></div>', unsafe_allow_html=True,
            )
        st.markdown("<br>", unsafe_allow_html=True)
        render_divider()

    # --- Filtros ---
    render_section_label("Filtros")

    # Fila 1: Partido (el más importante para navegación territorial)
    partidos_disponibles = get_partidos_distintos()
    filtro_partido = st.multiselect("Partido / Localidad", partidos_disponibles, key="radar_f_partido")

    # Fila 2: Clasificación, semáforo, prioridad, búsqueda
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        opciones_clas = [k for k in CLASIFICACION_COLORS if k != "pendiente"]
        filtro_clas = st.multiselect("Clasificacion", opciones_clas, key="radar_f_clas")
    with fc2:
        opciones_sem = [k for k in SEMAFORO_COLORS if k != "pendiente"]
        filtro_sem = st.multiselect("Semaforo", opciones_sem, key="radar_f_sem")
    with fc3:
        filtro_pri = st.selectbox("Prioridad", ["Todas", "alta", "media", "baja"], key="radar_f_pri")
    with fc4:
        filtro_busq = st.text_input("Buscar (CUIT o razon social)", key="radar_f_busq")

    # Fila 3: Cadena, checkboxes
    fc5, fc6, fc7, fc8 = st.columns(4)
    with fc5:
        filtro_cadena = st.selectbox(
            "Cadena agro", ["Todas", "agricola", "ganadera", "mixta", "lactea", "agroindustrial"],
            key="radar_f_cadena",
        )
    with fc6:
        filtro_bp = st.checkbox("Solo clientes BP", key="radar_f_bp")
    with fc7:
        filtro_prov_est = st.checkbox("Solo proveedores del estado", key="radar_f_prov")
    with fc8:
        filtro_deuda_bp = st.checkbox("Con deuda en BP", key="radar_f_deuda_bp")

    filtros = {}
    if filtro_partido:
        filtros["partido"] = filtro_partido
    if filtro_clas:
        filtros["clasificacion"] = filtro_clas
    if filtro_sem:
        filtros["semaforo"] = filtro_sem
    if filtro_pri != "Todas":
        filtros["prioridad"] = filtro_pri
    if filtro_busq:
        filtros["busqueda"] = filtro_busq
    if filtro_cadena != "Todas":
        filtros["cadena_agro"] = filtro_cadena
    if filtro_bp:
        filtros["solo_clientes_bp"] = True
    if filtro_prov_est:
        filtros["solo_proveedor_estado"] = True
    if filtro_deuda_bp:
        filtros["deuda_bapro"] = True

    # Orden
    orden_opciones = {
        "Score (mayor primero)": "score_total DESC",
        "Score (menor primero)": "score_total ASC",
        "Razón social A-Z": "razon_social ASC",
        "Monto BCRA (mayor)": "bcra_monto_total DESC",
        "Entidades BCRA (mayor)": "bcra_cantidad_entidades DESC",
    }
    orden_sel = st.selectbox("Ordenar por", list(orden_opciones.keys()), key="radar_orden")

    # --- Tabla de resultados ---
    prospectos = get_prospectos(filtros=filtros, orden=orden_opciones[orden_sel])
    st.markdown(f'<p style="font-size:0.8rem;color:#888;margin:0.5rem 0">{len(prospectos)} prospectos encontrados</p>', unsafe_allow_html=True)

    if prospectos:
        df = pd.DataFrame(prospectos)

        # Formatear para display
        df_display = df[[
            "cuit", "razon_social", "partido", "clasificacion", "score_total",
            "semaforo", "prioridad", "bcra_monto_total",
            "bcra_entidad_principal", "es_cliente_bp", "bcra_deuda_bapro",
        ]].copy()

        df_display.columns = [
            "CUIT", "Razon social", "Partido", "Clasificacion", "Score",
            "Semaforo", "Prioridad", "Exposicion BCRA",
            "Entidad principal", "Cliente BP", "Deuda BP",
        ]

        # Formatear valores
        df_display["Cliente BP"] = df_display["Cliente BP"].map({1: "Si", 0: "No"})
        df_display["Deuda BP"] = df_display["Deuda BP"].map({1: "Si", 0: "No", True: "Si", False: "No"})
        df_display["Exposicion BCRA"] = df_display["Exposicion BCRA"].apply(
            lambda x: f"${x/1000:.1f}M" if x and x > 0 else "—"
        )

        st.dataframe(
            df_display,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Score", min_value=0, max_value=100, format="%d",
                ),
            },
            use_container_width=True,
            height=min(400 + len(df_display) * 2, 700),
            hide_index=True,
        )

        # --- Exportar ---
        st.markdown("<br>", unsafe_allow_html=True)
        render_section_label("Exportar")
        ec1, ec2 = st.columns(2)
        with ec1:
            df_export = exportar_df(filtros=filtros)
            csv_data = df_export.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Descargar CSV", csv_data,
                file_name="radar_agro_prospectos.csv", mime="text/csv",
            )
        with ec2:
            from io import BytesIO
            buffer = BytesIO()
            df_export.to_excel(buffer, index=False, engine="openpyxl")
            st.download_button(
                "📥 Descargar Excel", buffer.getvalue(),
                file_name="radar_agro_prospectos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    render_divider()

    # --- Detalle del prospecto ---
    if prospectos:
        render_section_label("Detalle del prospecto")
        opciones_detalle = [
            f"{p['razon_social'][:40]} ({p['cuit']}) — Score: {p['score_total']}"
            for p in prospectos
        ]
        idx_sel = st.selectbox("Seleccionar prospecto", range(len(opciones_detalle)),
                               format_func=lambda i: opciones_detalle[i], key="radar_detalle_sel")

        if idx_sel is not None:
            _render_detalle(prospectos[idx_sel])

    render_divider()

    # --- Panel de importación ---
    with st.expander("⚙️ Importación y procesamiento", expanded=False):
        _render_panel_importacion()


def _render_detalle(p: dict):
    """Ficha de detalle completa de un prospecto."""
    cuit = p.get("cuit", "")
    if len(cuit) == 11:
        cuit_fmt = f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"
    else:
        cuit_fmt = cuit

    # Header
    st.markdown(f"""
    <div style="background:#f7f9fc;border:1px solid #e0e5ec;border-radius:14px;padding:1.2rem;margin:0.5rem 0">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">
            <div>
                <span style="font-size:1.2rem;font-weight:700;color:#1a1a2e">{p.get('razon_social', 'Sin nombre')}</span>
                <br><span style="font-size:0.8rem;color:#888">{cuit_fmt} · {p.get('partido', '')} · {p.get('provincia', '')}</span>
            </div>
            <div style="text-align:right">
                <span style="font-size:2.2rem;font-weight:900;color:#00A651">{p.get('score_total', 0)}</span>
                <br><span style="font-size:0.7rem;font-weight:600;color:#888">SCORE COMERCIAL</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        render_clasificacion_badge(p.get("clasificacion", "pendiente"))
    with bc2:
        render_semaforo_badge(p.get("semaforo", "pendiente"))
    with bc3:
        st.markdown(
            f'<span style="background:#f7f9fc;border:1px solid #e0e5ec;font-size:0.78rem;'
            f'font-weight:600;padding:0.2rem 0.7rem;border-radius:20px;color:#1a1a2e">'
            f'Prioridad: {p.get("prioridad", "baja").upper()}</span>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Métricas BCRA
    render_section_label("Perfil financiero (BCRA)")
    mc1, mc2, mc3, mc4 = st.columns(4)
    monto = p.get("bcra_monto_total", 0)
    monto_str = f"${monto/1000:.1f}M" if monto > 0 else "—"
    with mc1:
        render_metric_card(monto_str, "Exposición total")
    with mc2:
        render_metric_card(str(p.get("bcra_cantidad_entidades", 0)), "Entidades")
    with mc3:
        sit_texto = p.get("bcra_situacion_texto") or "No consultado"
        render_metric_card(sit_texto[:20], "Situación")
    with mc4:
        pct = p.get("bcra_pct_entidad_principal", 0)
        render_metric_card(f"{pct:.0f}%" if pct > 0 else "—", "Concentración")

    if p.get("bcra_entidad_principal"):
        st.markdown(
            f'<p style="font-size:0.78rem;color:#555;margin-top:0.3rem">'
            f'Entidad principal: <b>{p["bcra_entidad_principal"]}</b></p>',
            unsafe_allow_html=True,
        )

    if p.get("bcra_evolucion"):
        st.markdown('<span style="font-size:0.75rem;color:#888">Evolución:</span>', unsafe_allow_html=True)
        render_evolucion_badge(p.get("bcra_evolucion", ""))

    st.markdown("<br>", unsafe_allow_html=True)

    # Perfil sectorial
    render_section_label("Perfil sectorial")
    ps1, ps2, ps3 = st.columns(3)
    with ps1:
        st.markdown(f'<p style="font-size:0.8rem"><b>Cadena:</b> {p.get("cadena_agro", "—")}</p>', unsafe_allow_html=True)
    with ps2:
        st.markdown(f'<p style="font-size:0.8rem"><b>Tipo actor:</b> {p.get("subtipo_actor", "—")}</p>', unsafe_allow_html=True)
    with ps3:
        bp_label = "Sí (Procampo)" if p.get("es_cliente_bp") else "No"
        st.markdown(f'<p style="font-size:0.8rem"><b>Cliente BP:</b> {bp_label}</p>', unsafe_allow_html=True)

    tags = p.get("tags", "[]")
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []
    if tags:
        tags_html = " ".join(
            f'<span style="background:#e8f5ee;color:#00A651;font-size:0.7rem;font-weight:600;'
            f'padding:0.15rem 0.5rem;border-radius:20px">{t}</span>'
            for t in tags
        )
        st.markdown(tags_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Score desglosado
    render_section_label("Score explicado")
    componentes = {
        "Perfil sectorial (20%)": p.get("score_perfil_sectorial", 0),
        "Oportunidad financiera (35%)": p.get("score_oportunidad_financiera", 0),
        "Relevancia comercial (25%)": p.get("score_relevancia_comercial", 0),
        "Calidad de datos (20%)": p.get("score_calidad_datos", 0),
    }
    render_score_breakdown(componentes)

    st.markdown("<br>", unsafe_allow_html=True)

    # Motivos
    render_section_label("Interpretación comercial")
    if p.get("clasificacion_motivo"):
        render_ficha_pregunta("¿Por qué esta clasificación?", p["clasificacion_motivo"])
    if p.get("score_motivo"):
        render_ficha_pregunta("¿Qué dice el scoring?", p["score_motivo"])

    # Productos sugeridos
    from services.radar_classifier import sugerir_productos
    productos = sugerir_productos(p)
    if productos:
        st.markdown("<br>", unsafe_allow_html=True)
        render_section_label("Productos BP sugeridos")
        for prod in productos:
            render_producto_sugerido(prod)


def _render_panel_importacion():
    """Panel de importación, Procampo y procesamiento BCRA."""
    from services.radar_models import (
        get_kpis, get_partidos_distintos, get_pendientes_bcra_por_partido,
        actualizar_prospecto,
    )
    from services.radar_pipeline import (
        importar_csv, importar_licitarg, cargar_procampo,
        ejecutar_bcra, ejecutar_bcra_por_partido, clasificar_todos,
    )
    from services.bcra_client import consultar_cuit_completo, limpiar_cuit

    st.markdown("### Importar prospectos")

    ic1, ic2 = st.columns(2)

    with ic1:
        st.markdown("**Desde LICITARG** (120K empresas agro)")
        if st.button("Importar base LICITARG", key="btn_licitarg"):
            with st.spinner("Importando..."):
                stats = importar_licitarg()
            if stats.get("error"):
                st.error(stats["error"])
            else:
                st.success(f"{stats['nuevos']:,} nuevos / {stats['duplicados']:,} ya existian")
            st.rerun()

    with ic2:
        st.markdown("**Desde CSV / Excel**")
        archivo = st.file_uploader("Subir archivo de prospectos", type=["csv", "xlsx", "xls"], key="upload_csv")
        if archivo and st.button("Importar", key="btn_csv"):
            with st.spinner("Importando..."):
                stats = importar_csv(archivo, archivo.name)
            if stats.get("error"):
                st.error(stats["error"])
            else:
                st.success(f"{stats['nuevos']:,} nuevos / {stats['duplicados']:,} duplicados")
            st.rerun()

    st.markdown("---")

    # --- BCRA individual ---
    st.markdown("### Consultar BCRA individual")
    bc1, bc2 = st.columns([3, 1])
    with bc1:
        cuit_manual = st.text_input("Ingresar CUIT", placeholder="20-12345678-9", key="bcra_cuit_manual")
    with bc2:
        st.markdown("<br>", unsafe_allow_html=True)
        btn_bcra_manual = st.button("Consultar CUIT", key="btn_bcra_manual")

    if cuit_manual and btn_bcra_manual:
        cuit_limpio = limpiar_cuit(cuit_manual)
        if len(cuit_limpio) != 11:
            st.error("CUIT invalido — debe tener 11 digitos")
        else:
            with st.spinner(f"Consultando BCRA para {cuit_limpio}..."):
                resultado = consultar_cuit_completo(cuit_limpio)
            if resultado.get("bcra_situacion", -1) != -1:
                # Guardar en prospecto si existe
                campos_bcra = {k: v for k, v in resultado.items() if k.startswith("bcra_")}
                campos_bcra["fecha_bcra"] = datetime.now().isoformat()
                actualizar_prospecto(cuit_limpio, campos_bcra)

                # Mostrar resultado
                sit = resultado.get("bcra_situacion_texto", "")
                monto = resultado.get("bcra_monto_total", 0)
                ent = resultado.get("bcra_cantidad_entidades", 0)
                princ = resultado.get("bcra_entidad_principal", "")
                deuda_bp = "Si" if resultado.get("bcra_deuda_bapro") else "No"

                st.success(f"Situacion: **{sit}** — Exposicion: **${monto:,.0f}** — {ent} entidades")
                rc1, rc2, rc3 = st.columns(3)
                with rc1:
                    st.metric("Entidad principal", princ or "—")
                with rc2:
                    st.metric("Deuda con BP", deuda_bp)
                with rc3:
                    st.metric("Cheques rechazados", resultado.get("bcra_cheques_rechazados", 0))
            else:
                st.error(f"Error: {resultado.get('bcra_situacion_texto', 'Sin respuesta')}")

    st.markdown("---")

    # --- BCRA masivo filtrado por partido ---
    st.markdown("### Consultar BCRA masivo (por localidad)")
    st.markdown(
        '<p style="font-size:0.8rem;color:#888">Selecciona uno o mas partidos para consultar solo esos CUITs en BCRA. '
        'Sin filtro se consultan todos los pendientes.</p>',
        unsafe_allow_html=True,
    )

    partidos_disponibles = get_partidos_distintos()
    partidos_bcra = st.multiselect(
        "Filtrar por partido", partidos_disponibles, key="bcra_partidos",
    )

    kpis = get_kpis()
    if partidos_bcra:
        pendientes_lista = get_pendientes_bcra_por_partido(partidos_bcra)
        n_pend = len(pendientes_lista)
    else:
        n_pend = kpis.get("pendientes_bcra", 0)

    tiempo_est = n_pend * 3
    minutos = tiempo_est // 60
    st.markdown(f"**{n_pend:,}** pendientes (~{minutos} min estimados)")

    if n_pend > 500 and not partidos_bcra:
        st.warning("Hay muchos pendientes. Se recomienda filtrar por partido para acotar la consulta.")

    if n_pend > 0 and st.button("Consultar BCRA en lote", key="btn_bcra"):
        progress = st.progress(0)
        status = st.status("Consultando BCRA...", expanded=True)

        def _progress(actual, total, cuit, exito):
            progress.progress(actual / total if total > 0 else 0)
            status.update(label=f"BCRA: {actual}/{total} — {'ok' if exito else 'error'} {cuit}")

        if partidos_bcra:
            stats = ejecutar_bcra_por_partido(partidos_bcra, progress_callback=_progress)
        else:
            stats = ejecutar_bcra(progress_callback=_progress)

        status.update(
            label=f"BCRA completado: {stats['exitosos']} ok, {stats['errores']} errores",
            state="complete",
        )

        with st.spinner("Clasificando y scoreando..."):
            clasificar_todos()
        st.success("Clasificacion y scoring actualizados")
        st.rerun()

    st.markdown("---")
    st.markdown("### Reclasificar")
    if st.button("Reclasificar todo", key="btn_reclas"):
        with st.spinner("Reclasificando..."):
            clasificar_todos()
        st.success("Clasificacion y scoring actualizados")
        st.rerun()
