"""Ingesta de datos productivos reales de MAGyP (estimaciones agrícolas)."""

import os
import pandas as pd
import requests
import streamlit as st
from pathlib import Path

DATA_DIR = Path("data/real")

URLS_MAGYP = {
    "soja": "https://datos.magyp.gob.ar/dataset/8ae4865f-d2f2-45a2-9343-7a4a12728a90/resource/ba694aa3-99d2-4d7d-9936-60f88e36ad9a/download/soja-serie-1941-2024.csv",
    "maiz": "https://datos.magyp.gob.ar/dataset/514853fc-0a78-4b6f-a42f-8e89eab784c8/resource/9a6a02f8-ef58-4250-87c2-f639fec502f1/download/maiz-serie-1923-2024.csv",
    "trigo": "https://datos.magyp.gob.ar/dataset/10105e94-c560-4b02-b15f-ef3ef764b833/resource/50f0edcc-4dfc-4afb-b78a-b164601d36ae/download/trigo-serie-1927-2024.csv",
}

PROVINCIAS_MVP_IDS = [6, 14, 82, 30, 42]  # BsAs, Córdoba, Santa Fe, Entre Ríos, La Pampa

ENCODINGS = {"soja": "utf-8", "maiz": "latin-1", "trigo": "latin-1"}


def _descargar_csv(cultivo: str) -> Path:
    """Descarga CSV de MAGyP si no existe localmente."""
    path = DATA_DIR / f"{cultivo}.csv"
    if path.exists():
        return path
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    url = URLS_MAGYP[cultivo]
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    path.write_bytes(r.content)
    return path


def _georef_id(departamento_id) -> str:
    """Convierte departamento_id de MAGyP a ID de GeoJSON Georef."""
    return str(int(departamento_id)).zfill(5)


@st.cache_data(ttl=3600, show_spinner=False)
def cargar_produccion(cultivo: str) -> pd.DataFrame:
    """Carga DataFrame de producción filtrado a provincias MVP."""
    path = _descargar_csv(cultivo)
    enc = ENCODINGS.get(cultivo, "utf-8")
    df = pd.read_csv(path, encoding=enc)
    df = df[df["provincia_id"].isin(PROVINCIAS_MVP_IDS)].copy()
    df["georef_id"] = df["departamento_id"].apply(_georef_id)
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def cargar_todos_los_cultivos() -> pd.DataFrame:
    """Carga y concatena soja + maíz + trigo."""
    dfs = []
    for cultivo in URLS_MAGYP:
        try:
            dfs.append(cargar_produccion(cultivo))
        except Exception:
            continue
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def get_ultima_campania(df: pd.DataFrame) -> str:
    """Retorna la última campaña disponible."""
    campanias = sorted(df["campania"].unique())
    return campanias[-1] if campanias else ""


def get_produccion_depto(georef_id: str) -> dict:
    """Datos de producción de todos los cultivos para un departamento (última campaña)."""
    df = cargar_todos_los_cultivos()
    if df.empty:
        return {}
    ultima = get_ultima_campania(df)
    depto = df[(df["georef_id"] == georef_id) & (df["campania"] == ultima)]
    if depto.empty:
        return {}

    resultado = {
        "campania": ultima,
        "departamento": depto.iloc[0]["departamento"],
        "provincia": depto.iloc[0]["provincia"],
        "cultivos": {},
        "superficie_total_ha": 0,
        "produccion_total_tm": 0,
    }

    for _, row in depto.iterrows():
        cultivo = row["cultivo"].lower().strip()
        sup = row.get("superficie_sembrada_ha", 0) or 0
        prod = row.get("produccion_tm", 0) or 0
        rend = row.get("rendimiento_kgxha", 0) or 0
        resultado["cultivos"][cultivo] = {
            "superficie_sembrada_ha": float(sup),
            "superficie_cosechada_ha": float(row.get("superficie_cosechada_ha", 0) or 0),
            "produccion_tm": float(prod),
            "rendimiento_kgxha": float(rend),
        }
        resultado["superficie_total_ha"] += float(sup)
        resultado["produccion_total_tm"] += float(prod)

    # Cultivo principal por superficie
    if resultado["cultivos"]:
        principal = max(resultado["cultivos"].items(), key=lambda x: x[1]["superficie_sembrada_ha"])
        resultado["cultivo_principal"] = principal[0].capitalize()
    else:
        resultado["cultivo_principal"] = "—"

    return resultado


def get_tendencia_depto(georef_id: str, n: int = 5) -> list:
    """Evolución de superficie sembrada total en últimas n campañas."""
    df = cargar_todos_los_cultivos()
    if df.empty:
        return []
    depto = df[df["georef_id"] == georef_id]
    campanias = sorted(depto["campania"].unique())[-n:]

    tendencia = []
    for camp in campanias:
        camp_data = depto[depto["campania"] == camp]
        sup_total = camp_data["superficie_sembrada_ha"].sum()
        prod_total = camp_data["produccion_tm"].sum()
        tendencia.append({
            "campania": camp,
            "superficie_total_ha": float(sup_total),
            "produccion_total_tm": float(prod_total),
        })
    return tendencia


def get_variacion_superficie(georef_id: str) -> float:
    """Variación % de superficie sembrada entre últimas 2 campañas."""
    tendencia = get_tendencia_depto(georef_id, n=2)
    if len(tendencia) < 2:
        return 0.0
    anterior = tendencia[0]["superficie_total_ha"]
    actual = tendencia[1]["superficie_total_ha"]
    if anterior == 0:
        return 0.0
    return ((actual - anterior) / anterior) * 100


@st.cache_data(ttl=3600, show_spinner=False)
def get_resumen_todos_deptos() -> list:
    """Resumen de producción para todos los departamentos (última campaña)."""
    df = cargar_todos_los_cultivos()
    if df.empty:
        return []
    ultima = get_ultima_campania(df)
    df_ult = df[df["campania"] == ultima]

    # Agrupar por departamento
    resumen = []
    for georef_id, grupo in df_ult.groupby("georef_id"):
        sup_total = grupo["superficie_sembrada_ha"].sum()
        sup_cosechada = grupo["superficie_cosechada_ha"].sum()
        prod_total = grupo["produccion_tm"].sum()
        # Cultivo principal
        por_cultivo = grupo.groupby("cultivo")["superficie_sembrada_ha"].sum()
        cultivo_principal = por_cultivo.idxmax() if not por_cultivo.empty else "—"

        resumen.append({
            "georef_id": georef_id,
            "departamento": grupo.iloc[0]["departamento"],
            "provincia": grupo.iloc[0]["provincia"],
            "superficie_total_ha": float(sup_total),
            "superficie_cosechada_ha": float(sup_cosechada),
            "produccion_total_tm": float(prod_total),
            "cultivo_principal": cultivo_principal.capitalize() if isinstance(cultivo_principal, str) else "—",
            "n_cultivos": len(por_cultivo),
        })

    return sorted(resumen, key=lambda x: x["superficie_total_ha"], reverse=True)


def get_ranking_departamentos(cultivo: str, metrica: str = "superficie_sembrada_ha", n: int = 20) -> list:
    """Ranking de departamentos para un cultivo y métrica."""
    df = cargar_produccion(cultivo)
    if df.empty:
        return []
    ultima = get_ultima_campania(df)
    df_ult = df[df["campania"] == ultima].copy()
    df_ult = df_ult.sort_values(metrica, ascending=False).head(n)

    return [
        {
            "georef_id": row["georef_id"],
            "departamento": row["departamento"],
            "provincia": row["provincia"],
            metrica: float(row[metrica] or 0),
        }
        for _, row in df_ult.iterrows()
    ]


def get_totales_mvp() -> dict:
    """Totales agregados para todas las provincias MVP."""
    df = cargar_todos_los_cultivos()
    if df.empty:
        return {"superficie_ha": 0, "produccion_tm": 0, "deptos": 0, "campania": "—"}
    ultima = get_ultima_campania(df)
    df_ult = df[df["campania"] == ultima]
    return {
        "superficie_ha": float(df_ult["superficie_sembrada_ha"].sum()),
        "produccion_tm": float(df_ult["produccion_tm"].sum()),
        "deptos": df_ult["georef_id"].nunique(),
        "campania": ultima,
    }
