"""Radar Agro — Pipeline de procesamiento: import → enrich → classify → score."""

import re
import json
import uuid
import pandas as pd
from datetime import datetime

from services.radar_models import (
    insertar_prospectos, actualizar_prospecto, get_prospectos,
    get_pendientes_bcra, get_pendientes_bcra_por_partido,
    insertar_procampo, cruzar_procampo,
    log_importacion, get_db,
)
from services.bcra_client import consultar_batch, limpiar_cuit
from services.radar_scoring import calcular_score
from services.radar_classifier import clasificar


# --- Mapeo de actividades CLAE a cadena/subtipo ---
KEYWORDS_CADENA = {
    "agricola": ["cultivo", "soja", "trigo", "maiz", "girasol", "cereales", "oleaginosa", "semilla"],
    "ganadera": ["ganado", "bovino", "vacuno", "ovino", "porcino", "avicola", "cria", "engorde", "hacienda"],
    "lactea": ["leche", "lacteo", "tambo", "lecheria"],
    "agroindustrial": ["frigorifico", "molienda", "aceite", "harina", "alimento", "faena"],
    "mixta": ["agropecuario", "agro", "campo", "rural"],
}

KEYWORDS_SUBTIPO = {
    "cooperativa": ["cooperativa", "coop"],
    "acopio": ["acopio", "almacenaje", "silo", "elevador"],
    "exportador": ["exporta", "comercio exterior"],
    "frigorifico": ["frigorifico", "faena", "matadero"],
    "consignatario": ["consignatario", "remate", "feria"],
    "corredor": ["corredor", "intermediario"],
    "contratista": ["contratista", "laboreo", "cosecha"],
    "proveedor_insumos": ["insumo", "fertilizante", "agroquimico", "semillero"],
}


def _inferir_cadena(actividad: str) -> str:
    if not actividad:
        return ""
    act = actividad.lower()
    for cadena, keywords in KEYWORDS_CADENA.items():
        for kw in keywords:
            if kw in act:
                return cadena
    return ""


def _inferir_subtipo(actividad: str, tipo_societario: str = "") -> str:
    if not actividad:
        return "otro"
    act = actividad.lower()
    for subtipo, keywords in KEYWORDS_SUBTIPO.items():
        for kw in keywords:
            if kw in act:
                return subtipo
    # Inferencia por tipo societario
    if tipo_societario:
        ts = tipo_societario.upper()
        if "COOP" in ts:
            return "cooperativa"
    return "productor" if any(kw in act for kw in ["cultivo", "ganado", "agro", "campo"]) else "otro"


def importar_csv(archivo_bytes, nombre_archivo: str) -> dict:
    """Importa CSV o Excel de prospectos."""
    lote_id = str(uuid.uuid4())[:8]

    if nombre_archivo.endswith((".xlsx", ".xls")):
        df = pd.read_excel(archivo_bytes)
    else:
        df = pd.read_csv(archivo_bytes, dtype=str)

    # Normalizar columnas
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if "cuit" not in df.columns:
        return {"error": "El archivo no tiene columna 'cuit'", "total": 0, "nuevos": 0, "duplicados": 0}

    prospectos = []
    for _, row in df.iterrows():
        cuit = limpiar_cuit(str(row.get("cuit", "")))
        if len(cuit) != 11:
            continue

        actividad = str(row.get("actividad_fuente_base", row.get("actividad", row.get("actividad_descripcion", "")))).strip()
        tipo_soc = str(row.get("tipo_societario", "")).strip()

        prospectos.append({
            "cuit": cuit,
            "razon_social": str(row.get("razon_social", "")).strip(),
            "provincia": str(row.get("provincia", "Buenos Aires")).strip(),
            "partido": str(row.get("partido", row.get("dom_fiscal_localidad", ""))).strip(),
            "localidad": str(row.get("localidad", "")).strip(),
            "actividad_fuente_base": actividad,
            "fuente_origen": "csv",
            "tipo_societario": tipo_soc,
            "cadena_agro": _inferir_cadena(actividad),
            "subtipo_actor": _inferir_subtipo(actividad, tipo_soc),
            "lote_id": lote_id,
        })

    stats = insertar_prospectos(prospectos)
    log_importacion(lote_id, nombre_archivo, stats["total"], stats["nuevos"], stats["duplicados"])
    return stats


def importar_licitarg() -> dict:
    """Importa prospectos desde el parquet de LICITARG."""
    import os
    parquet_path = os.path.join(os.path.dirname(__file__), "..", "data", "licitarg", "agro-proveedores-estado.parquet")
    if not os.path.exists(parquet_path):
        return {"error": "Archivo LICITARG no encontrado", "total": 0, "nuevos": 0, "duplicados": 0}

    lote_id = f"licitarg_{datetime.now().strftime('%Y%m%d')}"
    df = pd.read_parquet(parquet_path)

    prospectos = []
    for _, row in df.iterrows():
        cuit = limpiar_cuit(str(row.get("cuit", "")))
        if len(cuit) != 11:
            continue

        actividad = str(row.get("actividad_descripcion", "")).strip()
        tipo_soc = str(row.get("tipo_societario", "")).strip()
        es_prov = int(row.get("es_proveedor_estado", 0))
        monto_adj = float(row.get("monto_total_adj", 0)) if pd.notna(row.get("monto_total_adj")) else 0

        tags = []
        if es_prov:
            tags.append("proveedor_estado")

        prospectos.append({
            "cuit": cuit,
            "razon_social": str(row.get("razon_social", "")).strip(),
            "provincia": "Buenos Aires",
            "partido": str(row.get("dom_fiscal_localidad", "")).strip(),
            "localidad": str(row.get("dom_fiscal_localidad", "")).strip(),
            "actividad_fuente_base": actividad,
            "fuente_origen": "licitarg",
            "tipo_societario": tipo_soc,
            "es_proveedor_estado": es_prov,
            "monto_adj_estado": monto_adj,
            "tags": json.dumps(tags, ensure_ascii=False),
            "cadena_agro": _inferir_cadena(actividad),
            "subtipo_actor": _inferir_subtipo(actividad, tipo_soc),
            "lote_id": lote_id,
        })

    stats = insertar_prospectos(prospectos)
    log_importacion(lote_id, "agro-proveedores-estado.parquet", stats["total"], stats["nuevos"], stats["duplicados"])
    return stats


def cargar_procampo(archivo_bytes) -> dict:
    """Carga lista de Procampo y cruza con prospectos."""
    df = pd.read_csv(archivo_bytes, dtype=str)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if "cuit" not in df.columns:
        return {"error": "El archivo no tiene columna 'cuit'"}

    registros = []
    for _, row in df.iterrows():
        cuit = limpiar_cuit(str(row.get("cuit", "")))
        if len(cuit) != 11:
            continue
        registros.append({
            "cuit": cuit,
            "razon_social": str(row.get("razon_social", "")).strip(),
            "tipo": str(row.get("tipo", "pesos")).strip(),
        })

    insertar_procampo(registros)
    cruzar_procampo()
    return {"total": len(registros)}


def _extraer_procampo_pdfs() -> list[dict]:
    """Extrae CUITs de los PDFs de Procampo en assets/."""
    import fitz
    import os

    assets_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
    pdfs = [
        ("Comercios_adheridos_Procampo_Digital.pdf", "pesos"),
        ("Comercios_adheridos_Procampo_Digital_dolares.pdf", "dolares"),
    ]

    registros = []
    for pdf_name, tipo in pdfs:
        path = os.path.join(assets_dir, pdf_name)
        if not os.path.exists(path):
            continue
        doc = fitz.open(path)
        for page in doc:
            tables = page.find_tables()
            for table in tables.tables:
                for row in table.extract():
                    if not row or len(row) < 2:
                        continue
                    nombre = (row[0] or "").strip()
                    cuit_raw = (row[1] or "").strip()
                    cuit = limpiar_cuit(cuit_raw)
                    if len(cuit) == 11 and nombre and "Establecimiento" not in nombre:
                        registros.append({
                            "cuit": cuit,
                            "razon_social": nombre,
                            "tipo": tipo,
                        })
    return registros


def sincronizar_procampo() -> dict:
    """Carga Procampo desde PDFs, cruza con prospectos, e inserta los que faltan como prospectos nuevos."""
    registros = _extraer_procampo_pdfs()
    if not registros:
        return {"total": 0, "nuevos_prospectos": 0, "cruzados": 0}

    # Guardar en tabla procampo
    insertar_procampo(registros)

    # Insertar como prospectos los que no existen todavía
    prospectos_nuevos = []
    for r in registros:
        prospectos_nuevos.append({
            "cuit": r["cuit"],
            "razon_social": r["razon_social"],
            "fuente_origen": "procampo",
            "provincia": "Buenos Aires",
            "cadena_agro": "agricola",
            "subtipo_actor": "comercio_procampo",
        })
    stats_insert = insertar_prospectos(prospectos_nuevos)

    # Cruzar todos
    cruzar_procampo()

    return {
        "total": len(registros),
        "nuevos_prospectos": stats_insert["nuevos"],
        "cruzados": stats_insert["nuevos"] + stats_insert["duplicados"],
    }


def ejecutar_bcra(progress_callback=None) -> dict:
    """Consulta BCRA para prospectos pendientes."""
    pendientes = get_pendientes_bcra()
    if not pendientes:
        return {"consultados": 0, "exitosos": 0, "errores": 0}

    resultados = consultar_batch(pendientes, progress_callback=progress_callback)
    ahora = datetime.now().isoformat()

    exitosos = 0
    errores = 0
    for cuit, data in resultados.items():
        if data.get("bcra_situacion", -1) != -1:
            campos = {k: v for k, v in data.items() if k.startswith("bcra_")}
            campos["fecha_bcra"] = ahora
            actualizar_prospecto(cuit, campos)
            exitosos += 1
        else:
            errores += 1

    return {"consultados": len(pendientes), "exitosos": exitosos, "errores": errores}


def ejecutar_bcra_por_partido(partidos: list[str], progress_callback=None) -> dict:
    """Consulta BCRA solo para prospectos pendientes de los partidos indicados."""
    pendientes = get_pendientes_bcra_por_partido(partidos)
    if not pendientes:
        return {"consultados": 0, "exitosos": 0, "errores": 0}

    resultados = consultar_batch(pendientes, progress_callback=progress_callback)
    ahora = datetime.now().isoformat()

    exitosos = 0
    errores = 0
    for cuit, data in resultados.items():
        if data.get("bcra_situacion", -1) != -1:
            campos = {k: v for k, v in data.items() if k.startswith("bcra_")}
            campos["fecha_bcra"] = ahora
            actualizar_prospecto(cuit, campos)
            exitosos += 1
        else:
            errores += 1

    return {"consultados": len(pendientes), "exitosos": exitosos, "errores": errores}


def clasificar_todos():
    """Ejecuta clasificación + scoring en todos los prospectos."""
    prospectos = get_prospectos()
    ahora = datetime.now().isoformat()

    for p in prospectos:
        # Scoring primero
        scores = calcular_score(p)
        p.update(scores)

        # Clasificación (usa score)
        clasif = clasificar(p)

        # Actualizar en DB
        campos = {**scores, **clasif, "fecha_clasificacion": ahora}
        actualizar_prospecto(p["cuit"], campos)


def pipeline_completo(archivo_bytes=None, nombre_archivo=None,
                      procampo_bytes=None, usar_licitarg=False,
                      progress_callback=None) -> dict:
    """Ejecuta pipeline completo."""
    resultado = {"pasos": []}

    # Paso 1: Importar
    if usar_licitarg:
        stats = importar_licitarg()
        resultado["pasos"].append({"paso": "Importar LICITARG", **stats})
    elif archivo_bytes and nombre_archivo:
        stats = importar_csv(archivo_bytes, nombre_archivo)
        resultado["pasos"].append({"paso": "Importar CSV", **stats})

    # Paso 2: Procampo
    if procampo_bytes:
        stats = cargar_procampo(procampo_bytes)
        resultado["pasos"].append({"paso": "Cargar Procampo", **stats})
    else:
        cruzar_procampo()

    # Paso 3: BCRA
    if progress_callback:
        stats = ejecutar_bcra(progress_callback=progress_callback)
    else:
        stats = ejecutar_bcra()
    resultado["pasos"].append({"paso": "Consultar BCRA", **stats})

    # Paso 4: Clasificar + Scorear
    clasificar_todos()
    resultado["pasos"].append({"paso": "Clasificar y Scorear", "ok": True})

    return resultado
