"""
Extractor de OpenStreetMap (Nominatim + Overpass con Multi-Mirror y Fallback Rápido).

Servicios usados:
  1. Nominatim  — Geocodificación y conteo de POIs fiable con User-Agent institucional.
  2. Overpass   — Conteo de POIs turísticos por coordenadas (hoteles, restaurantes, atracciones, museos).
     - Timeout rápido (3.5s por mirror) para no ralentizar el pipeline.
     - Fallback automático a Nominatim si los servidores Overpass están caídos o saturados.

Convención de columnas:
  - Geocodificación: OSM_Nominatim.<nombre>
  - Oferta/POIs:    OSM_Overpass.<nombre>
"""
from __future__ import annotations

import time
import unicodedata
from datetime import datetime
from typing import Optional

import requests

from src.utils.http_client import HttpClient
from src.utils.logger import get_logger
from config.settings import USER_AGENT

logger = get_logger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_MIRRORS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
_HEADERS = {"User-Agent": USER_AGENT}


class OSMExtractor:
    """Extractor robusto de OpenStreetMap con redundancia y fallbacks rápidos."""

    def __init__(self) -> None:
        self.client = HttpClient(min_interval=1.0)

    # ------------------------------------------------------------------
    # 1. Geocodificación Nominatim
    # ------------------------------------------------------------------
    def geocode_nominatim(
        self, municipio: str, pais: str = "España"
    ) -> Optional[dict]:
        """Geocodifica un municipio con OSM Nominatim."""
        try:
            params = {
                "q": f"{municipio}, {pais}",
                "format": "json",
                "limit": 1,
            }
            resp = requests.get(NOMINATIM_URL, params=params, headers=_HEADERS, timeout=6)
            results = resp.json()

            if not results:
                logger.warning("[OSM_Nominatim] Sin resultados para '%s'.", municipio)
                return None

            r = results[0]
            result = {
                "OSM_Nominatim.latitud":         float(r["lat"]),
                "OSM_Nominatim.longitud":        float(r["lon"]),
                "OSM_Nominatim.display_name":    r.get("display_name", ""),
                "_meta.fuente_geocod":           "OSM_Nominatim",
                "_meta.fecha_extraccion":        datetime.utcnow().isoformat(),
            }
            return result
        except Exception as exc:
            logger.warning("[OSM_Nominatim] Error geocodificando '%s': %s", municipio, exc)
            return None

    # ------------------------------------------------------------------
    # 2. Conteo de POIs Turísticos (Overpass con Fallback)
    # ------------------------------------------------------------------
    def poi_counts(
        self,
        municipio: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radio_metros: int = 8000,
    ) -> dict:
        """
        Cuenta los POIs turísticos de un municipio.

        Estrategia:
          1. Si se proporcionan lat y lon, consulta Overpass por radio local.
          2. Rota entre los servidores mirror de Overpass con timeout de 3.5s.
          3. Si Overpass falla por rate-limit o caída del servidor, usa Nominatim
             para devolver los conteos de POIs sin dejar valores nulos.
        """
        keys = [
            "OSM_Overpass.num_hoteles",
            "OSM_Overpass.num_restaurantes",
            "OSM_Overpass.num_atracciones",
            "OSM_Overpass.num_museos",
        ]

        # Si no tenemos coordenadas válidas, intentar obtenerlas de Nominatim
        if not lat or not lon or (lat == 0.0 and lon == 0.0):
            geo = self.geocode_nominatim(municipio)
            if geo:
                lat = geo["OSM_Nominatim.latitud"]
                lon = geo["OSM_Nominatim.longitud"]

        # ── Intento A: Overpass por radio de coordenadas ────────────────
        if lat and lon and (lat != 0.0 or lon != 0.0):
            query = f"""
            [out:json][timeout:6];
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
                    resp = requests.post(
                        mirror,
                        data={"data": query},
                        headers=_HEADERS,
                        timeout=3.5,
                    )
                    if resp.status_code == 200:
                        elements = resp.json().get("elements", [])
                        counts = [
                            int(el["tags"]["total"])
                            for el in elements
                            if el.get("type") == "count"
                        ]
                        if len(counts) >= 4:
                            res = dict(zip(keys, counts[:4]))
                            res["OSM_Overpass.fuente"] = f"Overpass ({mirror.split('/')[2]})"
                            res["OSM_Overpass.fecha_extraccion"] = datetime.utcnow().isoformat()
                            logger.info(
                                "[OSM] ✔ %s → hoteles=%d, restaurantes=%d, atracciones=%d, museos=%d [vía %s]",
                                municipio, res[keys[0]], res[keys[1]], res[keys[2]], res[keys[3]], res["OSM_Overpass.fuente"]
                            )
                            return res
                except Exception:
                    continue

        # ── Intento B: Fallback a Nominatim ──────────────────────────────
        logger.info("[OSM] ↪ Overpass no disponible para '%s'; usando fallback Nominatim...", municipio)
        try:
            res_nom = {}
            for cat, k in [("hotel", keys[0]), ("restaurante", keys[1]), ("turismo", keys[2]), ("museo", keys[3])]:
                p = {"q": f"{cat} en {municipio}, España", "format": "json", "limit": 50}
                r = requests.get(NOMINATIM_URL, params=p, headers=_HEADERS, timeout=4)
                if r.status_code == 200:
                    res_nom[k] = len(r.json())
                else:
                    res_nom[k] = 0
                time.sleep(0.2)

            res_nom["OSM_Overpass.fuente"] = "OSM_Nominatim_Fallback"
            res_nom["OSM_Overpass.fecha_extraccion"] = datetime.utcnow().isoformat()
            logger.info(
                "[OSM] ✔ %s (Fallback Nominatim) → hoteles=%d, restaurantes=%d, atracciones=%d, museos=%d",
                municipio, res_nom[keys[0]], res_nom[keys[1]], res_nom[keys[2]], res_nom[keys[3]]
            )
            return res_nom
        except Exception as exc:
            logger.warning("[OSM] ✗ Fallback Nominatim falló para '%s': %s", municipio, exc)

        return {k: 0 for k in keys} | {
            "OSM_Overpass.fuente": "Sin_Dato_OSM",
            "OSM_Overpass.fecha_extraccion": datetime.utcnow().isoformat(),
        }
