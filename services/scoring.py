"""Motor de scoring v2 — calculado desde datos reales MAGyP + SENASA."""

import numpy as np
import streamlit as st
from services.magyp_loader import (
    get_resumen_todos_deptos, get_variacion_superficie, get_produccion_depto,
)
from services.senasa_loader import get_bovinos_depto, get_resumen_bovinos
from services.precios import calcular_vbp

# Tamaño promedio de explotación por provincia (ha) para estimar productores
TAMANO_PROMEDIO_HA = {
    "Buenos Aires": 500,
    "Córdoba": 400,
    "Santa Fe": 350,
    "Entre Ríos": 300,
    "La Pampa": 800,
}

# Departamentos con emergencia agropecuaria declarada (actualizar manualmente desde decretos)
EMERGENCIAS_ACTIVAS = {
    "06189": "Sequía prolongada — decreto 2026",  # Carlos Tejedor
    "06455": "Emergencia vigente desde enero 2026",  # Lincoln
}


def _etiqueta_score(score, vbp_usd, variacion, tiene_emergencia):
    """Genera etiqueta comercial según perfil."""
    if tiene_emergencia:
        return "EMERGENCIA ACTIVA"
    if score >= 80:
        return "ALTA PRIORIDAD"
    if variacion > 10 and vbp_usd > 50_000_000:
        return "OPORT. OFENSIVA"
    if variacion < -5:
        return "OPORT. DEFENSIVA"
    if score >= 60:
        if vbp_usd > 30_000_000:
            return "FOCO: FINANCIACIÓN"
        return "FOCO: CAP. TRABAJO"
    if score >= 40:
        return "OBSERVAR"
    return "SIN PRIORIDAD"


@st.cache_data(ttl=3600, show_spinner=False)
def _calcular_todos_los_scores() -> dict:
    """Calcula scores para todos los departamentos con datos reales."""
    resumen_agro = get_resumen_todos_deptos()
    resumen_bovinos = {r["georef_id"]: r for r in get_resumen_bovinos()}

    if not resumen_agro:
        return {}

    # Calcular VBP para todos los departamentos
    vbps = {}
    for depto in resumen_agro:
        gid = depto["georef_id"]
        prod = get_produccion_depto(gid)
        if prod:
            vbp = calcular_vbp(prod)
            vbps[gid] = vbp["vbp_total_usd"]
        else:
            vbps[gid] = 0

    # Percentiles de VBP para scoring
    vbp_values = [v for v in vbps.values() if v > 0]
    if not vbp_values:
        return {}

    vbp_array = np.array(vbp_values)

    scores_dict = {}
    for depto in resumen_agro:
        gid = depto["georef_id"]
        vbp_usd = vbps.get(gid, 0)

        # --- Dimensión 1: Perfil productivo (35%) ---
        # Percentil del VBP
        if vbp_usd > 0:
            comp_perfil = float(np.searchsorted(np.sort(vbp_array), vbp_usd) / len(vbp_array) * 100)
        else:
            comp_perfil = 0.0

        # --- Dimensión 2: Dinámica de cambio (25%) ---
        variacion = get_variacion_superficie(gid)
        if variacion > 15:
            comp_dinamica = 90.0
        elif variacion > 5:
            comp_dinamica = 70.0
        elif variacion > -5:
            comp_dinamica = 50.0
        elif variacion > -15:
            comp_dinamica = 30.0
        else:
            comp_dinamica = 10.0

        # --- Dimensión 3: Pérdida de cosecha (20%) — ratio cosechada/sembrada MAGyP ---
        sup_sembrada = depto["superficie_total_ha"]
        sup_cosechada = depto.get("superficie_cosechada_ha", 0)
        if sup_sembrada > 0 and sup_cosechada > 0:
            pct_perdida = (1 - sup_cosechada / sup_sembrada) * 100
            if pct_perdida > 30:
                comp_estres = 95.0
            elif pct_perdida > 20:
                comp_estres = 80.0
            elif pct_perdida > 10:
                comp_estres = 65.0
            elif pct_perdida > 5:
                comp_estres = 50.0
            else:
                comp_estres = 30.0
        else:
            comp_estres = 40.0

        # --- Dimensión 4: Emergencia/riesgo (20%) — decretos reales ---
        tiene_emergencia = gid in EMERGENCIAS_ACTIVAS
        comp_emergencia = 90.0 if tiene_emergencia else 50.0

        # Score final ponderado
        score = round(
            comp_perfil * 0.35 +
            comp_dinamica * 0.25 +
            comp_estres * 0.20 +
            comp_emergencia * 0.20
        )
        score = max(0, min(100, score))

        # Estimar productores
        sup_total = depto["superficie_total_ha"]
        provincia = depto["provincia"]
        tamano_prom = TAMANO_PROMEDIO_HA.get(provincia, 500)
        productores_est = max(1, round(sup_total / tamano_prom))

        # Datos ganaderos
        bovinos = resumen_bovinos.get(gid, {})
        total_cabezas = bovinos.get("total_cabezas", 0)

        # Clasificar zona
        if total_cabezas > 50000 and sup_total < 50000:
            tipo_zona = "ganadera"
        elif sup_total > 100000:
            tipo_zona = "agricola"
        elif total_cabezas > 20000 and sup_total > 30000:
            tipo_zona = "mixta"
        elif sup_total > 0:
            tipo_zona = "agricola"
        else:
            tipo_zona = "sin datos"

        etiqueta = _etiqueta_score(score, vbp_usd, variacion, tiene_emergencia)

        scores_dict[gid] = {
            "id": gid,
            "nombre": depto["departamento"],
            "provincia": provincia,
            "score": score,
            "etiqueta": etiqueta,
            "tipo_zona": tipo_zona,
            "cultivo_principal": depto["cultivo_principal"],
            "componentes": {
                "perfil_productivo": round(comp_perfil),
                "dinamica_cambio": round(comp_dinamica),
                "estres_hidrico": round(comp_estres),
                "emergencia_riesgo": round(comp_emergencia),
            },
            # Datos comerciales reales
            "superficie_total_ha": round(sup_total),
            "produccion_total_tm": round(depto["produccion_total_tm"]),
            "vbp_usd": round(vbp_usd),
            "productores_estimados": productores_est,
            "total_cabezas": total_cabezas,
            "variacion_superficie_pct": round(variacion, 1),
            "emergencia_activa": tiene_emergencia,
            "n_cultivos": depto["n_cultivos"],
        }

    return scores_dict


# --- Interfaz pública (misma que v1, sin romper la UI) ---

def cargar_scores():
    return _calcular_todos_los_scores()


def get_score(depto_id):
    return cargar_scores().get(depto_id)


def get_score_value(depto_id):
    s = get_score(depto_id)
    return s["score"] if s else 0


def get_top_zonas(n=5):
    scores = cargar_scores()
    ordenados = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
    return ordenados[:n]


def get_zonas_por_banda(banda):
    scores = cargar_scores()
    rangos = {
        "alta": (80, 100),
        "media": (60, 79),
        "observar": (40, 59),
        "baja": (0, 39),
    }
    min_s, max_s = rangos.get(banda, (0, 100))
    return [s for s in scores.values() if min_s <= s["score"] <= max_s]


def get_all_scores():
    return list(cargar_scores().values())


def get_kpis():
    scores = cargar_scores()
    all_scores = list(scores.values())

    if not all_scores:
        return {"total": 0, "alta": 0, "media": 0, "observar": 0, "baja": 0, "promedio": 0,
                "superficie_total_ha": 0, "produccion_total_tm": 0, "vbp_total_usd": 0,
                "productores_estimados": 0}

    return {
        "total": len(all_scores),
        "alta": sum(1 for s in all_scores if s["score"] >= 80),
        "media": sum(1 for s in all_scores if 60 <= s["score"] < 80),
        "observar": sum(1 for s in all_scores if 40 <= s["score"] < 60),
        "baja": sum(1 for s in all_scores if s["score"] < 40),
        "promedio": round(sum(s["score"] for s in all_scores) / len(all_scores), 1),
        # KPIs comerciales reales
        "superficie_total_ha": sum(s.get("superficie_total_ha", 0) for s in all_scores),
        "produccion_total_tm": sum(s.get("produccion_total_tm", 0) for s in all_scores),
        "vbp_total_usd": sum(s.get("vbp_usd", 0) for s in all_scores),
        "productores_estimados": sum(s.get("productores_estimados", 0) for s in all_scores),
    }
