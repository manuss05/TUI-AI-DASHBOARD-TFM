"""Extractor de OpenStreetMap (Nominatim y Overpass) en formato crudo."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

import requests

from config.settings import USER_AGENT
from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_MIRRORS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
_HEADERS = {"User-Agent": USER_AGENT}


class OSMExtractor:
    """Extractor OSM sin transformaciones de datos."""

    def __init__(self) -> None:
        self.client = HttpClient(min_interval=1.0)

    def geocode_nominatim(self, query: str) -> Optional[dict]:
        """Devuelve la respuesta completa de Nominatim sin truncar."""
        try:
            params = {"q": query, "format": "json", "limit": 1}
            resp = requests.get(NOMINATIM_URL, params=params, headers=_HEADERS, timeout=6)
            results = resp.json()
            if not results:
                return None
            r = results[0]
            return {
                "query": query,
                "place_id": r.get("place_id"),
                "osm_type": r.get("osm_type", ""),
                "osm_id": r.get("osm_id"),
                "lat": r.get("lat"),
                "lon": r.get("lon"),
                "display_name": r.get("display_name", ""),
                "class": r.get("class", ""),
                "type": r.get("type", ""),
                "importance": r.get("importance"),
                "raw_json": json.dumps(r, ensure_ascii=False),
                "_meta.fecha_extraccion": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.warning("[OSM_Nominatim] Error en '%s': %s", query, exc)
            return None

    def query_overpass_counts(
        self, query_name: str, lat: float, lon: float, radio_metros: int = 8000
    ) -> dict:
        """Ejecuta consulta de conteo en Overpass y devuelve las respuestas crudas de los elementos."""
        query = f"""
        [out:json][timeout:10];
        (
          node["tourism"="hotel"](around:{radio_metros}, {lat}, {lon});
          way["tourism"="hotel"](around:{radio_metros}, {lat}, {lon});
        )->.hoteles;
        (
          node["amenity"="restaurant"](around:{radio_metros}, {lat}, {lon});
          way["amenity"="restaurant"](around:{radio_metros}, {lat}, {lon});
        )->.restaurantes;
        (
          node["tourism"="attraction"](around:{radio_metros}, {lat}, {lon});
          way["tourism"="attraction"](around:{radio_metros}, {lat}, {lon});
        )->.atracciones;
        (
          node["tourism"="museum"](around:{radio_metros}, {lat}, {lon});
          way["tourism"="museum"](around:{radio_metros}, {lat}, {lon});
        )->.museos;
        .hoteles      out count;
        .restaurantes out count;
        .atracciones  out count;
        .museos       out count;
        """
        for mirror in OVERPASS_MIRRORS:
            try:
                resp = requests.post(mirror, data={"data": query}, headers=_HEADERS, timeout=6.0)
                if resp.status_code == 200:
                    elements = resp.json().get("elements", [])
                    return {
                        "query_name": query_name,
                        "lat": lat,
                        "lon": lon,
                        "radio_metros": radio_metros,
                        "mirror_usado": mirror,
                        "elements_raw_json": json.dumps(elements, ensure_ascii=False),
                        "_meta.fecha_extraccion": datetime.utcnow().isoformat(),
                    }
            except Exception:
                continue
        return {
            "query_name": query_name,
            "lat": lat,
            "lon": lon,
            "radio_metros": radio_metros,
            "mirror_usado": "FAILED",
            "elements_raw_json": "[]",
            "_meta.fecha_extraccion": datetime.utcnow().isoformat(),
        }
