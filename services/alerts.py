"""Alertas — generadas automáticamente desde datos reales MAGyP."""

import streamlit as st
from services.magyp_loader import get_resumen_todos_deptos, get_variacion_superficie


@st.cache_data(ttl=3600)
def _generar_alertas():
    """Genera alertas desde cambios en datos productivos reales (todas las provincias)."""
    resumen = get_resumen_todos_deptos()
    alertas = []
    alerta_id = 1000

    for depto in resumen:
        provincia = depto["provincia"]
        gid = depto["georef_id"]
        variacion = get_variacion_superficie(gid)
        nombre = depto["departamento"]
        sup = depto["superficie_total_ha"]

        # Pérdida de cosecha (ratio cosechada/sembrada)
        sup_cosechada = depto.get("superficie_cosechada_ha", 0)
        pct_cosecha = (sup_cosechada / sup * 100) if sup > 0 else 100
        perdida = 100 - pct_cosecha

        # Alerta por pérdida de cosecha significativa
        if perdida > 20 and sup > 10000:
            alerta_id += 1
            alertas.append({
                "id": alerta_id, "tipo": "estres_hidrico",
                "titulo": f"Pérdida de cosecha {perdida:.0f}% — {sup_cosechada:,.0f} de {sup:,.0f} ha sembradas",
                "zona": nombre, "provincia": provincia, "depto_id": gid,
                "nivel": "alto" if perdida > 30 else "medio", "score": 0,
                "accion": f"Pérdida significativa. Evaluar refinanciación y cobertura de seguros.",
                "producto_bp": "Refinanciación + Seguro agropecuario",
                "fecha": "2026-03-26", "estado": "nueva",
                "fuente": "MAGyP — ratio cosechada/sembrada",
            })

        # Retracción de superficie
        if variacion < -15 and sup > 10000:
            alerta_id += 1
            alertas.append({
                "id": alerta_id, "tipo": "cambio_productivo",
                "titulo": f"Retracción productiva: {variacion:.0f}% superficie vs. campaña anterior",
                "zona": nombre, "provincia": provincia, "depto_id": gid,
                "nivel": "alto", "score": 0,
                "accion": f"Caída de {abs(variacion):.0f}% en superficie. Evaluar refinanciación y capital de trabajo.",
                "producto_bp": "Capital de Trabajo PIV + Refinanciación",
                "fecha": "2026-03-26", "estado": "nueva",
                "fuente": "MAGyP — variación superficie",
            })
        elif variacion < -8 and sup > 20000:
            alerta_id += 1
            alertas.append({
                "id": alerta_id, "tipo": "cambio_productivo",
                "titulo": f"Reducción de superficie: {variacion:.0f}% vs. campaña anterior",
                "zona": nombre, "provincia": provincia, "depto_id": gid,
                "nivel": "medio", "score": 0,
                "accion": "Monitorear evolución. Posible necesidad de capital de trabajo.",
                "producto_bp": "Capital de Trabajo PAIV",
                "fecha": "2026-03-26", "estado": "nueva",
                "fuente": "MAGyP — variación superficie",
            })

        # Expansión — oportunidad comercial
        if variacion > 15 and sup > 15000:
            alerta_id += 1
            alertas.append({
                "id": alerta_id, "tipo": "oportunidad_inversion",
                "titulo": f"Expansión productiva: +{variacion:.0f}% superficie. Oportunidad de financiación.",
                "zona": nombre, "provincia": provincia, "depto_id": gid,
                "nivel": "medio", "score": 0,
                "accion": f"Zona en crecimiento. Ofrecer Préstamo Siembra + Procampo Digital USD.",
                "producto_bp": "Préstamo Siembra + Procampo Digital USD",
                "fecha": "2026-03-26", "estado": "nueva",
                "fuente": "MAGyP — variación superficie",
            })

        # Zona grande en expansión — oportunidad de seguros
        if sup > 100000 and variacion > 5:
            alerta_id += 1
            alertas.append({
                "id": alerta_id, "tipo": "zona_subasegurada",
                "titulo": f"Zona de {sup:,.0f} ha en expansión — evaluar cobertura",
                "zona": nombre, "provincia": provincia, "depto_id": gid,
                "nivel": "bajo", "score": 0,
                "accion": "Superficie significativa en crecimiento. Derivar a Provincia Seguros.",
                "producto_bp": "Seguro agropecuario (Provincia Seguros)",
                "fecha": "2026-03-26", "estado": "nueva",
                "fuente": "MAGyP — superficie total",
            })

    return alertas


def _todas_las_alertas():
    return _generar_alertas()


def get_alertas(tipo=None, provincia=None, nivel=None, estado=None):
    alertas = _todas_las_alertas()
    if tipo:
        alertas = [a for a in alertas if a["tipo"] == tipo]
    if provincia:
        alertas = [a for a in alertas if a.get("provincia") == provincia]
    if nivel:
        alertas = [a for a in alertas if a["nivel"] == nivel]
    if estado:
        alertas = [a for a in alertas if a.get("estado") == estado]
    return alertas


def get_alertas_recientes(n=5):
    return sorted(_todas_las_alertas(), key=lambda a: a["fecha"], reverse=True)[:n]


def get_alertas_por_zona(depto_id):
    return [a for a in _todas_las_alertas() if a.get("depto_id") == depto_id]


def get_alertas_nuevas():
    return get_alertas(estado="nueva")


def get_kpis_alertas():
    alertas = _todas_las_alertas()
    return {
        "total": len(alertas),
        "nuevas": sum(1 for a in alertas if a.get("estado") == "nueva"),
        "criticas": sum(1 for a in alertas if a.get("nivel") in ("alto", "critico")),
        "por_tipo": list(set(a["tipo"] for a in alertas)),
    }
