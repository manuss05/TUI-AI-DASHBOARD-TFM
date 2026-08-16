"""
Extractor de TripAdvisor Content API.

Requiere clave API (gratuita con cuota limitada).
Solicitar en: https://www.tripadvisor.com/developers

Si la clave no está configurada en .env (TRIPADVISOR_API_KEY),
el extractor se omite y registra un fallo de tipo "Omitido" en el reporter.

Convención de columnas de salida: TripAdvisor.*
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd

from config.settings import TRIPADVISOR_API_KEY
from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.content.tripadvisor.com/api/v1"


class TripAdvisorExtractor:
    """Extractor de POIs desde la Content API de TripAdvisor."""

    def __init__(self, api_key: str = TRIPADVISOR_API_KEY) -> None:
        self.api_key = api_key.strip() if api_key else ""
        self.client  = HttpClient()
        if not self.api_key:
            logger.warning(
                "[TripAdvisor] ⊘ TRIPADVISOR_API_KEY no configurada. "
                "Define la clave en .env para activar este extractor."
            )

    @property
    def is_active(self) -> bool:
        """True si la clave API está disponible."""
        return bool(self.api_key)

    def search_location(
        self, query: str, category: str = "attractions"
    ) -> list[dict]:
        params = {
            "key": self.api_key,
            "searchQuery": query,
            "category": category,
            "language": "es",
        }
        resp = self.client.get(f"{BASE_URL}/location/search", params=params)
        return resp.json().get("data", [])

    def get_location_details(self, location_id: str) -> dict:
        params = {
            "key": self.api_key,
            "language": "es",
            "currency": "EUR",
        }
        resp = self.client.get(
            f"{BASE_URL}/location/{location_id}/details", params=params
        )
        return resp.json()

    def get_pois_for_municipio(
        self,
        municipio: str,
        cod_ine: str,
        max_results: int = 10,
    ) -> pd.DataFrame:
        """
        Devuelve un DataFrame con los POIs de TripAdvisor del municipio.
        Columnas con prefijo TripAdvisor.*
        """
        logger.info(
            "[TripAdvisor] ▶ Buscando POIs para '%s' (cod_ine=%s)...",
            municipio, cod_ine,
        )
        rows = []
        for cat in ("attractions", "hotels", "restaurants"):
            try:
                locations = self.search_location(municipio, category=cat)
                for loc in locations[:max_results]:
                    details = self.get_location_details(loc["location_id"])
                    rows.append({
                        "_meta.cod_ine_clave":              cod_ine,
                        "TripAdvisor.location_id":          loc.get("location_id"),
                        "TripAdvisor.nombre_poi":           details.get("name"),
                        "TripAdvisor.categoria":            cat,
                        "TripAdvisor.rating":               details.get("rating"),
                        "TripAdvisor.num_reviews":          details.get("num_reviews"),
                        "TripAdvisor.latitud":              details.get("latitude"),
                        "TripAdvisor.longitud":             details.get("longitude"),
                        "TripAdvisor.fuente":               "TripAdvisor_ContentAPI",
                        "_meta.fecha_extraccion":           datetime.utcnow().isoformat(),
                    })
            except Exception as exc:
                logger.warning(
                    "[TripAdvisor] ✗ Error en categoría '%s' para '%s': %s",
                    cat, municipio, exc,
                )

        df = pd.DataFrame(rows)
        if not df.empty:
            logger.info(
                "[TripAdvisor] ✔ %s → %d POIs extraídos.",
                municipio, len(df),
            )
        return df
