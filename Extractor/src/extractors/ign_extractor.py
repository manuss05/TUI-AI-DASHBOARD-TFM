"""Extractor del IGN vía CartoCiudad — datos crudos de geocodificación."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

CANDIDATES_URL = "https://www.cartociudad.es/geocoder/api/geocoder/candidates"


class IGNExtractor:
    """Geocodificador oficial del IGN vía CartoCiudad con respuesta cruda."""

    def __init__(self) -> None:
        self.client = HttpClient(min_interval=1.0)

    def geocode(self, query: str) -> Optional[dict]:
        """Consulta CartoCiudad y devuelve el candidato crudo completo."""
        try:
            resp = self.client.get(
                CANDIDATES_URL,
                params={"q": query, "limit": 1},
            )
            data = resp.json()
            if not isinstance(data, list) or not data:
                logger.warning("[CartoCiudad] Sin resultados para '%s'.", query)
                return None

            c = data[0]
            result = {
                "query": query,
                "id": c.get("id", ""),
                "muniCode": c.get("muniCode", ""),
                "provinceCode": c.get("provinceCode", ""),
                "muni": c.get("muni", ""),
                "province": c.get("province", ""),
                "comunidadAutonoma": c.get("comunidadAutonoma", ""),
                "lat": c.get("lat"),
                "lng": c.get("lng"),
                "type": c.get("type", ""),
                "state": c.get("state", ""),
                "raw_json": json.dumps(c, ensure_ascii=False),
                "_meta.fecha_extraccion": datetime.now().isoformat(),
            }
            return result
        except Exception as exc:
            logger.warning("[CartoCiudad] Error '%s': %s", query, exc)
            return None
