"""Extractor de datos.gob.es — Catálogo Nacional de Datos Abiertos de España."""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import requests

from config.settings import USER_AGENT
from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://datos.gob.es/apidata/catalog/dataset.json"
_HEADERS = {"Accept": "application/json", "User-Agent": USER_AGENT}


class DatosGobExtractor:
    """Descarga de metadatos de recursos turísticos sin transformaciones."""

    def __init__(self) -> None:
        self.client = HttpClient()

    def search_datasets(self, keyword: str = "turismo", limit: int = 100) -> pd.DataFrame:
        logger.info("[DatosGob] ▶ Consultando catálogo para '%s'...", keyword)
        params = {"_pageSize": limit, "_sort": "-modified"}
        try:
            resp = requests.get(BASE_URL, params=params, headers=_HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("[DatosGob] ✗ Error: %s", exc)
            return pd.DataFrame()

        items = data.get("result", {}).get("items", []) if isinstance(data, dict) else []
        rows: list[dict] = []
        fecha_extraccion = datetime.utcnow().isoformat()

        for item in items:
            rows.append({
                "keyword_busqueda": keyword,
                "about": item.get("_about", ""),
                "title_raw": json.dumps(item.get("title", ""), ensure_ascii=False),
                "description_raw": json.dumps(item.get("description", ""), ensure_ascii=False),
                "publisher_raw": json.dumps(item.get("publisher", ""), ensure_ascii=False),
                "distribution_raw": json.dumps(item.get("distribution", []), ensure_ascii=False),
                "modified": item.get("modified", ""),
                "_meta.fecha_extraccion": fecha_extraccion,
            })

        return pd.DataFrame(rows)
