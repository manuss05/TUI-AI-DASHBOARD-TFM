"""
Extractor de datos.gob.es — Catálogo Nacional de Datos Abiertos de España.

API pública sin clave: https://datos.gob.es/apidata/catalog/dataset.json
Localiza recursos descargables (CSV, XLSX, JSON) sobre turismo publicados por
ministerios, comunidades autónomas y ayuntamientos de España.

Convención de columnas de salida: DatosGob.*
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd
import requests

from src.utils.http_client import HttpClient
from src.utils.logger import get_logger
from config.settings import USER_AGENT

logger = get_logger(__name__)

BASE_URL = "https://datos.gob.es/apidata/catalog/dataset.json"
_HEADERS = {
    "Accept": "application/json",
    "User-Agent": USER_AGENT,
}


def _extract_text(field: any) -> str:
    """Extrae texto de estructuras literales simples o multilingües de datos.gob.es."""
    if isinstance(field, str):
        return field
    elif isinstance(field, dict):
        return field.get("_value", "")
    elif isinstance(field, list) and len(field) > 0:
        for item in field:
            if isinstance(item, dict) and item.get("_lang") == "es":
                return item.get("_value", "")
        return _extract_text(field[0])
    return ""


class DatosGobExtractor:
    """Buscador de datasets turísticos en el catálogo nacional datos.gob.es."""

    def __init__(self) -> None:
        self.client = HttpClient()

    def search_datasets(
        self, keyword: str = "turismo", limit: int = 100
    ) -> pd.DataFrame:
        """
        Descarga los datasets más recientes del catálogo nacional y filtra por keyword.

        Columnas de salida: DatosGob.*
        """
        logger.info(
            "[DatosGob] ▶ Buscando datasets relacionados con '%s' en el catálogo nacional...",
            keyword,
        )
        params = {"_pageSize": limit, "_sort": "-modified"}
        try:
            resp = requests.get(BASE_URL, params=params, headers=_HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("[DatosGob] ✗ Error consultando el catálogo: %s", exc)
            return pd.DataFrame()

        items = data.get("result", {}).get("items", []) if isinstance(data, dict) else []
        rows = []
        kw_lower = keyword.lower()

        for item in items:
            titulo = _extract_text(item.get("title"))
            descripcion = _extract_text(item.get("description"))
            publicador = _extract_text(item.get("publisher"))

            if kw_lower in titulo.lower() or kw_lower in descripcion.lower():
                distributions = item.get("distribution", [])
                if isinstance(distributions, dict):
                    distributions = [distributions]

                for dist in distributions:
                    if isinstance(dist, dict):
                        url_rec = dist.get("accessURL") or dist.get("downloadURL")
                        formato = dist.get("format")
                        if isinstance(formato, dict):
                            formato = formato.get("_value")

                        rows.append({
                            "DatosGob.titulo_dataset": titulo,
                            "DatosGob.descripcion":    descripcion,
                            "DatosGob.url_recurso":    url_rec,
                            "DatosGob.formato":        formato,
                            "DatosGob.publicador":     publicador,
                            "DatosGob.fuente":         "datos.gob.es",
                            "_meta.fecha_extraccion":  datetime.utcnow().isoformat(),
                        })

        df = pd.DataFrame(rows)
        logger.info(
            "[DatosGob] ✔ '%s' → %d recursos encontrados en el catálogo.",
            keyword, len(df),
        )
        return df
