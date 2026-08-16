"""
Extractor de TripAdvisor Content API.

Es una API OFICIAL y real, pero de acceso restringido: necesitas
solicitar una clave en https://www.tripadvisor.com/developers
(tiene un tier gratuito con cuota limitada de llamadas/mes, suficiente
para un TFM si se usa con moderación y cacheando resultados).

Condiciones de uso relevantes para un TFM (revísalas en el portal antes
de publicar el dataset): TripAdvisor limita cuánto tiempo puedes
almacenar/cachear los datos y cómo puedes mostrarlos. Guarda solo lo que
necesites (rating agregado, nº de reseñas, categoría) y evita republicar
el texto completo de las reseñas.
"""
from datetime import datetime
import pandas as pd
from config.settings import TRIPADVISOR_API_KEY
from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://api.content.tripadvisor.com/api/v1"


class TripAdvisorExtractor:
    def __init__(self, api_key: str = TRIPADVISOR_API_KEY):
        if not api_key:
            logger.warning("TRIPADVISOR_API_KEY no configurada: este extractor no funcionará hasta que la definas en .env")
        self.api_key = api_key
        self.client = HttpClient()

    def search_location(self, query: str, category: str = "attractions") -> list[dict]:
        params = {"key": self.api_key, "searchQuery": query, "category": category, "language": "es"}
        resp = self.client.get(f"{BASE_URL}/location/search", params=params)
        return resp.json().get("data", [])

    def get_location_details(self, location_id: str) -> dict:
        params = {"key": self.api_key, "language": "es", "currency": "EUR"}
        resp = self.client.get(f"{BASE_URL}/location/{location_id}/details", params=params)
        return resp.json()

    def get_pois_for_municipio(self, municipio: str, cod_ine: str, max_results: int = 10) -> pd.DataFrame:
        rows = []
        for cat in ["attractions", "hotels", "restaurants"]:
            for loc in self.search_location(municipio, category=cat)[:max_results]:
                details = self.get_location_details(loc["location_id"])
                rows.append({
                    "cod_ine": cod_ine,
                    "location_id_tripadvisor": loc.get("location_id"),
                    "nombre": details.get("name"),
                    "categoria": cat,
                    "rating": details.get("rating"),
                    "num_reviews": details.get("num_reviews"),
                    "latitud": details.get("latitude"),
                    "longitud": details.get("longitude"),
                    "fuente": "TripAdvisor-ContentAPI",
                    "fecha_extraccion": datetime.utcnow().isoformat(),
                })
        return pd.DataFrame(rows)
