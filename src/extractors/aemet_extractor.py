"""Extractor de AEMET OpenData — datos crudos de predicción meteorológica municipal."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

import pandas as pd
import requests

from config.settings import AEMET_API_KEY
from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://opendata.aemet.es/opendata/api"


class AEMETExtractor:
    """Extractor de predicciones de AEMET OpenData en formato crudo."""

    def __init__(self, api_key: str = AEMET_API_KEY) -> None:
        self.api_key = api_key.strip() if api_key else ""
        self.client = HttpClient(
            base_headers={"api_key": self.api_key, "Accept": "application/json"},
            min_interval=1.2,
        )

    @property
    def is_active(self) -> bool:
        return bool(self.api_key)

    def _fetch_datos(self, endpoint_path: str) -> Optional[Any]:
        """Patrón AEMET en 2 pasos: endpoint -> URL temporal en 'datos' -> payload JSON."""
        if not self.is_active:
            return None
        url = f"{BASE_URL}{endpoint_path}"
        resp = self.client.get(url, headers={"api_key": self.api_key})
        res_json = resp.json()
        if res_json.get("estado") != 200:
            return None
        datos_url = res_json.get("datos")
        if not datos_url:
            return None
        r_data = requests.get(datos_url, timeout=30)
        if r_data.status_code != 200:
            return None
        try:
            return r_data.json()
        except Exception:
            r_data.encoding = "ISO-8859-15"
            return json.loads(r_data.text)

    def get_prediccion_diaria(self, cod_ine: str) -> list[dict]:
        """Obtiene la predicción municipal diaria completa sin filtrar franjas ni subcampos."""
        cod_ine_5 = str(cod_ine).zfill(5)
        payload = self._fetch_datos(f"/prediccion/especifica/municipio/diaria/{cod_ine_5}")
        if not payload or not isinstance(payload, list):
            return []

        rows: list[dict] = []
        fecha_extraccion = datetime.utcnow().isoformat()

        for item in payload:
            nombre_mun = item.get("nombre", "")
            provincia = item.get("provincia", "")
            id_mun = item.get("id", cod_ine_5)
            elaborado = item.get("elaborado", "")

            prediccion = item.get("prediccion", {})
            dias = prediccion.get("dia", []) if isinstance(prediccion, dict) else []

            for dia in dias:
                rows.append({
                    "id_municipio": id_mun,
                    "nombre": nombre_mun,
                    "provincia": provincia,
                    "elaborado": elaborado,
                    "fecha": dia.get("fecha", ""),
                    "dia_raw_json": json.dumps(dia, ensure_ascii=False),
                    "_meta.fecha_extraccion": fecha_extraccion,
                })
        return rows

    def get_predicciones_municipios(self, targets: list[dict]) -> pd.DataFrame:
        if not self.is_active:
            return pd.DataFrame()
        all_rows: list[dict] = []
        for t in targets:
            cod_ine = t.get("cod_ine") or t.get("CartoCiudad.cod_ine") or t.get("COD")
            if not cod_ine:
                continue
            try:
                all_rows.extend(self.get_prediccion_diaria(str(cod_ine)))
            except Exception as exc:
                logger.warning("[AEMET] Error INE %s: %s", cod_ine, exc)
        return pd.DataFrame(all_rows)

    def close(self) -> None:
        if hasattr(self.client, "session") and self.client.session:
            self.client.session.close()
