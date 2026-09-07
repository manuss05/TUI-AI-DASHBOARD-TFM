"""
Extractor del INE (Instituto Nacional de Estadística) vía API Tempus3.
Modo dato crudo: extrae todos los campos devueltos por la API sin transformaciones.

Documentación: https://www.ine.es/dyngs/DataLab/manual.html?cid=45
Base URL:       https://servicios.ine.es/wstempus/js/ES/
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

import pandas as pd

from src.schema import empty_dataframe
from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://servicios.ine.es/wstempus/js/ES"

# IDs de tabla en INE Tempus3
_TABLA_POB_PROVINCIAS = 2852     # Población oficial por provincia
_TABLA_POB_MUNICIPIOS = 29005    # Cifras oficiales del padrón por municipio
_TABLA_EOH_MUN_DEMANDA = 2078    # EOH por punto turístico
_TABLA_EOH_PROV_DEMANDA = 2074   # EOH por provincia y CCAA
_TABLA_ADR_PROV = 2059           # Indicadores de Rentabilidad: ADR por CCAA y provincia (IRSH)
_TABLA_REVPAR_PROV = 2057        # Indicadores de Rentabilidad: RevPAR por CCAA y provincia (IRSH)
_TABLA_RENTABILIDAD_EOH = 2066   # Indicadores de ocupación/rentabilidad hotelera
_TABLA_EGATUR_CCAA = 10839       # Gasto de los turistas internacionales por CCAA de destino (EGATUR)
_TABLA_EGATUR_ACCESO = 10835     # Gasto de turistas internacionales por vía de acceso (EGATUR)


def _descarga_tabla(
    client: HttpClient, table_id: int, n_ultimos: int
) -> list[dict]:
    """
    Descarga raw de una tabla Tempus3 con metadatos completos (tip=AM).
    tip=AM garantiza la inclusión de Fecha (ISO), T3_Periodo (Mxx), T3_TipoDato y MetaData.
    """
    url = f"{BASE_URL}/DATOS_TABLA/{table_id}"
    params = {"nult": n_ultimos, "tip": "AM"}
    try:
        resp = client.get(url, params=params)
        data = resp.json()
        logger.info(
            "[INE] [OK] Tabla %s descargada: %d series.", table_id, len(data)
        )
        return data if isinstance(data, list) else []
    except Exception as exc:
        logger.error(
            "[INE] [ERROR] Error descargando tabla %s: %s", table_id, exc
        )
        return []


def _extract_series_data(
    series: list[dict], table_id: int, table_schema_key: str = "INE_provincias"
) -> pd.DataFrame:
    """Extrae todas las series y observaciones asociadas en formato tabular crudo."""
    rows: list[dict] = []
    fecha_extraccion = datetime.now().isoformat()

    for s in series:
        if not isinstance(s, dict):
            continue
        cod = s.get("COD", "")
        nombre = s.get("Nombre", "")
        unidad = s.get("T3_Unidad", "")
        escala = s.get("T3_Escala", "")
        meta_json = json.dumps(s.get("MetaData", []), ensure_ascii=False)

        data_list = s.get("Data") or []
        if isinstance(data_list, list):
            for d in data_list:
                if not isinstance(d, dict):
                    continue
                rows.append({
                    "COD": cod,
                    "Nombre": nombre,
                    "T3_Unidad": unidad,
                    "T3_Escala": escala,
                    "Fecha": d.get("Fecha", ""),
                    "T3_Periodo": d.get("T3_Periodo", ""),
                    "T3_TipoDato": d.get("T3_TipoDato", ""),
                    "Anyo": d.get("Anyo"),
                    "Valor": d.get("Valor"),
                    "MetaData_json": meta_json,
                    "tabla_id": table_id,
                    "_meta.fecha_extraccion": fecha_extraccion,
                })

    if not rows:
        return empty_dataframe(table_schema_key)
    return pd.DataFrame(rows)


class INEExtractor:
    """Extractor oficial del Instituto Nacional de Estadística (INE) en formato crudo."""

    def __init__(self) -> None:
        self.client = HttpClient()

    def get_maestro_provincias(self, n_ultimos: int = 1) -> pd.DataFrame:
        """Descarga cruda de la población oficial por provincia (Tabla 2852)."""
        logger.info("[INE_Pob_PROV] -> Descargando datos crudos Tabla %s...", _TABLA_POB_PROVINCIAS)
        series = _descarga_tabla(self.client, _TABLA_POB_PROVINCIAS, n_ultimos)
        if not series:
            return empty_dataframe("INE_provincias")
        return _extract_series_data(series, _TABLA_POB_PROVINCIAS, "INE_provincias")

    def get_maestro_municipios(self, n_ultimos: int = 1) -> pd.DataFrame:
        """Descarga cruda del padrón oficial municipal (Tabla 29005)."""
        logger.info("[INE_Pob_MUN] -> Descargando datos crudos Tabla %s...", _TABLA_POB_MUNICIPIOS)
        series = _descarga_tabla(self.client, _TABLA_POB_MUNICIPIOS, n_ultimos)
        if not series:
            return empty_dataframe("municipios_espana")
        return _extract_series_data(series, _TABLA_POB_MUNICIPIOS, "municipios_espana")

    def get_eoh_municipios(self, n_ultimos: int = 12) -> pd.DataFrame:
        """Descarga cruda de la EOH por punto turístico (Tabla 2078)."""
        logger.info("[INE_EOH_MUN] -> Descargando datos crudos EOH Localidades (Tabla %s)...", _TABLA_EOH_MUN_DEMANDA)
        series = _descarga_tabla(self.client, _TABLA_EOH_MUN_DEMANDA, n_ultimos)
        if not series:
            return empty_dataframe("flujo_ine_localidad")
        return _extract_series_data(series, _TABLA_EOH_MUN_DEMANDA, "flujo_ine_localidad")

    def get_eoh_provincias(self, n_ultimos: int = 12) -> pd.DataFrame:
        """Descarga cruda de la EOH por provincia y CCAA (Tabla 2074)."""
        logger.info("[INE_EOH_PROV] -> Descargando datos crudos EOH Provincias/CCAA (Tabla %s)...", _TABLA_EOH_PROV_DEMANDA)
        series = _descarga_tabla(self.client, _TABLA_EOH_PROV_DEMANDA, n_ultimos)
        if not series:
            return empty_dataframe("flujo_ine_provincia")
        return _extract_series_data(series, _TABLA_EOH_PROV_DEMANDA, "flujo_ine_provincia")

    def get_rentabilidad_H(
        self, n_ultimos: int = 12, tables: list[int] | None = None
    ) -> pd.DataFrame:
        """
        Descarga cruda de indicadores de rentabilidad hotelera (ADR y RevPAR).
        Por defecto descarga Tabla 2059 (ADR) y Tabla 2057 (RevPAR) por CCAA y provincias.
        Soporta además la consulta de tablas adicionales como Tabla 2066.
        """
        target_tables = tables or [_TABLA_ADR_PROV, _TABLA_REVPAR_PROV]
        logger.info(
            "[INE_Rentabilidad] -> Descargando indicadores de rentabilidad hotelera (Tablas: %s)...",
            target_tables,
        )
        frames: list[pd.DataFrame] = []
        for t_id in target_tables:
            series = _descarga_tabla(self.client, t_id, n_ultimos)
            if series:
                df = _extract_series_data(series, t_id, "rentabilidad_H")
                if not df.empty:
                    frames.append(df)
        if not frames:
            return empty_dataframe("rentabilidad_H")
        return pd.concat(frames, ignore_index=True)

    def get_gasto_turistico(
        self, n_ultimos: int = 12, tables: list[int] | None = None
    ) -> pd.DataFrame:
        """
        Descarga cruda de gasto turístico (EGATUR) al nivel geográfico más granular disponible.
        Por defecto descarga Tabla 10839 (Gasto según CCAA de destino) y Tabla 10835 (por vía de acceso).
        """
        target_tables = tables or [_TABLA_EGATUR_CCAA, _TABLA_EGATUR_ACCESO]
        logger.info(
            "[INE_EGATUR] -> Descargando datos crudos de gasto turístico (Tablas: %s)...",
            target_tables,
        )
        frames: list[pd.DataFrame] = []
        for t_id in target_tables:
            series = _descarga_tabla(self.client, t_id, n_ultimos)
            if series:
                df = _extract_series_data(series, t_id, "gasto_turistico")
                if not df.empty:
                    frames.append(df)
        if not frames:
            return empty_dataframe("gasto_turistico")
        return pd.concat(frames, ignore_index=True)


    def search_operations(self, keyword: str) -> pd.DataFrame:
        resp = self.client.get(f"{BASE_URL}/OPERACIONES_DISPONIBLES")
        df = pd.DataFrame(resp.json())
        if "Nombre" in df.columns:
            mask = df["Nombre"].str.contains(keyword, case=False, na=False)
            return df[mask]
        return df

