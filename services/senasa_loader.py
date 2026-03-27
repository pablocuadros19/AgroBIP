"""Ingesta de datos ganaderos reales de SENASA (existencias bovinas)."""

import pandas as pd
import requests
import streamlit as st
from pathlib import Path

DATA_DIR = Path("data/real")

URL_BOVINOS = "https://datos.magyp.gob.ar/dataset/c19a5875-fb39-48b6-b0b2-234382722afb/resource/1b920477-8112-4e12-bc2c-94b564f04183/download/existencias-bovinas-provincia-departamento-2008-2019.csv"

PROVINCIAS_MVP_IDS = [6, 14, 82, 30, 42]

CATEGORIAS_BOVINAS = ["vacas", "vaquillonas", "novillos", "novillitos", "terneros", "terneras", "toros", "toritos", "bueyes"]


def _descargar_bovinos() -> Path:
    """Descarga CSV de SENASA si no existe."""
    path = DATA_DIR / "bovinos.csv"
    if path.exists():
        return path
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    r = requests.get(URL_BOVINOS, timeout=60)
    r.raise_for_status()
    path.write_bytes(r.content)
    return path


def _georef_id(departamento_id) -> str:
    return str(int(departamento_id)).zfill(5)


@st.cache_data(ttl=3600, show_spinner=False)
def cargar_bovinos() -> pd.DataFrame:
    """Carga datos de bovinos filtrado a provincias MVP, último año disponible."""
    path = _descargar_bovinos()
    df = pd.read_csv(path, encoding="latin-1")
    df = df[df["provincia_id"].isin(PROVINCIAS_MVP_IDS)].copy()
    df["georef_id"] = df["departamento_id"].apply(_georef_id)

    # Calcular total de cabezas
    cols_num = [c for c in CATEGORIAS_BOVINAS if c in df.columns]
    df["total_cabezas"] = df[cols_num].sum(axis=1)

    return df


def get_bovinos_depto(georef_id: str) -> dict:
    """Datos ganaderos para un departamento (último año disponible)."""
    df = cargar_bovinos()
    if df.empty:
        return {}

    depto = df[df["georef_id"] == georef_id]
    if depto.empty:
        return {}

    # Último año
    ultimo_anio = depto["anio"].max()
    row = depto[depto["anio"] == ultimo_anio].iloc[0]

    resultado = {
        "anio": int(ultimo_anio),
        "departamento": row["departamento"],
        "provincia": row["provincia"],
        "total_cabezas": int(row["total_cabezas"]),
        "categorias": {},
    }

    for cat in CATEGORIAS_BOVINAS:
        if cat in row.index:
            val = row[cat]
            if pd.notna(val):
                resultado["categorias"][cat] = int(val)

    return resultado


@st.cache_data(ttl=3600, show_spinner=False)
def get_resumen_bovinos() -> list:
    """Resumen ganadero de todos los departamentos (último año)."""
    df = cargar_bovinos()
    if df.empty:
        return []

    ultimo_anio = df["anio"].max()
    df_ult = df[df["anio"] == ultimo_anio]

    resumen = []
    for _, row in df_ult.iterrows():
        resumen.append({
            "georef_id": row["georef_id"],
            "departamento": row["departamento"],
            "provincia": row["provincia"],
            "total_cabezas": int(row["total_cabezas"]),
        })

    return sorted(resumen, key=lambda x: x["total_cabezas"], reverse=True)


def get_totales_bovinos() -> dict:
    """Totales ganaderos agregados."""
    df = cargar_bovinos()
    if df.empty:
        return {"total_cabezas": 0, "deptos": 0, "anio": "—"}
    ultimo_anio = df["anio"].max()
    df_ult = df[df["anio"] == ultimo_anio]
    return {
        "total_cabezas": int(df_ult["total_cabezas"].sum()),
        "deptos": df_ult["georef_id"].nunique(),
        "anio": int(ultimo_anio),
    }
