"""
Extractor del INE (Instituto Nacional de Estadística) vía API Tempus3.

API pública, gratuita, sin clave.
Documentación: https://www.ine.es/dyngs/DataLab/manual.html?cid=45
Base URL:       https://servicios.ine.es/wstempus/js/ES/

Tablas utilizadas para cobertura completa de España:
  - Maestro Provincias (Tabla 2852):
    Cifras oficiales de población para las 52 provincias y ciudades autónomas.
  - Maestro Municipios (Tabla 29005):
    Cifras oficiales del padrón para los 8.138 municipios de España.
  - EOH por Punto Turístico / Localidad (Tabla 2078):
    Viajeros y pernoctaciones mensuales para las 113 localidades turísticas clave.
  - EOH por Provincia y CCAA (Tabla 2074):
    Viajeros y pernoctaciones mensuales para todas las provincias y CCAA de España.

Convención de columnas de salida:
  - INE_Pob_PROV.*  → Padrón / Población por provincia
  - INE_Pob_MUN.*   → Padrón / Población por municipio (8.138 municipios)
  - INE_EOH_MUN.*   → Flujos turísticos hoteleros por punto turístico
  - INE_EOH_PROV.*  → Flujos turísticos hoteleros por provincia y CCAA
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

import pandas as pd

from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://servicios.ine.es/wstempus/js/ES"

# IDs de tabla verificados en el INE Tempus3
_TABLA_POB_PROVINCIAS   = 2852   # Población oficial por provincia (52 provincias)
_TABLA_POB_MUNICIPIOS   = 29005  # Cifras oficiales del padrón por municipio (8.138 municipios)
_TABLA_EOH_MUN_DEMANDA  = 2078   # Viajeros y pernoctaciones por punto turístico (113 puntos)
_TABLA_EOH_PROV_DEMANDA = 2074   # Viajeros y pernoctaciones por provincia y CCAA (todas las provs)


def _parse_serie_nombre(nombre: str) -> dict:
    """
    Descompone el nombre de serie del INE en campos estructurados.
    """
    parts = [p.strip().rstrip(".") for p in nombre.split(".") if p.strip()]
    return {
        "parte_0": parts[0] if len(parts) > 0 else "",
        "parte_1": parts[1] if len(parts) > 1 else "",
        "parte_2": parts[2] if len(parts) > 2 else "",
        "parte_3": parts[3] if len(parts) > 3 else "",
        "nombre_completo": nombre,
    }


def _descarga_tabla(
    client: HttpClient, table_id: int, n_ultimos: int
) -> list[dict]:
    """Descarga raw de una tabla Tempus3 y devuelve la lista de series."""
    url = f"{BASE_URL}/DATOS_TABLA/{table_id}"
    params = {"nult": n_ultimos}
    try:
        resp = client.get(url, params=params)
        data = resp.json()
        logger.info(
            "[INE] ✔ Tabla %s descargada: %d series.", table_id, len(data)
        )
        return data
    except Exception as exc:
        logger.error(
            "[INE] ✗ Error descargando tabla %s: %s", table_id, exc
        )
        return []


class INEExtractor:
    """Extractor oficial del Instituto Nacional de Estadística (INE)."""

    def __init__(self) -> None:
        self.client = HttpClient()

    # ------------------------------------------------------------------
    # Maestro y Censo de Provincias de España (Tabla 2852)
    # ------------------------------------------------------------------
    def get_maestro_provincias(self, n_ultimos: int = 1) -> pd.DataFrame:
        """
        Descarga el censo/población oficial de las 52 provincias y
        ciudades autónomas de España.

        Columnas de salida: INE_Pob_PROV.*
        """
        logger.info(
            "[INE_Pob_PROV] ▶ Descargando cifras oficiales de población por provincia (Tabla %s)...",
            _TABLA_POB_PROVINCIAS,
        )
        series = _descarga_tabla(self.client, _TABLA_POB_PROVINCIAS, n_ultimos)
        if not series:
            return pd.DataFrame()

        rows = []
        for s in series:
            parsed = _parse_serie_nombre(s.get("Nombre", ""))
            provincia = parsed["parte_0"]
            sexo      = parsed["parte_1"]
            concepto  = parsed["parte_2"]

            # Solo tomar el total de población (habitantes totales)
            if sexo.lower() == "total" and "habitantes" in concepto.lower() and provincia != "Total Nacional":
                for d in s.get("Data", []):
                    rows.append({
                        "INE_Pob_PROV.provincia":              provincia,
                        "INE_Pob_PROV.poblacion_total":        d.get("Valor"),
                        "INE_Pob_PROV.anio":                   d.get("Anyo"),
                        "INE_Pob_PROV.cod_serie":              s.get("COD", ""),
                        "INE_Pob_PROV.nombre_serie_completo":  s.get("Nombre", ""),
                        "INE_Pob_PROV.fuente":                 "INE_Padron_Tabla_2852",
                        "_meta.fecha_extraccion":              datetime.utcnow().isoformat(),
                    })

        df = pd.DataFrame(rows)
        logger.info(
            "[INE_Pob_PROV] ✔ %d provincias/ciudades autónomas procesadas correctamente.",
            len(df),
        )
        return df

    # ------------------------------------------------------------------
    # Maestro y Censo de Todos los Municipios de España (Tabla 29005)
    # ------------------------------------------------------------------
    def get_maestro_municipios(self, n_ultimos: int = 1) -> pd.DataFrame:
        """
        Descarga el censo/padrón oficial de todos los 8.138 municipios de España.

        Columnas de salida: INE_Pob_MUN.*
        """
        logger.info(
            "[INE_Pob_MUN] ▶ Descargando cifras oficiales del padrón de todos los municipios de España (Tabla %s)...",
            _TABLA_POB_MUNICIPIOS,
        )
        series = _descarga_tabla(self.client, _TABLA_POB_MUNICIPIOS, n_ultimos)
        if not series:
            return pd.DataFrame()

        rows = []
        for s in series:
            parsed = _parse_serie_nombre(s.get("Nombre", ""))
            municipio = parsed["parte_0"]
            sexo      = parsed["parte_1"]
            concepto  = parsed["parte_2"]

            # Filtrar por Total Habitantes
            if sexo.lower() == "total" and "habitantes" in concepto.lower():
                for d in s.get("Data", []):
                    rows.append({
                        "INE_Pob_MUN.nombre_municipio":        municipio,
                        "INE_Pob_MUN.poblacion_oficial":       d.get("Valor"),
                        "INE_Pob_MUN.anio":                    d.get("Anyo"),
                        "INE_Pob_MUN.cod_serie":               s.get("COD", ""),
                        "INE_Pob_MUN.nombre_serie_completo":   s.get("Nombre", ""),
                        "INE_Pob_MUN.fuente":                  "INE_Padron_Tabla_29005",
                        "_meta.fecha_extraccion":              datetime.utcnow().isoformat(),
                    })

        df = pd.DataFrame(rows)
        logger.info(
            "[INE_Pob_MUN] ✔ %d municipios oficiales de España extraídos.",
            len(df),
        )
        return df

    # ------------------------------------------------------------------
    # EOH — Flujos Turísticos por Punto Turístico / Localidad (Tabla 2078)
    # ------------------------------------------------------------------
    def get_eoh_municipios(self, n_ultimos: int = 12) -> pd.DataFrame:
        """
        Descarga la Encuesta de Ocupación Hotelera desagregada por
        punto turístico (113 localidades turísticas de España).

        Columnas de salida: INE_EOH_MUN.*
        """
        logger.info(
            "[INE_EOH_MUN] ▶ Descargando viajeros/pernoctaciones por localidad turística (últimos %d períodos)...",
            n_ultimos,
        )
        series = _descarga_tabla(self.client, _TABLA_EOH_MUN_DEMANDA, n_ultimos)
        if not series:
            return pd.DataFrame()

        rows = []
        for s in series:
            parsed = _parse_serie_nombre(s.get("Nombre", ""))
            if parsed["parte_0"].lower() == "nacional":
                localidad = parsed["parte_2"]
                residencia = parsed["parte_3"]
            else:
                localidad = parsed["parte_0"]
                residencia = parsed["parte_2"] if len(parsed["parte_2"]) > 0 else parsed["parte_3"]

            indicador = parsed["parte_1"].lower()

            for d in s.get("Data", []):
                rows.append({
                    "INE_EOH_MUN.punto_turistico":          localidad,
                    "INE_EOH_MUN.indicador":                indicador,
                    "INE_EOH_MUN.residencia":               residencia,
                    "INE_EOH_MUN.nombre_serie_completo":    s.get("Nombre", ""),
                    "INE_EOH_MUN.cod_serie":                s.get("COD", ""),
                    "INE_EOH_MUN.anio":                     d.get("Anyo"),
                    "INE_EOH_MUN.periodo":                  d.get("NombrePeriodo", ""),
                    "INE_EOH_MUN.valor":                    d.get("Valor"),
                    "INE_EOH_MUN.fuente":                   "INE_EOH_MUN",
                    "INE_EOH_MUN.tabla_id":                 _TABLA_EOH_MUN_DEMANDA,
                    "_meta.fecha_extraccion":               datetime.utcnow().isoformat(),
                })

        df = pd.DataFrame(rows)
        n_localidades = df["INE_EOH_MUN.punto_turistico"].nunique()
        logger.info(
            "[INE_EOH_MUN] ✔ %d filas | %d localidades turísticas | Tabla ID %s",
            len(df), n_localidades, _TABLA_EOH_MUN_DEMANDA,
        )
        return df

    # ------------------------------------------------------------------
    # EOH — Flujos Turísticos por Provincia y CCAA (Tabla 2074)
    # ------------------------------------------------------------------
    def get_eoh_provincias(self, n_ultimos: int = 12) -> pd.DataFrame:
        """
        Descarga la Encuesta de Ocupación Hotelera a nivel de
        comunidad autónoma y provincia para toda España (52 provincias/ciudades autónomas + 17 CCAA).

        Columnas de salida: INE_EOH_PROV.*
        """
        logger.info(
            "[INE_EOH_PROV] ▶ Descargando viajeros/pernoctaciones para todas las provincias y CCAA de España (últimos %d períodos)...",
            n_ultimos,
        )
        series = _descarga_tabla(self.client, _TABLA_EOH_PROV_DEMANDA, n_ultimos)
        if not series:
            return pd.DataFrame()

        rows = []
        for s in series:
            parsed = _parse_serie_nombre(s.get("Nombre", ""))
            ambito     = parsed["parte_0"]
            indicador  = parsed["parte_1"]
            residencia = parsed["parte_2"]

            for d in s.get("Data", []):
                rows.append({
                    "INE_EOH_PROV.ambito":                  ambito,
                    "INE_EOH_PROV.indicador":               indicador,
                    "INE_EOH_PROV.residencia":              residencia,
                    "INE_EOH_PROV.nombre_serie_completo":   s.get("Nombre", ""),
                    "INE_EOH_PROV.cod_serie":               s.get("COD", ""),
                    "INE_EOH_PROV.anio":                    d.get("Anyo"),
                    "INE_EOH_PROV.periodo":                 d.get("NombrePeriodo", ""),
                    "INE_EOH_PROV.valor":                   d.get("Valor"),
                    "INE_EOH_PROV.fuente":                  "INE_EOH_PROV",
                    "INE_EOH_PROV.tabla_id":                _TABLA_EOH_PROV_DEMANDA,
                    "_meta.fecha_extraccion":               datetime.utcnow().isoformat(),
                })

        df = pd.DataFrame(rows)
        n_ambitos = df["INE_EOH_PROV.ambito"].nunique()
        logger.info(
            "[INE_EOH_PROV] ✔ %d filas | %d ámbitos (todas las provincias y CCAA) | Tabla ID %s",
            len(df), n_ambitos, _TABLA_EOH_PROV_DEMANDA,
        )
        return df

    # ------------------------------------------------------------------
    # Descubrimiento de tablas (para análisis exploratorio en TFM)
    # ------------------------------------------------------------------
    def search_operations(self, keyword: str) -> pd.DataFrame:
        resp = self.client.get(f"{BASE_URL}/OPERACIONES_DISPONIBLES")
        df = pd.DataFrame(resp.json())
        if "Nombre" in df.columns:
            mask = df["Nombre"].str.contains(keyword, case=False, na=False)
            return df[mask][["Id", "Cod_IOE", "Nombre"]]
        return df
