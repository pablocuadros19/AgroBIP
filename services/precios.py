"""Precios de mercado de granos y cálculo de VBP."""

import json
import streamlit as st
from pathlib import Path

PRECIOS_PATH = Path("data/real/precios_granos.json")


@st.cache_data(ttl=3600)
def get_precios() -> dict:
    """Retorna dict de precios por grano."""
    if not PRECIOS_PATH.exists():
        return {}
    with open(PRECIOS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("granos", {})


def get_fecha_precios() -> str:
    if not PRECIOS_PATH.exists():
        return "—"
    with open(PRECIOS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("fecha_actualizacion", "—")


def get_tipo_cambio() -> float:
    if not PRECIOS_PATH.exists():
        return 1200.0
    with open(PRECIOS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("tipo_cambio_usd_ars", 1200.0)


def calcular_vbp(produccion_depto: dict) -> dict:
    """Calcula Valor Bruto de Producción para un departamento.

    Args:
        produccion_depto: dict de get_produccion_depto() con key 'cultivos'

    Returns:
        dict con vbp_usd total, vbp_por_cultivo, etc.
    """
    precios = get_precios()
    cultivos = produccion_depto.get("cultivos", {})

    vbp_total_usd = 0.0
    vbp_por_cultivo = {}

    for cultivo, datos in cultivos.items():
        prod_tm = datos.get("produccion_tm", 0)
        # Normalizar nombre de cultivo para matchear con precios
        cultivo_key = cultivo.lower().strip()
        # Mapeo de nombres MAGyP a keys de precios
        mapeo = {"soja": "soja", "maíz": "maiz", "maiz": "maiz", "trigo": "trigo", "girasol": "girasol"}
        precio_key = mapeo.get(cultivo_key, cultivo_key)

        precio_info = precios.get(precio_key, {})
        precio_usd = precio_info.get("precio_tn_usd", 0)
        vbp_cultivo = prod_tm * precio_usd

        vbp_por_cultivo[cultivo] = {
            "produccion_tm": prod_tm,
            "precio_tn_usd": precio_usd,
            "vbp_usd": vbp_cultivo,
        }
        vbp_total_usd += vbp_cultivo

    tc = get_tipo_cambio()
    return {
        "vbp_total_usd": vbp_total_usd,
        "vbp_total_ars": vbp_total_usd * tc,
        "vbp_por_cultivo": vbp_por_cultivo,
        "fecha_precios": get_fecha_precios(),
    }
