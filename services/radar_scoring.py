"""Radar Agro — Motor de scoring comercial con 4 componentes explicables."""


PESOS = {
    "perfil_sectorial": 0.20,
    "oportunidad_financiera": 0.35,
    "relevancia_comercial": 0.25,
    "calidad_datos": 0.20,
}

SUBTIPO_SCORES = {
    "cooperativa": 90, "acopio": 85, "exportador": 85,
    "frigorifico": 80, "consignatario": 75, "corredor": 70,
    "productor": 65, "contratista": 50, "proveedor_insumos": 55,
    "otro": 30,
}

CADENA_AJUSTE = {
    "mixta": 10, "agricola": 5, "ganadera": 5,
    "lactea": 5, "agroindustrial": 5,
}


def _score_perfil_sectorial(p: dict) -> tuple[float, str]:
    subtipo = p.get("subtipo_actor", "otro")
    base = SUBTIPO_SCORES.get(subtipo, 30)

    cadena = p.get("cadena_agro", "")
    ajuste_cadena = CADENA_AJUSTE.get(cadena, -15 if not cadena else 0)

    import json
    tags = p.get("tags", "[]")
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []
    bonus_tags = min(len(tags) * 5, 15)

    score = min(base + ajuste_cadena + bonus_tags, 100)
    score = max(score, 0)

    motivo = f"Perfil: {subtipo}"
    if cadena:
        motivo += f", cadena {cadena}"
    return score, motivo


def _score_oportunidad_financiera(p: dict) -> tuple[float, str]:
    sit = p.get("bcra_situacion", -1)
    es_cliente = p.get("es_cliente_bp", 0)
    hay_exp = p.get("bcra_hay_exposicion", 0)
    conc_alta = p.get("bcra_concentracion_alta", 0)
    diversificada = p.get("bcra_exposicion_diversificada", 0)
    monto = p.get("bcra_monto_total", 0)

    # Sin datos BCRA
    if sit == -1:
        return 50, "Sin consulta BCRA realizada"

    # Casos base
    if es_cliente and not hay_exp:
        base, motivo = 90, "Cliente BP con exposición baja — oportunidad de cross-sell"
    elif not es_cliente and not hay_exp:
        base, motivo = 85, "Sin exposición bancaria relevante — terreno limpio"
    elif not es_cliente and conc_alta and sit <= 2:
        entidad = p.get("bcra_entidad_principal", "otra entidad")
        pct = p.get("bcra_pct_entidad_principal", 0)
        base, motivo = 80, f"Concentración en {entidad} ({pct:.0f}%) — oportunidad de captación"
    elif not es_cliente and diversificada and sit <= 2:
        base, motivo = 70, "Exposición diversificada — oportunidad de ganar share"
    elif es_cliente and hay_exp:
        base, motivo = 60, "Cliente BP con exposición activa — profundizar relación"
    elif sit == 0:
        base, motivo = 80, "Sin deudas registradas en BCRA"
    else:
        base, motivo = 55, "Con exposición detectada"

    # Penalizaciones
    penalizacion = 0
    if sit == 3:
        penalizacion += 25
        motivo += ". Situación 3 (con problemas)"
    elif sit >= 4:
        penalizacion += 40
        motivo += f". Situación {sit} — riesgo crediticio"

    if p.get("bcra_tiene_refinanciaciones", 0):
        penalizacion += 15

    if p.get("bcra_cheques_pendientes", 0) > 0:
        penalizacion += 20
        motivo += ". Cheques rechazados pendientes"

    if p.get("bcra_evolucion") == "empeorando":
        penalizacion += 10
        motivo += ". Evolución empeorando"

    score = max(base - penalizacion, 0)
    return min(score, 100), motivo


def _score_relevancia_comercial(p: dict) -> tuple[float, str]:
    subtipo = p.get("subtipo_actor", "otro")
    es_cliente = p.get("es_cliente_bp", 0)
    monto = p.get("bcra_monto_total", 0)
    es_prov_estado = p.get("es_proveedor_estado", 0)
    monto_adj = p.get("monto_adj_estado", 0)
    tipo_soc = p.get("tipo_societario", "")

    # Base por subtipo
    corporativos = {"cooperativa", "acopio", "exportador", "frigorifico"}
    intermediarios = {"corredor", "consignatario"}

    if subtipo in corporativos:
        base, motivo = 85, f"Actor corporativo ({subtipo}) — alto potencial de volumen"
    elif subtipo in intermediarios:
        base, motivo = 70, f"Intermediario ({subtipo}) — maneja volumen de terceros"
    elif subtipo == "productor":
        base, motivo = 50, "Productor — relevancia estándar"
    else:
        base, motivo = 30, "Sin tipificación clara"

    bonus = 0
    if es_cliente:
        bonus += 15
    if monto > 50000:  # > 50M en miles
        bonus += 10
    elif monto > 10000:  # > 10M
        bonus += 5

    # Señales LICITARG
    if es_prov_estado:
        bonus += 10
        motivo += ". Proveedor del estado (formalizado)"
    if monto_adj > 10_000_000:
        bonus += 5
    if tipo_soc and tipo_soc.upper() in ("SA", "S.A.", "S.A"):
        bonus += 5

    # Señal territorial cruzada
    bonus_territorial = _bonus_zona_caliente(p)
    if bonus_territorial > 0:
        bonus += bonus_territorial

    score = min(base + bonus, 100)
    return score, motivo


def _bonus_zona_caliente(p: dict) -> int:
    """Si el prospecto está en una zona de alto score territorial, bonus."""
    partido = p.get("partido", "")
    if not partido:
        return 0
    try:
        from services.scoring import get_all_scores
        scores = get_all_scores()
        for s in scores:
            nombre = s.get("nombre", "").upper()
            if partido.upper() in nombre or nombre in partido.upper():
                if s.get("score", 0) >= 70:
                    return 10
        return 0
    except Exception:
        return 0


def _score_calidad_datos(p: dict) -> tuple[float, str]:
    score = 0
    factores = []

    if p.get("razon_social"):
        score += 15
    else:
        factores.append("sin razón social")

    if p.get("bcra_situacion", -1) != -1:
        score += 25
    else:
        factores.append("sin consulta BCRA")

    if p.get("subtipo_actor", "otro") != "otro":
        score += 15
    else:
        factores.append("sin tipificación")

    if p.get("cadena_agro"):
        score += 10

    import json
    tags = p.get("tags", "[]")
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []
    if tags:
        score += 10

    if p.get("es_cliente_bp"):
        score += 10

    if p.get("partido") or p.get("localidad"):
        score += 10
    else:
        factores.append("sin ubicación")

    cuit = p.get("cuit", "")
    if len(cuit) == 11 and cuit.isdigit():
        score += 5

    if p.get("fuente_origen") == "licitarg":
        score += 5

    motivo = "Datos completos" if score >= 80 else f"Datos parciales ({', '.join(factores[:2])})" if factores else "Datos razonables"
    return min(score, 100), motivo


def calcular_score(prospecto: dict) -> dict:
    """Calcula score total con 4 componentes. Retorna dict con scores y motivos."""
    s1, m1 = _score_perfil_sectorial(prospecto)
    s2, m2 = _score_oportunidad_financiera(prospecto)
    s3, m3 = _score_relevancia_comercial(prospecto)
    s4, m4 = _score_calidad_datos(prospecto)

    total = round(
        s1 * PESOS["perfil_sectorial"] +
        s2 * PESOS["oportunidad_financiera"] +
        s3 * PESOS["relevancia_comercial"] +
        s4 * PESOS["calidad_datos"]
    )

    # Motivo: los 2 componentes de mayor peso * score
    componentes = [
        (s2 * PESOS["oportunidad_financiera"], m2),
        (s3 * PESOS["relevancia_comercial"], m3),
        (s1 * PESOS["perfil_sectorial"], m1),
        (s4 * PESOS["calidad_datos"], m4),
    ]
    componentes.sort(key=lambda x: x[0], reverse=True)
    motivo = ". ".join([c[1] for c in componentes[:2]])

    return {
        "score_total": total,
        "score_perfil_sectorial": round(s1, 1),
        "score_oportunidad_financiera": round(s2, 1),
        "score_relevancia_comercial": round(s3, 1),
        "score_calidad_datos": round(s4, 1),
        "score_motivo": motivo,
    }
