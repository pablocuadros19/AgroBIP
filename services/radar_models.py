"""Radar Agro — Modelo de datos SQLite y operaciones CRUD."""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "radar_agro.db")

_conn = None


def get_db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        init_db(_conn)
    return _conn


def init_db(conn: sqlite3.Connection):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS prospectos (
        cuit TEXT PRIMARY KEY,
        razon_social TEXT,
        provincia TEXT DEFAULT 'Buenos Aires',
        partido TEXT,
        localidad TEXT,
        actividad_fuente_base TEXT,
        fuente_origen TEXT,
        tipo_societario TEXT,
        es_proveedor_estado INTEGER DEFAULT 0,
        monto_adj_estado REAL DEFAULT 0,
        tags TEXT DEFAULT '[]',
        cadena_agro TEXT,
        subtipo_actor TEXT DEFAULT 'otro',
        es_cliente_bp INTEGER DEFAULT 0,
        fuente_procampo TEXT,
        bcra_situacion INTEGER DEFAULT -1,
        bcra_situacion_texto TEXT,
        bcra_monto_total REAL DEFAULT 0,
        bcra_cantidad_entidades INTEGER DEFAULT 0,
        bcra_entidad_principal TEXT,
        bcra_pct_entidad_principal REAL DEFAULT 0,
        bcra_situacion_maxima INTEGER DEFAULT 0,
        bcra_hay_exposicion INTEGER DEFAULT 0,
        bcra_concentracion_alta INTEGER DEFAULT 0,
        bcra_exposicion_diversificada INTEGER DEFAULT 0,
        bcra_tiene_refinanciaciones INTEGER DEFAULT 0,
        bcra_cheques_rechazados INTEGER DEFAULT 0,
        bcra_cheques_pendientes INTEGER DEFAULT 0,
        bcra_evolucion TEXT,
        bcra_ultimo_periodo TEXT,
        bcra_detalle TEXT,
        bcra_deuda_bapro INTEGER DEFAULT 0,
        clasificacion TEXT DEFAULT 'pendiente',
        clasificacion_motivo TEXT,
        score_total INTEGER DEFAULT 0,
        score_perfil_sectorial REAL DEFAULT 0,
        score_oportunidad_financiera REAL DEFAULT 0,
        score_relevancia_comercial REAL DEFAULT 0,
        score_calidad_datos REAL DEFAULT 0,
        score_motivo TEXT,
        semaforo TEXT DEFAULT 'pendiente',
        prioridad TEXT DEFAULT 'baja',
        fecha_importacion TEXT,
        fecha_bcra TEXT,
        fecha_clasificacion TEXT,
        lote_id TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_clasificacion ON prospectos(clasificacion);
    CREATE INDEX IF NOT EXISTS idx_score ON prospectos(score_total DESC);
    CREATE INDEX IF NOT EXISTS idx_semaforo ON prospectos(semaforo);
    CREATE INDEX IF NOT EXISTS idx_cliente_bp ON prospectos(es_cliente_bp);
    CREATE INDEX IF NOT EXISTS idx_partido ON prospectos(partido);

    CREATE TABLE IF NOT EXISTS bcra_cache (
        cuit TEXT PRIMARY KEY,
        response_json TEXT,
        fecha_consulta TEXT,
        exito INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS procampo (
        cuit TEXT PRIMARY KEY,
        razon_social TEXT,
        tipo TEXT,
        fecha_carga TEXT
    );

    CREATE TABLE IF NOT EXISTS importaciones (
        id TEXT PRIMARY KEY,
        archivo TEXT,
        fecha TEXT,
        total INTEGER DEFAULT 0,
        nuevos INTEGER DEFAULT 0,
        duplicados INTEGER DEFAULT 0,
        estado TEXT DEFAULT 'completado'
    );
    """)
    conn.commit()

    # Migración: agregar columna bcra_deuda_bapro si no existe (DBs creadas antes)
    try:
        conn.execute("SELECT bcra_deuda_bapro FROM prospectos LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE prospectos ADD COLUMN bcra_deuda_bapro INTEGER DEFAULT 0")
        conn.commit()


def insertar_prospectos(prospectos: list[dict]) -> dict:
    """Inserta prospectos en lote. Retorna {total, nuevos, duplicados}."""
    db = get_db()
    nuevos = 0
    duplicados = 0
    ahora = datetime.now().isoformat()

    for p in prospectos:
        cuit = p.get("cuit", "").strip()
        if not cuit:
            continue
        tags = p.get("tags", [])
        if isinstance(tags, list):
            tags = json.dumps(tags, ensure_ascii=False)

        try:
            db.execute("""
                INSERT OR IGNORE INTO prospectos (
                    cuit, razon_social, provincia, partido, localidad,
                    actividad_fuente_base, fuente_origen, tipo_societario,
                    es_proveedor_estado, monto_adj_estado,
                    tags, cadena_agro, subtipo_actor,
                    fecha_importacion, lote_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cuit,
                p.get("razon_social", ""),
                p.get("provincia", "Buenos Aires"),
                p.get("partido", ""),
                p.get("localidad", ""),
                p.get("actividad_fuente_base", ""),
                p.get("fuente_origen", "csv"),
                p.get("tipo_societario", ""),
                int(p.get("es_proveedor_estado", 0)),
                float(p.get("monto_adj_estado", 0)),
                tags,
                p.get("cadena_agro", ""),
                p.get("subtipo_actor", "otro"),
                ahora,
                p.get("lote_id", ""),
            ))
            if db.total_changes > 0:
                nuevos += 1
            else:
                duplicados += 1
        except sqlite3.IntegrityError:
            duplicados += 1

    db.commit()
    return {"total": len(prospectos), "nuevos": nuevos, "duplicados": duplicados}


def actualizar_prospecto(cuit: str, campos: dict):
    """Actualiza campos arbitrarios de un prospecto."""
    db = get_db()
    sets = []
    vals = []
    for k, v in campos.items():
        sets.append(f"{k} = ?")
        vals.append(v)
    vals.append(cuit)
    db.execute(f"UPDATE prospectos SET {', '.join(sets)} WHERE cuit = ?", vals)
    db.commit()


def get_prospecto(cuit: str) -> dict | None:
    db = get_db()
    row = db.execute("SELECT * FROM prospectos WHERE cuit = ?", (cuit,)).fetchone()
    if row is None:
        return None
    return dict(row)


def get_prospectos(filtros: dict | None = None, orden: str = "score_total DESC",
                   limite: int = 0) -> list[dict]:
    """Consulta prospectos con filtros opcionales."""
    db = get_db()
    where_clauses = []
    params = []

    if filtros:
        if filtros.get("clasificacion"):
            placeholders = ",".join("?" for _ in filtros["clasificacion"])
            where_clauses.append(f"clasificacion IN ({placeholders})")
            params.extend(filtros["clasificacion"])

        if filtros.get("semaforo"):
            placeholders = ",".join("?" for _ in filtros["semaforo"])
            where_clauses.append(f"semaforo IN ({placeholders})")
            params.extend(filtros["semaforo"])

        if filtros.get("prioridad") and filtros["prioridad"] != "Todas":
            where_clauses.append("prioridad = ?")
            params.append(filtros["prioridad"])

        if filtros.get("busqueda"):
            where_clauses.append("(razon_social LIKE ? OR cuit LIKE ?)")
            term = f"%{filtros['busqueda']}%"
            params.extend([term, term])

        if filtros.get("cadena_agro") and filtros["cadena_agro"] != "Todas":
            where_clauses.append("cadena_agro = ?")
            params.append(filtros["cadena_agro"])

        if filtros.get("solo_clientes_bp"):
            where_clauses.append("es_cliente_bp = 1")

        if filtros.get("solo_proveedor_estado"):
            where_clauses.append("es_proveedor_estado = 1")

        if filtros.get("partido"):
            placeholders = ",".join("?" for _ in filtros["partido"])
            where_clauses.append(f"partido IN ({placeholders})")
            params.extend(filtros["partido"])

        if filtros.get("deuda_bapro"):
            where_clauses.append("bcra_deuda_bapro = 1")

    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    limit = f"LIMIT {limite}" if limite > 0 else ""
    query = f"SELECT * FROM prospectos {where} ORDER BY {orden} {limit}"

    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_kpis() -> dict:
    """KPIs agregados del universo de prospectos."""
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM prospectos").fetchone()[0]
    if total == 0:
        return {
            "total": 0, "contactar": 0, "score_promedio": 0,
            "clientes_bp": 0, "pendientes_bcra": 0,
            "por_clasificacion": {}, "por_semaforo": {}, "por_prioridad": {},
        }

    contactar = db.execute(
        "SELECT COUNT(*) FROM prospectos WHERE semaforo = 'contactar'"
    ).fetchone()[0]

    score_prom = db.execute(
        "SELECT AVG(score_total) FROM prospectos WHERE clasificacion != 'pendiente'"
    ).fetchone()[0] or 0

    clientes_bp = db.execute(
        "SELECT COUNT(*) FROM prospectos WHERE es_cliente_bp = 1"
    ).fetchone()[0]

    pendientes_bcra = db.execute(
        "SELECT COUNT(*) FROM prospectos WHERE bcra_situacion = -1"
    ).fetchone()[0]

    # Distribución por clasificación
    rows_clas = db.execute(
        "SELECT clasificacion, COUNT(*) as n FROM prospectos GROUP BY clasificacion"
    ).fetchall()
    por_clasificacion = {r["clasificacion"]: r["n"] for r in rows_clas}

    # Distribución por semáforo
    rows_sem = db.execute(
        "SELECT semaforo, COUNT(*) as n FROM prospectos GROUP BY semaforo"
    ).fetchall()
    por_semaforo = {r["semaforo"]: r["n"] for r in rows_sem}

    # Distribución por prioridad
    rows_pri = db.execute(
        "SELECT prioridad, COUNT(*) as n FROM prospectos GROUP BY prioridad"
    ).fetchall()
    por_prioridad = {r["prioridad"]: r["n"] for r in rows_pri}

    return {
        "total": total,
        "contactar": contactar,
        "score_promedio": round(score_prom),
        "clientes_bp": clientes_bp,
        "pendientes_bcra": pendientes_bcra,
        "por_clasificacion": por_clasificacion,
        "por_semaforo": por_semaforo,
        "por_prioridad": por_prioridad,
    }


def get_partidos_distintos() -> list[str]:
    """Retorna lista de partidos/localidades únicos en prospectos."""
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT partido FROM prospectos WHERE partido != '' ORDER BY partido"
    ).fetchall()
    return [r["partido"] for r in rows]


def get_pendientes_bcra_por_partido(partidos: list[str], max_dias: int = 30) -> list[str]:
    """CUITs pendientes de BCRA filtrados por partido."""
    db = get_db()
    from datetime import timedelta
    limite = (datetime.now() - timedelta(days=max_dias)).isoformat()
    placeholders = ",".join("?" for _ in partidos)
    rows = db.execute(f"""
        SELECT cuit FROM prospectos
        WHERE partido IN ({placeholders})
        AND (bcra_situacion = -1 OR fecha_bcra IS NULL OR fecha_bcra < ?)
    """, (*partidos, limite)).fetchall()
    return [r["cuit"] for r in rows]


def get_pendientes_bcra(max_dias: int = 30) -> list[str]:
    """CUITs que no tienen consulta BCRA o la tienen vencida."""
    db = get_db()
    limite = datetime(2000, 1, 1).isoformat()
    if max_dias > 0:
        from datetime import timedelta
        limite = (datetime.now() - timedelta(days=max_dias)).isoformat()

    rows = db.execute("""
        SELECT cuit FROM prospectos
        WHERE bcra_situacion = -1 OR fecha_bcra IS NULL OR fecha_bcra < ?
    """, (limite,)).fetchall()
    return [r["cuit"] for r in rows]


def insertar_procampo(registros: list[dict]):
    db = get_db()
    ahora = datetime.now().isoformat()
    for r in registros:
        cuit = r.get("cuit", "").strip()
        if not cuit:
            continue
        db.execute("""
            INSERT OR REPLACE INTO procampo (cuit, razon_social, tipo, fecha_carga)
            VALUES (?, ?, ?, ?)
        """, (cuit, r.get("razon_social", ""), r.get("tipo", ""), ahora))
    db.commit()


def cruzar_procampo():
    """Marca prospectos que aparecen en tabla procampo."""
    db = get_db()
    db.execute("""
        UPDATE prospectos SET es_cliente_bp = 1, fuente_procampo = (
            SELECT tipo FROM procampo WHERE procampo.cuit = prospectos.cuit
        ) WHERE cuit IN (SELECT cuit FROM procampo)
    """)
    db.commit()


def log_importacion(lote_id: str, archivo: str, total: int, nuevos: int, duplicados: int):
    db = get_db()
    db.execute("""
        INSERT OR REPLACE INTO importaciones (id, archivo, fecha, total, nuevos, duplicados, estado)
        VALUES (?, ?, ?, ?, ?, ?, 'completado')
    """, (lote_id, archivo, datetime.now().isoformat(), total, nuevos, duplicados))
    db.commit()


def get_top_bancos_competencia(limite: int = 5) -> list[dict]:
    """Top bancos donde están concentrados los prospectos (para mapa competitivo)."""
    db = get_db()
    rows = db.execute("""
        SELECT bcra_entidad_principal as entidad, COUNT(*) as cantidad,
               ROUND(AVG(bcra_pct_entidad_principal), 1) as pct_promedio
        FROM prospectos
        WHERE bcra_entidad_principal IS NOT NULL AND bcra_entidad_principal != ''
        GROUP BY bcra_entidad_principal
        ORDER BY cantidad DESC
        LIMIT ?
    """, (limite,)).fetchall()
    return [dict(r) for r in rows]


def exportar_df(filtros: dict | None = None):
    """Retorna DataFrame para exportación."""
    import pandas as pd
    prospectos = get_prospectos(filtros=filtros)
    if not prospectos:
        return pd.DataFrame()

    columnas_export = [
        "cuit", "razon_social", "provincia", "partido", "localidad",
        "cadena_agro", "subtipo_actor", "tipo_societario",
        "es_proveedor_estado", "es_cliente_bp",
        "clasificacion", "score_total", "prioridad", "semaforo",
        "bcra_situacion_texto", "bcra_monto_total",
        "bcra_cantidad_entidades", "bcra_entidad_principal",
        "bcra_pct_entidad_principal", "bcra_evolucion",
        "bcra_deuda_bapro",
        "bcra_cheques_rechazados", "bcra_cheques_pendientes",
        "clasificacion_motivo", "score_motivo",
        "score_perfil_sectorial", "score_oportunidad_financiera",
        "score_relevancia_comercial", "score_calidad_datos",
    ]
    df = pd.DataFrame(prospectos)
    cols_disponibles = [c for c in columnas_export if c in df.columns]
    return df[cols_disponibles]
