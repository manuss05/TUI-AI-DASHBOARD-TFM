"""Extractor de AEMET OpenData — prediccion meteorologica diaria municipal."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

import pandas as pd
import requests

from config.settings import AEMET_API_KEY
from src.schema import TABLE_SCHEMAS, empty_dataframe
from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://opendata.aemet.es/opendata/api"


class AEMETExtractor:

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
        """Patron en 2 pasos: endpoint -> URL temporal en 'datos' -> payload JSON."""
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
        cod_ine_5 = str(cod_ine).zfill(5)
        payload = self._fetch_datos(f"/prediccion/especifica/municipio/diaria/{cod_ine_5}")
        if not payload or not isinstance(payload, list):
            return []

        rows: list[dict] = []
        fecha_extraccion = datetime.utcnow().isoformat()

        for item in payload:
            nombre_mun = item.get("nombre", "")
            provincia = item.get("provincia", "")
            for dia in item.get("prediccion", {}).get("dia", []):
                fecha_str = dia.get("fecha", "").split("T")[0] if "T" in dia.get("fecha", "") else dia.get("fecha", "")
                temp = dia.get("temperatura", {})
                sens = dia.get("sensTermica", {})
                hum = dia.get("humedadRelativa", {})

                prob_precip_list = dia.get("probPrecipitation", dia.get("probPrecipacion", dia.get("probPrecipitacion", [])))
                prob_val = None
                if isinstance(prob_precip_list, list):
                    for p in prob_precip_list:
                        if p.get("periodo") == "00-24" and p.get("value") is not None:
                            prob_val = p.get("value")
                            break
                        if p.get("value") is not None and prob_val is None:
                            prob_val = p.get("value")

                cielo_list = dia.get("estadoCielo", [])
                cielo_desc = ""
                if isinstance(cielo_list, list):
                    for c in cielo_list:
                        if c.get("periodo") == "00-24" and c.get("descripcion"):
                            cielo_desc = c["descripcion"]
                            break
                        if c.get("descripcion") and not cielo_desc:
                            cielo_desc = c["descripcion"]

                viento_list = dia.get("viento", [])
                viento_dir, viento_vel = "", None
                if isinstance(viento_list, list):
                    for v in viento_list:
                        if v.get("periodo") == "00-24" and (v.get("direccion") or v.get("velocidad") is not None):
                            viento_dir = v.get("direccion", "")
                            viento_vel = v.get("velocidad")
                            break
                        if (v.get("direccion") or v.get("velocidad") is not None) and not viento_dir:
                            viento_dir = v.get("direccion", "")
                            viento_vel = v.get("velocidad")

                rows.append({
                    "AEMET_Clima.cod_ine": cod_ine_5,
                    "AEMET_Clima.nombre_municipio": nombre_mun,
                    "AEMET_Clima.provincia": provincia,
                    "AEMET_Clima.fecha_prediccion": fecha_str,
                    "AEMET_Clima.temp_max": temp.get("maxima"),
                    "AEMET_Clima.temp_min": temp.get("minima"),
                    "AEMET_Clima.sens_termica_max": sens.get("maxima"),
                    "AEMET_Clima.sens_termica_min": sens.get("minima"),
                    "AEMET_Clima.humedad_max": hum.get("maxima"),
                    "AEMET_Clima.humedad_min": hum.get("minima"),
                    "AEMET_Clima.prob_precipitacion_pct": prob_val,
                    "AEMET_Clima.estado_cielo_desc": cielo_desc,
                    "AEMET_Clima.viento_dir": viento_dir,
                    "AEMET_Clima.viento_vel_kmh": viento_vel,
                    "AEMET_Clima.uv_max": dia.get("uvMax"),
                    "AEMET_Clima.fuente": "AEMET_OpenData",
                    "_meta.cod_ine_clave": cod_ine_5,
                    "_meta.nombre_municipio": nombre_mun,
                    "_meta.fecha_extraccion": fecha_extraccion,
                })
        return rows

    def get_predicciones_municipios(self, targets: list[dict]) -> pd.DataFrame:
        if not self.is_active:
            return empty_dataframe("clima_aemet")
        all_rows: list[dict] = []
        for t in targets:
            cod_ine = t.get("_meta.cod_ine_clave") or t.get("CartoCiudad.cod_ine") or t.get("cod_ine")
            if not cod_ine or str(cod_ine).startswith("PROV_"):
                continue
            try:
                all_rows.extend(self.get_prediccion_diaria(str(cod_ine)))
            except Exception as exc:
                logger.warning("[AEMET] Error INE %s: %s", cod_ine, exc)
        if not all_rows:
            return empty_dataframe("clima_aemet")
        df = pd.DataFrame(all_rows)
        for c in TABLE_SCHEMAS["clima_aemet"]:
            if c not in df.columns:
                df[c] = None
        return df[TABLE_SCHEMAS["clima_aemet"]]

    def close(self) -> None:
        if hasattr(self.client, "session") and self.client.session:
            self.client.session.close()
