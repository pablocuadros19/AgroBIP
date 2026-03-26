"""Producción — exploración de datos reales MAGyP por cultivo y departamento."""

import streamlit as st
import pandas as pd
from ui.components import render_divider, render_section_label, render_metric_card
from services.magyp_loader import (
    cargar_produccion, get_ultima_campania, get_ranking_departamentos, get_totales_mvp,
)
from services.senasa_loader import get_totales_bovinos
from services.precios import get_precios, get_fecha_precios


def render_page_produccion():
    """Página de exploración de datos productivos reales."""

    st.markdown("### Producción agropecuaria")
    render_divider()

    # --- Totales ---
    render_section_label("Resumen regional — 5 provincias MVP")
    totales = get_totales_mvp()
    bovinos = get_totales_bovinos()

    c1, c2, c3, c4 = st.columns(4)
    render_metric_card(f"{totales['deptos']}", "Departamentos con datos", c1)
    render_metric_card(f"{totales['superficie_ha']/1_000_000:.1f} M ha", "Superficie agrícola", c2)
    render_metric_card(f"{totales['produccion_tm']/1_000_000:.1f} M tn", "Producción total", c3)
    render_metric_card(f"{bovinos['total_cabezas']/1_000_000:.1f} M cab.", f"Bovinos ({bovinos['anio']})", c4)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Selector de cultivo ---
    render_section_label("Explorar por cultivo")
    fc1, fc2 = st.columns(2)

    with fc1:
        cultivo_sel = st.selectbox(
            "Cultivo",
            ["soja", "maiz", "trigo"],
            format_func=lambda x: x.capitalize(),
            key="prod_cultivo",
        )

    with fc2:
        metrica_sel = st.selectbox(
            "Ordenar por",
            ["superficie_sembrada_ha", "produccion_tm", "rendimiento_kgxha"],
            format_func=lambda x: {
                "superficie_sembrada_ha": "Superficie sembrada (ha)",
                "produccion_tm": "Producción (tn)",
                "rendimiento_kgxha": "Rendimiento (kg/ha)",
            }.get(x, x),
            key="prod_metrica",
        )

    # --- Datos del cultivo ---
    df = cargar_produccion(cultivo_sel)
    if df.empty:
        st.warning(f"No hay datos para {cultivo_sel}.")
        return

    ultima = get_ultima_campania(df)
    precios = get_precios()
    precio_usd = precios.get(cultivo_sel, {}).get("precio_tn_usd", 0)

    # KPIs del cultivo
    df_ult = df[df["campania"] == ultima]
    c1, c2, c3, c4 = st.columns(4)
    render_metric_card(f"{df_ult['georef_id'].nunique()}", "Departamentos", c1)
    render_metric_card(f"{df_ult['superficie_sembrada_ha'].sum()/1000:.0f}k ha", "Superficie total", c2)
    render_metric_card(f"{df_ult['produccion_tm'].sum()/1000:.0f}k tn", "Producción total", c3)
    render_metric_card(f"USD {precio_usd}/tn", f"Precio ref. ({get_fecha_precios()})", c4)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Ranking ---
    render_section_label(f"Top 20 departamentos — {cultivo_sel.capitalize()} — Campaña {ultima}")
    ranking = get_ranking_departamentos(cultivo_sel, metrica_sel, n=20)

    if ranking:
        metrica_label = {
            "superficie_sembrada_ha": "Superficie (ha)",
            "produccion_tm": "Producción (tn)",
            "rendimiento_kgxha": "Rendimiento (kg/ha)",
        }.get(metrica_sel, metrica_sel)

        df_rank = pd.DataFrame(ranking)
        df_rank = df_rank.rename(columns={
            "departamento": "Departamento",
            "provincia": "Provincia",
            metrica_sel: metrica_label,
        })
        df_rank.insert(0, "#", range(1, len(df_rank) + 1))

        st.dataframe(
            df_rank[["#", "Departamento", "Provincia", metrica_label]],
            use_container_width=True, hide_index=True, height=min(500, 40 * len(df_rank) + 40),
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Evolución histórica del cultivo ---
    render_section_label(f"Evolución de superficie — {cultivo_sel.capitalize()} (últimas 10 campañas)")
    campanias = sorted(df["campania"].unique())[-10:]
    evol = df[df["campania"].isin(campanias)].groupby("campania").agg(
        superficie=("superficie_sembrada_ha", "sum"),
        produccion=("produccion_tm", "sum"),
    ).reset_index()

    if not evol.empty:
        evol = evol.set_index("campania")
        st.bar_chart(evol[["superficie"]], use_container_width=True, height=250)

    # --- Tabla completa del cultivo ---
    st.markdown("<br>", unsafe_allow_html=True)
    render_section_label(f"Datos completos — {cultivo_sel.capitalize()} — Campaña {ultima}")

    df_tabla = df_ult[["departamento", "provincia", "superficie_sembrada_ha",
                        "superficie_cosechada_ha", "produccion_tm", "rendimiento_kgxha"]].copy()
    df_tabla = df_tabla.sort_values("superficie_sembrada_ha", ascending=False)
    df_tabla.columns = ["Departamento", "Provincia", "Sup. sembrada (ha)",
                        "Sup. cosechada (ha)", "Producción (tn)", "Rend. (kg/ha)"]

    st.dataframe(df_tabla, use_container_width=True, hide_index=True,
                 height=min(400, 40 * len(df_tabla) + 40))

    # Exportar
    csv = df_tabla.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        f"Descargar {cultivo_sel} — {ultima}",
        data=csv, file_name=f"agrobip_{cultivo_sel}_{ultima.replace('/', '-')}.csv",
        mime="text/csv",
    )

    st.caption(
        f"Fuente: MAGyP — Estimaciones Agrícolas, campaña {ultima}. "
        f"Precios: referencia Matba Rofex al {get_fecha_precios()}. "
        f"Ganadería: SENASA, último dato {bovinos['anio']}."
    )
