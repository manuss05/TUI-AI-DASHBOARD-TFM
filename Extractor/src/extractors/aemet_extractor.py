"""Extractor de AEMET OpenData — datos crudos de predicción meteorológica municipal."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

import pandas as pd
import requests

from config.settings import AEMET_API_KEY
from src.schema import empty_dataframe
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

    def get_estaciones(self) -> list[dict]:
        """Obtiene el inventario completo de estaciones meteorológicas."""
        payload = self._fetch_datos("/valores/climatologicos/inventarioestaciones/todasestaciones")
        if not payload or not isinstance(payload, list):
            return []
        return payload

    def get_clima_estacion(self, idema: str, anio_ini: str, anio_fin: str) -> list[dict]:
        """Obtiene la climatología mensual/anual para una estación en un rango de años."""
        path = f"/valores/climatologicos/mensualesanuales/datos/anioini/{anio_ini}/aniofin/{anio_fin}/estacion/{idema}"
        payload = self._fetch_datos(path)
        if not payload or not isinstance(payload, list):
            return []
        
        fecha_extraccion = datetime.now().isoformat()
        rows = []
        for item in payload:
            item["_meta.fecha_extraccion"] = fecha_extraccion
            rows.append(item)
        return rows

    def get_climatologias_provinciales(self, anio_ini: int, anio_fin: int) -> pd.DataFrame:
        """
        Obtiene climatologías para una estación representativa por provincia.
        Se priorizan aeropuertos u observatorios.
        """
        if not self.is_active:
            return empty_dataframe("clima_aemet")

        estaciones = self.get_estaciones()
        if not estaciones:
            logger.warning("[AEMET] No se pudo obtener el inventario de estaciones.")
            return empty_dataframe("clima_aemet")

        # Agrupar por provincia
        provs = {}
        for s in estaciones:
            prov = s.get("provincia", "DESCONOCIDA")
            provs.setdefault(prov, []).append(s)

        best_stations = []
        for prov, sts in provs.items():
            best = next((s for s in sts if "AEROPUERTO" in s.get("nombre", "").upper()), None)
            if not best:
                best = next((s for s in sts if "OBSERVATORIO" in s.get("nombre", "").upper()), None)
            if not best:
                best = sts[0]
            best_stations.append(best)

        logger.info(f"[AEMET] Seleccionadas {len(best_stations)} estaciones representativas.")

        all_rows = []
        for s in best_stations:
            idema = s.get("indicativo")
            prov = s.get("provincia")
            if not idema:
                continue
            try:
                clima = self.get_clima_estacion(idema, str(anio_ini), str(anio_fin))
                for c in clima:
                    c["estacion_nombre"] = s.get("nombre")
                    c["estacion_provincia"] = prov
                all_rows.extend(clima)
            except Exception as exc:
                logger.warning("[AEMET] Error estación %s: %s", idema, exc)

        if not all_rows:
            return empty_dataframe("clima_aemet")
        return pd.DataFrame(all_rows)

    def close(self) -> None:
        if hasattr(self.client, "session") and self.client.session:
            self.client.session.close()
