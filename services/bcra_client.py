"""Cliente BCRA Central de Deudores + Cheques — adaptado de PRUEBA 101."""

import httpx
import re
import json
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

BCRA_TOKEN = os.getenv("BCRA_TOKEN", "")
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}
if BCRA_TOKEN:
    HEADERS["Authorization"] = f"BEARER {BCRA_TOKEN}"

SITUACION_TEXTOS = {
    0: "Sin deudas registradas",
    1: "Normal",
    2: "Con seguimiento especial",
    3: "Con problemas",
    4: "Alto riesgo de insolvencia",
    5: "Irrecuperable",
    6: "Irrecuperable por disposición técnica",
}

CACHE_MAX_DIAS = 30
RATE_LIMIT_DELAY = 2.0
DELAY_ENTRE_ENDPOINTS = 1.0


def _hacer_request(url: str, max_reintentos: int = 3) -> httpx.Response | None:
    for intento in range(max_reintentos + 1):
        try:
            with httpx.Client(verify=False, timeout=15) as client:
                r = client.get(url, headers=HEADERS)
                if r.status_code == 429:
                    espera = 5 * (intento + 1)
                    time.sleep(espera)
                    continue
                return r
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError):
            if intento < max_reintentos:
                time.sleep(3 * (intento + 1))
                continue
    return None


def consultar_deudas(cuit: str) -> dict:
    """Consulta Central de Deudores. Captura últimos 6 períodos."""
    url = f"https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuit}"
    r = _hacer_request(url)

    if r is None:
        return {"bcra_situacion": -1, "bcra_situacion_texto": "Error conexión"}

    if r.status_code == 404:
        return {
            "bcra_situacion": 0,
            "bcra_situacion_texto": "Sin deudas registradas",
            "bcra_monto_total": 0,
            "bcra_cantidad_entidades": 0,
            "bcra_detalle": [],
            "bcra_periodos": [],
            "bcra_evolucion": "sin_historial",
        }

    if r.status_code != 200:
        return {"bcra_situacion": -1, "bcra_situacion_texto": f"Error HTTP {r.status_code}"}

    try:
        data = r.json()
    except Exception:
        return {"bcra_situacion": -1, "bcra_situacion_texto": "Error parseando JSON"}

    periodos = data.get("results", {}).get("periodos", [])
    if not periodos:
        return {
            "bcra_situacion": 0,
            "bcra_situacion_texto": "Sin deudas registradas",
            "bcra_monto_total": 0,
            "bcra_cantidad_entidades": 0,
            "bcra_detalle": [],
            "bcra_periodos": [],
            "bcra_evolucion": "sin_historial",
        }

    periodos_detalle = []
    for periodo in periodos[:6]:
        entidades = periodo.get("entidades", [])
        periodo_info = {
            "periodo": periodo.get("periodo", ""),
            "entidades": [],
            "peor_situacion": 0,
            "monto_total": 0,
        }
        for e in entidades:
            periodo_info["entidades"].append({
                "entidad": e.get("entidad", ""),
                "situacion": e.get("situacion", 0),
                "monto": e.get("monto", 0),
                "dias_atraso": e.get("diasAtrasoPago", 0),
                "refinanciaciones": e.get("refinanciaciones", False),
                "situacion_juridica": e.get("situacionJuridica", False),
            })
        if periodo_info["entidades"]:
            periodo_info["peor_situacion"] = max(e["situacion"] for e in periodo_info["entidades"])
            periodo_info["monto_total"] = sum(e["monto"] for e in periodo_info["entidades"])
        periodos_detalle.append(periodo_info)

    ultimo = periodos_detalle[0]
    peor_situacion = ultimo["peor_situacion"]
    monto_total = ultimo["monto_total"]

    # Evolución
    evolucion = "sin_historial"
    if len(periodos_detalle) >= 2:
        sit_actual = periodos_detalle[0]["peor_situacion"]
        sit_anterior = periodos_detalle[1]["peor_situacion"]
        if sit_actual < sit_anterior:
            evolucion = "mejorando"
        elif sit_actual > sit_anterior:
            evolucion = "empeorando"
        else:
            evolucion = "estable"

    return {
        "bcra_situacion": peor_situacion,
        "bcra_situacion_texto": SITUACION_TEXTOS.get(peor_situacion, "Desconocida"),
        "bcra_monto_total": monto_total,
        "bcra_cantidad_entidades": len(ultimo["entidades"]),
        "bcra_detalle": ultimo["entidades"],
        "bcra_periodos": periodos_detalle,
        "bcra_evolucion": evolucion,
    }


def consultar_cheques(cuit: str) -> dict:
    """Consulta cheques rechazados."""
    url = f"https://api.bcra.gob.ar/centraldedeudores/v1.0/Cheques/{cuit}"
    r = _hacer_request(url)

    if r is None:
        return {"bcra_cheques_rechazados": 0, "bcra_cheques_pendientes": 0}
    if r.status_code in (404, 204):
        return {"bcra_cheques_rechazados": 0, "bcra_cheques_pendientes": 0}
    if r.status_code != 200:
        return {"bcra_cheques_rechazados": 0, "bcra_cheques_pendientes": 0}

    try:
        data = r.json()
    except Exception:
        return {"bcra_cheques_rechazados": 0, "bcra_cheques_pendientes": 0}

    resultados = data.get("results", {})
    cheques_raw = resultados.get("cheques", [])
    causales = resultados.get("causales", [])

    if not cheques_raw and causales:
        total = sum(c.get("cantidad", 0) for c in causales)
        return {"bcra_cheques_rechazados": total, "bcra_cheques_pendientes": total}

    total = len(cheques_raw)
    rehabilitados = sum(1 for ch in cheques_raw if ch.get("fechaPago"))
    pendientes = total - rehabilitados

    return {
        "bcra_cheques_rechazados": total,
        "bcra_cheques_pendientes": pendientes,
    }


def _calcular_metricas_derivadas(deudas: dict, cheques: dict) -> dict:
    """Calcula métricas derivadas a partir de respuesta BCRA."""
    monto_total = deudas.get("bcra_monto_total", 0)
    entidades = deudas.get("bcra_detalle", [])
    cantidad_entidades = len(entidades)

    # Entidad principal y concentración
    entidad_principal = ""
    pct_principal = 0
    if entidades and monto_total > 0:
        principal = max(entidades, key=lambda e: e.get("monto", 0))
        entidad_principal = principal.get("entidad", "")
        pct_principal = round(principal.get("monto", 0) / monto_total * 100, 1) if monto_total > 0 else 0

    # Umbrales (montos en miles de pesos según API BCRA)
    hay_exposicion = 1 if monto_total > 1000 else 0  # > 1M pesos
    concentracion_alta = 1 if pct_principal > 60 and cantidad_entidades > 0 else 0
    diversificada = 1 if cantidad_entidades >= 3 and pct_principal < 40 else 0

    tiene_refinanciaciones = 0
    if entidades:
        tiene_refinanciaciones = 1 if any(e.get("refinanciaciones") for e in entidades) else 0

    # Deuda con Banco Provincia
    deuda_bapro = any(
        "PROVINCIA" in e.get("entidad", "").upper()
        for e in entidades
    )

    return {
        "bcra_situacion": deudas.get("bcra_situacion", -1),
        "bcra_situacion_texto": deudas.get("bcra_situacion_texto", ""),
        "bcra_monto_total": monto_total,
        "bcra_cantidad_entidades": cantidad_entidades,
        "bcra_entidad_principal": entidad_principal,
        "bcra_pct_entidad_principal": pct_principal,
        "bcra_situacion_maxima": deudas.get("bcra_situacion", 0),
        "bcra_hay_exposicion": hay_exposicion,
        "bcra_concentracion_alta": concentracion_alta,
        "bcra_exposicion_diversificada": diversificada,
        "bcra_tiene_refinanciaciones": tiene_refinanciaciones,
        "bcra_cheques_rechazados": cheques.get("bcra_cheques_rechazados", 0),
        "bcra_cheques_pendientes": cheques.get("bcra_cheques_pendientes", 0),
        "bcra_evolucion": deudas.get("bcra_evolucion", "sin_historial"),
        "bcra_ultimo_periodo": deudas.get("bcra_periodos", [{}])[0].get("periodo", "") if deudas.get("bcra_periodos") else "",
        "bcra_detalle": json.dumps(deudas.get("bcra_periodos", []), ensure_ascii=False),
        "bcra_deuda_bapro": deuda_bapro,
    }


def _cache_get(cuit: str) -> dict | None:
    """Busca en cache SQLite."""
    from services.radar_models import get_db
    db = get_db()
    row = db.execute(
        "SELECT response_json, fecha_consulta, exito FROM bcra_cache WHERE cuit = ?", (cuit,)
    ).fetchone()
    if row is None:
        return None
    fecha = row["fecha_consulta"]
    limite = (datetime.now() - timedelta(days=CACHE_MAX_DIAS)).isoformat()
    if fecha < limite:
        return None
    if not row["exito"]:
        return None
    try:
        return json.loads(row["response_json"])
    except Exception:
        return None


def _cache_set(cuit: str, data: dict, exito: bool):
    from services.radar_models import get_db
    db = get_db()
    db.execute("""
        INSERT OR REPLACE INTO bcra_cache (cuit, response_json, fecha_consulta, exito)
        VALUES (?, ?, ?, ?)
    """, (cuit, json.dumps(data, ensure_ascii=False), datetime.now().isoformat(), int(exito)))
    db.commit()


def consultar_cuit_completo(cuit: str) -> dict:
    """Consulta BCRA completa (deudas + cheques) con cache."""
    cuit_limpio = re.sub(r"[^0-9]", "", cuit)
    if len(cuit_limpio) != 11:
        return {"bcra_situacion": -1, "bcra_situacion_texto": "CUIT inválido"}

    cached = _cache_get(cuit_limpio)
    if cached:
        return cached

    deudas = consultar_deudas(cuit_limpio)
    time.sleep(DELAY_ENTRE_ENDPOINTS)
    cheques = consultar_cheques(cuit_limpio)

    if deudas.get("bcra_situacion", -1) == -1:
        _cache_set(cuit_limpio, deudas, exito=False)
        return deudas

    metricas = _calcular_metricas_derivadas(deudas, cheques)
    _cache_set(cuit_limpio, metricas, exito=True)
    return metricas


def consultar_batch(cuits: list[str], progress_callback=None) -> dict:
    """Consulta lote de CUITs con rate limiting y progress callback."""
    resultados = {}
    total = len(cuits)

    for i, cuit in enumerate(cuits):
        cuit_limpio = re.sub(r"[^0-9]", "", cuit)
        if len(cuit_limpio) != 11:
            resultados[cuit] = {"bcra_situacion": -1, "bcra_situacion_texto": "CUIT inválido"}
            if progress_callback:
                progress_callback(i + 1, total, cuit, False)
            continue

        resultado = consultar_cuit_completo(cuit_limpio)
        resultados[cuit_limpio] = resultado
        exito = resultado.get("bcra_situacion", -1) != -1

        if progress_callback:
            progress_callback(i + 1, total, cuit, exito)

        # Rate limiting entre CUITs
        if i < total - 1:
            time.sleep(RATE_LIMIT_DELAY)

    return resultados


def limpiar_cuit(cuit: str) -> str:
    """Normaliza CUIT: quita guiones, espacios, valida 11 dígitos."""
    return re.sub(r"[^0-9]", "", str(cuit).strip())
