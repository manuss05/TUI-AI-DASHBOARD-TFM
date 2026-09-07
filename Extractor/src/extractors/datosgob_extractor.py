"""Extractor de datos.gob.es — Catálogo Nacional de Datos Abiertos de España."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd

from config.settings import USER_AGENT
from src.schema import empty_dataframe
from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://datos.gob.es/apidata/catalog/dataset"
_HEADERS = {"Accept": "application/json", "User-Agent": USER_AGENT}


class DatosGobExtractor:
    """Descarga de metadatos de recursos turísticos sin transformaciones."""

    def __init__(self) -> None:
        self.client = HttpClient(base_headers=_HEADERS, min_interval=0.2)

    def get_theme_datasets(
        self,
        theme: str = "turismo",
        page_size: int = 50,
        max_pages: int | None = None,
        sort: str = "-modified",
    ) -> pd.DataFrame:
        """
        Descarga metadatos de conjuntos de datos del catálogo filtrados por temática
        usando la API Linked Data de datos.gob.es con soporte completo de paginación (_page, _pageSize, _sort).
        """
        clean_theme = (theme or "turismo").strip().lower()
        logger.info("[DatosGob] -> Consultando catalogo para tema '%s'...", clean_theme)
        url = f"{BASE_URL}/theme/{clean_theme}.json"

        all_rows: list[dict[str, Any]] = []
        page = 0
        fecha_extraccion = datetime.now().isoformat()

        while True:
            params = {"_page": page, "_pageSize": page_size, "_sort": sort}
            try:
                resp = self.client.get(url, params=params)
                data = resp.json()
            except Exception as exc:
                logger.warning("[DatosGob] [ERROR] Error en pagina %d para tema '%s': %s", page, clean_theme, exc)
                break

            result = data.get("result", {}) if isinstance(data, dict) else {}
            items = result.get("items", []) if isinstance(result, dict) else []

            if not items:
                logger.debug("[DatosGob] No se encontraron mas items en pagina %d.", page)
                break

            for item in items:
                all_rows.append({
                    "theme": clean_theme,
                    "about": item.get("_about", ""),
                    "title_raw": json.dumps(item.get("title", ""), ensure_ascii=False),
                    "description_raw": json.dumps(item.get("description", ""), ensure_ascii=False),
                    "publisher_raw": json.dumps(item.get("publisher", ""), ensure_ascii=False),
                    "distribution_raw": json.dumps(item.get("distribution", []), ensure_ascii=False),
                    "keywords_raw": json.dumps(item.get("keyword", []), ensure_ascii=False),
                    "modified": item.get("modified", ""),
                    "_meta.fecha_extraccion": fecha_extraccion,
                })

            logger.info("[DatosGob] [OK] Pagina %d descargada (%d items acumulados).", page, len(all_rows))
            page += 1

            if max_pages is not None and page >= max_pages:
                break

            # Terminar si no hay indicador de página siguiente o si devolvió menos que el pageSize
            if not result.get("next") or len(items) < page_size:
                break

        if not all_rows:
            return empty_dataframe("datosgob_catalogo")

        df = pd.DataFrame(all_rows)
        logger.info("[DatosGob] [OK] Total datasets recuperados para '%s': %d", clean_theme, len(df))
        return df

    def search_datasets(self, keyword: str = "turismo", limit: int = 100) -> pd.DataFrame:
        """Compatibilidad con llamadas previas: busca por tema con límite total de registros."""
        page_size = min(limit, 50) if limit > 0 else 50
        max_pages = (limit + page_size - 1) // page_size if limit > 0 else None
        clean_kw = (keyword or "turismo").strip().lower()
        theme = clean_kw if clean_kw in ["turismo", "sector-publico", "economia"] else "turismo"
        df = self.get_theme_datasets(theme=theme, page_size=page_size, max_pages=max_pages)
        if df.empty:
            return empty_dataframe("datosgob_catalogo")
        if limit > 0 and len(df) > limit:
            return df.iloc[:limit].reset_index(drop=True)
        return df


