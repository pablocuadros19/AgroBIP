"""Radar Agro — Clasificador comercial con reglas transparentes + semáforo."""

import json

CORPORATIVOS = {"cooperativa", "acopio", "exportador", "frigorifico", "consignatario", "corredor"}


def clasificar(prospecto: dict) -> dict:
    """Aplica reglas de clasificación en orden de prioridad. Retorna resultado."""
    subtipo = prospecto.get("subtipo_actor", "otro")
    es_cliente = prospecto.get("es_cliente_bp", 0)
    sit = prospecto.get("bcra_situacion", -1)
    hay_exp = prospecto.get("bcra_hay_exposicion", 0)
    conc_alta = prospecto.get("bcra_concentracion_alta", 0)
    monto = prospecto.get("bcra_monto_total", 0)
    score = prospecto.get("score_total", 0)

    tags = prospecto.get("tags", "[]")
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = []

    tiene_actividad = subtipo != "otro" or len(tags) > 0 or bool(prospecto.get("cadena_agro"))

    # --- Regla 0: datos insuficientes ---
    if sit == -1 and not tiene_actividad:
        resultado = {
            "clasificacion": "revisar_manual",
            "clasificacion_motivo": "Datos insuficientes para clasificación automática.",
            "semaforo": "investigar",
            "prioridad": "baja",
        }
        return _ajustar_final(resultado, prospecto)

    # --- Regla 1: corporativo_agregador ---
    if subtipo in CORPORATIVOS:
        semaforo = "contactar" if score >= 60 else "investigar"
        prioridad = "alta" if score >= 65 else "media" if score >= 45 else "baja"
        resultado = {
            "clasificacion": "corporativo_agregador",
            "clasificacion_motivo": f"Actor corporativo ({subtipo}). Potencial de volumen y agregación de clientes.",
            "semaforo": semaforo,
            "prioridad": prioridad,
        }
        return _ajustar_final(resultado, prospecto)

    # --- Regla 2: competencia_activa ---
    if not es_cliente and hay_exp and conc_alta and sit <= 2:
        entidad = prospecto.get("bcra_entidad_principal", "otra entidad")
        pct = prospecto.get("bcra_pct_entidad_principal", 0)
        semaforo = "contactar" if score >= 60 else "investigar"
        prioridad = "alta" if score >= 65 else "media" if score >= 45 else "baja"
        resultado = {
            "clasificacion": "competencia_activa",
            "clasificacion_motivo": f"Exposición concentrada en {entidad} ({pct:.0f}%). Situación normal. Oportunidad de captación.",
            "semaforo": semaforo,
            "prioridad": prioridad,
        }
        return _ajustar_final(resultado, prospecto)

    # --- Regla 3: oportunidad_limpia ---
    if not hay_exp and tiene_actividad:
        semaforo = "contactar" if score >= 55 else "investigar"
        prioridad = "alta" if score >= 60 else "media" if score >= 40 else "baja"
        resultado = {
            "clasificacion": "oportunidad_limpia",
            "clasificacion_motivo": "Sin exposición bancaria relevante detectada. Actividad agro confirmada. Prospecto limpio.",
            "semaforo": semaforo,
            "prioridad": prioridad,
        }
        return _ajustar_final(resultado, prospecto)

    # --- Regla 4: subatendido_potencial ---
    if tiene_actividad and monto > 0 and not hay_exp:
        if es_cliente:
            motivo = "Cliente BP con exposición baja para su perfil — oportunidad de cross-sell."
            semaforo = "contactar"
            prioridad = "alta" if score >= 55 else "media"
        else:
            motivo = "Actividad confirmada con exposición baja para su perfil. Potencial de profundización."
            semaforo = "investigar" if score < 55 else "contactar"
            prioridad = "media"
        resultado = {
            "clasificacion": "subatendido_potencial",
            "clasificacion_motivo": motivo,
            "semaforo": semaforo,
            "prioridad": prioridad,
        }
        return _ajustar_final(resultado, prospecto)

    # --- Regla 5: default ---
    resultado = {
        "clasificacion": "revisar_manual",
        "clasificacion_motivo": "No encaja en clasificación automática. Requiere revisión de datos.",
        "semaforo": "investigar",
        "prioridad": "baja",
    }
    return _ajustar_final(resultado, prospecto)


def _ajustar_final(resultado: dict, prospecto: dict) -> dict:
    """Post-ajustes por situación BCRA, cliente BP, cheques."""
    sit = prospecto.get("bcra_situacion_maxima", prospecto.get("bcra_situacion", -1))
    es_cliente = prospecto.get("es_cliente_bp", 0)
    cheques_pend = prospecto.get("bcra_cheques_pendientes", 0)

    # Ajuste por situación BCRA mala
    if sit >= 4:
        resultado["semaforo"] = "descartar"
        resultado["prioridad"] = "baja"
        resultado["clasificacion_motivo"] += f" Situación BCRA {sit} — riesgo crediticio elevado."
    elif sit == 3:
        if resultado["semaforo"] == "contactar":
            resultado["semaforo"] = "monitorear"
        resultado["clasificacion_motivo"] += " Situación BCRA 3 — precaución."

    # Ajuste por cliente BP
    if es_cliente:
        if resultado["clasificacion"] == "oportunidad_limpia":
            resultado["clasificacion"] = "subatendido_potencial"
            resultado["clasificacion_motivo"] = "Cliente BP existente (Procampo) con potencial de profundización."
        # Subir prioridad un nivel
        if resultado["prioridad"] == "baja":
            resultado["prioridad"] = "media"
        elif resultado["prioridad"] == "media":
            resultado["prioridad"] = "alta"

    # Ajuste por cheques rechazados
    if cheques_pend > 0:
        if resultado["prioridad"] == "alta":
            resultado["prioridad"] = "media"
        elif resultado["prioridad"] == "media":
            resultado["prioridad"] = "baja"

    return resultado


def sugerir_productos(prospecto: dict) -> list[dict]:
    """Sugiere productos BP según clasificación y cadena."""
    from services.zone_profile import PRODUCTOS_BP

    clasificacion = prospecto.get("clasificacion", "")
    cadena = prospecto.get("cadena_agro", "")
    subtipo = prospecto.get("subtipo_actor", "")
    productos = []

    if clasificacion in ("oportunidad_limpia", "subatendido_potencial"):
        if cadena in ("agricola", "mixta"):
            if "siembra" in PRODUCTOS_BP:
                productos.append(PRODUCTOS_BP["siembra"])
            if "procampo" in PRODUCTOS_BP:
                productos.append(PRODUCTOS_BP["procampo"])
        if cadena in ("ganadera", "mixta"):
            if "ganados" in PRODUCTOS_BP:
                productos.append(PRODUCTOS_BP["ganados"])
        if cadena == "lactea":
            if "lecheria" in PRODUCTOS_BP:
                productos.append(PRODUCTOS_BP["lecheria"])

    if clasificacion == "competencia_activa":
        if "procampo" in PRODUCTOS_BP:
            productos.append(PRODUCTOS_BP["procampo"])
        if "cap_trabajo" in PRODUCTOS_BP:
            productos.append(PRODUCTOS_BP["cap_trabajo"])

    if clasificacion == "corporativo_agregador":
        if "procampo_usd" in PRODUCTOS_BP:
            productos.append(PRODUCTOS_BP["procampo_usd"])
        if "tarjeta_procampo" in PRODUCTOS_BP:
            productos.append(PRODUCTOS_BP["tarjeta_procampo"])
        if "cap_trabajo" in PRODUCTOS_BP:
            productos.append(PRODUCTOS_BP["cap_trabajo"])

    # Si no matcheó nada, producto genérico
    if not productos:
        if "cap_trabajo" in PRODUCTOS_BP:
            productos.append(PRODUCTOS_BP["cap_trabajo"])

    return productos[:4]
