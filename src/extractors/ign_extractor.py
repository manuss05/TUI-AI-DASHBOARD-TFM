"""Extractor del IGN via CartoCiudad — geocodificacion con enriquecimiento Nominatim."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

CANDIDATES_URL = "https://www.cartociudad.es/geocoder/api/geocoder/candidates"
NOMINATIM_URL  = "https://nominatim.openstreetmap.org/search"


class IGNExtractor:
    """Geocodificador oficial INE/IGN vía CartoCiudad con enriquecimiento de coordenadas."""

    def __init__(self) -> None:
        self.client = HttpClient(min_interval=1.0)

    def geocode(self, municipio: str) -> Optional[dict]:
        """
        Geocodifica un municipio usando CartoCiudad (para cod_ine) y Nominatim (para coordenadas).

        Devuelve un dict con claves CartoCiudad.* o None si falla.
        """
        try:
            resp = self.client.get(
                CANDIDATES_URL,
                params={"q": municipio, "limit": 1},
            )
            data = resp.json()

            if not isinstance(data, list) or not data:
                logger.warning("[CartoCiudad] Sin resultados para '%s'.", municipio)
                return None

            c = data[0]
            lat = float(c.get("lat") or 0.0)
            lng = float(c.get("lng") or 0.0)
            cod_ine = c.get("muniCode") or c.get("provinceCode", "")

            # Si CartoCiudad devuelve 0.0, enriquecer con Nominatim
            if lat == 0.0 and lng == 0.0:
                try:
                    time.sleep(0.5)
                    resp_nom = self.client.get(
                        NOMINATIM_URL,
                        params={"q": f"{municipio}, España", "format": "json", "limit": 1},
                    )
                    nom_data = resp_nom.json()
                    if nom_data:
                        lat = float(nom_data[0]["lat"])
                        lng = float(nom_data[0]["lon"])
                except Exception:
                    pass

            result = {
                "CartoCiudad.cod_ine":          str(cod_ine).zfill(5) if cod_ine else "",
                "CartoCiudad.nombre_municipio": c.get("muni") or municipio,
                "CartoCiudad.provincia":        c.get("province", ""),
                "CartoCiudad.ccaa":             c.get("comunidadAutonoma", ""),
                "CartoCiudad.latitud":          lat,
                "CartoCiudad.longitud":         lng,
                "_meta.fuente_geocod":          "CartoCiudad+IGN",
                "_meta.fecha_extraccion":       datetime.utcnow().isoformat(),
            }
            logger.info("[CartoCiudad] %s -> %s", municipio, result["CartoCiudad.cod_ine"])
            return result

        except Exception as exc:
            logger.warning("[CartoCiudad] Error '%s': %s", municipio, exc)
            return None
