"""Carga y funciones geoespaciales para departamentos argentinos."""

import json
from pathlib import Path
from functools import lru_cache

GEOJSON_PATH = Path("data/departamentos.geojson")

# Provincias de Pampa Húmeda (foco del MVP)
PROVINCIAS_MVP = ["Buenos Aires", "Córdoba", "Santa Fe", "Entre Ríos", "La Pampa"]


@lru_cache(maxsize=1)
def cargar_geojson():
    """Carga el GeoJSON completo de departamentos."""
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def filtrar_por_provincias(geojson, provincias=None):
    """Filtra features del GeoJSON por lista de provincias."""
    if provincias is None:
        provincias = PROVINCIAS_MVP

    provincias_lower = [p.lower() for p in provincias]
    features_filtradas = [
        f for f in geojson["features"]
        if f["properties"].get("provincia", {}).get("nombre", "").lower() in provincias_lower
    ]
    return {
        "type": "FeatureCollection",
        "features": features_filtradas,
    }


def get_departamento_id(feature):
    """Extrae el ID de un feature de departamento."""
    return feature["properties"].get("id", "")


def get_departamento_nombre(feature):
    """Extrae el nombre de un feature."""
    return feature["properties"].get("nombre", "")


def get_provincia_nombre(feature):
    """Extrae la provincia de un feature."""
    return feature["properties"].get("provincia", {}).get("nombre", "")


def get_centroide(feature):
    """Calcula centroide aproximado de un feature (promedio de coordenadas)."""
    geom = feature.get("geometry", {})
    coords = geom.get("coordinates", [])

    if not coords:
        return None, None

    # Aplanar coordenadas según tipo de geometría
    flat = []
    geom_type = geom.get("type", "")

    if geom_type == "Polygon":
        for ring in coords:
            flat.extend(ring)
    elif geom_type == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                flat.extend(ring)

    if not flat:
        return None, None

    lons = [c[0] for c in flat]
    lats = [c[1] for c in flat]
    return sum(lats) / len(lats), sum(lons) / len(lons)


def listar_provincias(geojson):
    """Lista provincias únicas del GeoJSON."""
    provincias = set()
    for f in geojson["features"]:
        prov = get_provincia_nombre(f)
        if prov:
            provincias.add(prov)
    return sorted(provincias)


def buscar_departamento(geojson, depto_id):
    """Busca un departamento por ID."""
    for f in geojson["features"]:
        if get_departamento_id(f) == depto_id:
            return f
    return None
