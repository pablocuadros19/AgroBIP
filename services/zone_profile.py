"""Perfiles productivos por zona — generados desde datos reales MAGyP + SENASA."""

from services.magyp_loader import get_produccion_depto, get_tendencia_depto, get_variacion_superficie
from services.senasa_loader import get_bovinos_depto
from services.precios import calcular_vbp

# Tamaño promedio de explotación por provincia (ha)
TAMANO_PROMEDIO_HA = {
    "Buenos Aires": 500,
    "Córdoba": 400,
    "Santa Fe": 350,
    "Entre Ríos": 300,
    "La Pampa": 800,
}

# Mapeo señal → producto BP sugerido (datos reales del PDF A5388)
PRODUCTOS_BP = {
    "siembra": {
        "nombre": "Préstamo con destino a Siembra",
        "detalle": "Financiación para labores de siembra, protección y fertilización. Trigo, cebada, maíz, girasol, soja, papa.",
        "condicion": "TNA 37% fija · Pago íntegro al vencimiento · Sola firma",
    },
    "lecheria_inversion": {
        "nombre": "Préstamos Lechería — Inversión",
        "detalle": "Construcción e instalaciones, compra de maquinarias, retención de vientres, pasturas.",
        "condicion": "Hasta $5.000.000 · Tasa variable TAMAR · Hasta 48 meses",
    },
    "lecheria_ct": {
        "nombre": "Préstamos Lechería — Capital de Trabajo",
        "detalle": "Alimentación, sanidad, capital de trabajo industrias lácteas.",
        "condicion": "Hasta $5.000.000 · Tasa variable TAMAR · Hasta 36 meses",
    },
    "ganados_inversion": {
        "nombre": "Préstamos Ganados y Carnes — Inversión",
        "detalle": "Instalaciones, maquinarias, mejoramiento genético, pasturas, retención de vientres.",
        "condicion": "Tasa variable TAMAR · Hasta 48 meses · A satisfacción del banco",
    },
    "ganados_ct": {
        "nombre": "Préstamos Ganados y Carnes — Capital de Trabajo",
        "detalle": "Incremento y/o recomposición de capital de trabajo ganadero.",
        "condicion": "Tasa variable TAMAR · Hasta 24 meses",
    },
    "cap_trabajo_piv": {
        "nombre": "Capital de Trabajo — PIV",
        "detalle": "Para productores agropecuarios y empresas del sector agroindustrial.",
        "condicion": "Hasta 180 días · Pago íntegro al vencimiento",
    },
    "cap_trabajo_paiv": {
        "nombre": "Capital de Trabajo — PAIV",
        "detalle": "Para productores agropecuarios y empresas del sector agroindustrial.",
        "condicion": "Hasta 12 meses · Pago amortizable a interés vencido",
    },
    "procampo_pesos": {
        "nombre": "Procampo Digital — Pesos",
        "detalle": "Financiación digital para adquisición de insumos, bienes y servicios agroindustriales.",
        "condicion": "TNA desde 25% fija · Hasta 360 días · 100% digital via BIP",
    },
    "procampo_usd": {
        "nombre": "Procampo Digital — Dólares (NUEVO)",
        "detalle": "Financiación en USD para insumos, bienes y servicios. Lanzado marzo 2026 con foco en Expoagro.",
        "condicion": "TNA desde 0% USD (promo Expoagro) · Hasta 360 días · 100% digital via BIP",
    },
    "refinanciacion_emergencia": {
        "nombre": "Refinanciación por Emergencia Agropecuaria",
        "detalle": "Prórroga y refinanciación para productores declarados en emergencia y/o desastre.",
        "condicion": "Tasa bonificada BADLAR 80% RO · Hasta 270 días",
    },
    "seguro_agro": {
        "nombre": "Seguro Agropecuario",
        "detalle": "Cobertura para cultivos y ganado. Derivar a Provincia Seguros.",
        "condicion": "Consultar condiciones con área de seguros",
    },
}


def get_perfil(depto_id: str) -> dict:
    """Genera perfil productivo desde datos reales para cualquier departamento."""
    prod = get_produccion_depto(depto_id)
    bovinos = get_bovinos_depto(depto_id)
    tendencia = get_tendencia_depto(depto_id, n=5)
    variacion = get_variacion_superficie(depto_id)

    if not prod and not bovinos:
        return None

    # Datos base
    nombre = prod.get("departamento", bovinos.get("departamento", "—")) if prod else bovinos.get("departamento", "—")
    provincia = prod.get("provincia", bovinos.get("provincia", "—")) if prod else bovinos.get("provincia", "—")
    campania = prod.get("campania", "—") if prod else "—"

    sup_total = prod.get("superficie_total_ha", 0) if prod else 0
    prod_total = prod.get("produccion_total_tm", 0) if prod else 0
    cultivo_principal = prod.get("cultivo_principal", "—") if prod else "—"
    total_cabezas = bovinos.get("total_cabezas", 0) if bovinos else 0

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
        tipo_zona = "ganadera" if total_cabezas > 0 else "sin datos"

    # Estimar productores
    tamano_prom = TAMANO_PROMEDIO_HA.get(provincia, 500)
    productores_est = max(1, round(sup_total / tamano_prom)) if sup_total > 0 else 0

    # VBP
    vbp_data = calcular_vbp(prod) if prod else {"vbp_total_usd": 0, "vbp_total_ars": 0, "vbp_por_cultivo": {}}

    # Cultivos para tabla
    cultivos_lista = []
    if prod and prod.get("cultivos"):
        for cult_nombre, cult_datos in prod["cultivos"].items():
            sup = cult_datos["superficie_sembrada_ha"]
            pct = round(sup / sup_total * 100, 1) if sup_total > 0 else 0
            vbp_cult = vbp_data["vbp_por_cultivo"].get(cult_nombre, {})
            cultivos_lista.append({
                "nombre": cult_nombre.capitalize(),
                "superficie_ha": round(sup),
                "produccion_tm": round(cult_datos["produccion_tm"]),
                "rendimiento_kgxha": round(cult_datos["rendimiento_kgxha"]),
                "pct_superficie": pct,
                "vbp_usd": round(vbp_cult.get("vbp_usd", 0)),
            })
        cultivos_lista.sort(key=lambda x: x["superficie_ha"], reverse=True)

    # Generar ficha automática
    ficha = _generar_ficha(
        nombre, provincia, tipo_zona, cultivo_principal, sup_total,
        prod_total, productores_est, vbp_data["vbp_total_usd"],
        variacion, total_cabezas, depto_id
    )

    return {
        "nombre": nombre,
        "provincia": provincia,
        "tipo_zona": tipo_zona,
        "campania": campania,
        "superficie_total_ha": round(sup_total),
        "produccion_total_tm": round(prod_total),
        "cultivo_principal": cultivo_principal,
        "cultivos": cultivos_lista,
        "total_cabezas": total_cabezas,
        "productores_estimados": productores_est,
        "vbp_total_usd": round(vbp_data["vbp_total_usd"]),
        "vbp_total_ars": round(vbp_data["vbp_total_ars"]),
        "vbp_por_cultivo": vbp_data["vbp_por_cultivo"],
        "variacion_superficie_pct": round(variacion, 1),
        "tendencia": tendencia,
        "bovinos": bovinos.get("categorias", {}) if bovinos else {},
        "emergencia_activa": depto_id in _EMERGENCIAS,
        "ficha": ficha,
        "fuentes": {
            "produccion": f"MAGyP — Estimaciones Agrícolas, campaña {campania}",
            "ganaderia": f"SENASA — Existencias bovinas, {bovinos.get('anio', '—')}" if bovinos else None,
            "precios": f"Precios de referencia, {vbp_data.get('fecha_precios', '—')}",
        },
    }


_EMERGENCIAS = {
    "06189": "Sequía prolongada — decreto 2026",
    "06455": "Emergencia vigente desde enero 2026",
}


def _generar_ficha(nombre, provincia, tipo_zona, cultivo_principal, sup_total,
                   prod_total, productores_est, vbp_usd, variacion, total_cabezas, depto_id):
    """Genera las 4 respuestas de la ficha automáticamente."""

    tiene_emergencia = depto_id in _EMERGENCIAS
    vbp_mm = vbp_usd / 1_000_000 if vbp_usd else 0

    # ¿Qué pasa?
    if tiene_emergencia:
        que_pasa = (
            f"Emergencia agropecuaria declarada en {nombre}. "
            f"Zona {tipo_zona} con {sup_total:,.0f} ha sembradas y ~{productores_est} productores estimados. "
            f"Cultivo principal: {cultivo_principal}."
        )
    elif variacion < -10:
        que_pasa = (
            f"Retracción productiva en {nombre}: la superficie sembrada cayó {abs(variacion):.1f}% vs. campaña anterior. "
            f"{sup_total:,.0f} ha sembradas, producción de {prod_total:,.0f} tn. "
            f"Cultivo principal: {cultivo_principal}."
        )
    elif variacion > 10:
        que_pasa = (
            f"Expansión productiva en {nombre}: superficie sembrada creció {variacion:.1f}% vs. campaña anterior. "
            f"{sup_total:,.0f} ha, {prod_total:,.0f} tn. {cultivo_principal} lidera."
        )
    else:
        que_pasa = (
            f"Zona {tipo_zona} con {sup_total:,.0f} ha sembradas. "
            f"Producción: {prod_total:,.0f} tn. Cultivo principal: {cultivo_principal}. "
            f"~{productores_est} productores estimados."
        )
        if total_cabezas > 0:
            que_pasa += f" Stock ganadero: {total_cabezas:,} cabezas."

    # ¿Por qué importa?
    por_que = f"VBP estimado: USD {vbp_mm:,.1f} M. "
    if productores_est > 500:
        por_que += f"Zona con alta densidad de productores (~{productores_est}). "
    if vbp_mm > 50:
        por_que += "Alto impacto en la economía regional. Oportunidad comercial significativa para BP."
    elif vbp_mm > 10:
        por_que += "Zona con potencial de colocación de productos agro BP."
    else:
        por_que += "Zona de menor escala — evaluar oportunidades puntuales."

    # ¿Qué producto?
    if tiene_emergencia:
        que_producto = "Refinanciación emergencia (tasa bonificada BADLAR 80% RO). Capital de trabajo de emergencia. Evaluar prórroga de vencimientos."
    elif tipo_zona == "ganadera":
        que_producto = "Préstamos Ganados y Carnes (inversión y cap. trabajo). Si hay expansión: financiación de retención de vientres."
    elif tipo_zona == "agricola":
        que_producto = f"Préstamo Siembra para campaña fina. Procampo Digital (pesos y USD) para insumos. "
        if vbp_mm > 30:
            que_producto += "Procampo Digital USD para productores de mayor escala."
    else:
        que_producto = "Capital de Trabajo PIV/PAIV. Evaluar perfil para Procampo Digital."

    # ¿Qué prioridad?
    if tiene_emergencia:
        que_prioridad = "ACCIÓN INMEDIATA. Contactar sucursal de la zona. Activar protocolo de emergencia."
    elif variacion < -10:
        que_prioridad = "Acción esta semana. Zona en retracción — necesitan capital de trabajo y posiblemente refinanciación."
    elif vbp_mm > 50:
        que_prioridad = "Acción este mes. Zona de alto valor — oportunidad de colocación de múltiples productos."
    elif variacion > 10:
        que_prioridad = "Acción este mes. Zona en crecimiento — oportunidad ofensiva."
    else:
        que_prioridad = "Monitorear. Revisar en próximo ciclo de scoring."

    return {
        "que_pasa": que_pasa,
        "por_que_importa": por_que,
        "que_producto": que_producto,
        "que_prioridad": que_prioridad,
    }


def sugerir_productos(depto_id, score_data=None):
    """Sugiere productos BP según perfil de zona y señales activas."""
    perfil = get_perfil(depto_id)
    productos = []

    tipo = perfil.get("tipo_zona", "") if perfil else ""
    emergencia = perfil.get("emergencia_activa", False) if perfil else False
    variacion = perfil.get("variacion_superficie_pct", 0) if perfil else 0
    vbp_usd = perfil.get("vbp_total_usd", 0) if perfil else 0
    score = score_data.get("score", 0) if score_data else 0

    # Emergencia → refinanciación
    if emergencia:
        productos.append(PRODUCTOS_BP["refinanciacion_emergencia"])

    # Retracción → capital de trabajo defensivo
    if variacion < -5:
        productos.append(PRODUCTOS_BP["cap_trabajo_piv"])

    # Zona agrícola → siembra + procampo
    if tipo == "agricola":
        productos.append(PRODUCTOS_BP["siembra"])
        productos.append(PRODUCTOS_BP["procampo_pesos"])

    # Zona ganadera → ganados y carnes
    if tipo == "ganadera":
        productos.append(PRODUCTOS_BP["ganados_inversion"])
        productos.append(PRODUCTOS_BP["ganados_ct"])

    # Zona mixta
    if tipo == "mixta":
        productos.append(PRODUCTOS_BP["cap_trabajo_paiv"])
        productos.append(PRODUCTOS_BP["siembra"])

    # Alto VBP + score alto → Procampo USD (producto estrella nuevo)
    if vbp_usd > 20_000_000 and score >= 60:
        productos.append(PRODUCTOS_BP["procampo_usd"])

    # Expansión → financiar inversión
    if variacion > 10:
        productos.append(PRODUCTOS_BP["procampo_usd"])

    # Default
    if not productos:
        productos.append(PRODUCTOS_BP["cap_trabajo_piv"])

    # Dedup
    seen = set()
    unique = []
    for p in productos:
        if p["nombre"] not in seen:
            seen.add(p["nombre"])
            unique.append(p)

    return unique[:4]
