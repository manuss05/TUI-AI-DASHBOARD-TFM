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

from config.settings import PROVINCIAS_ESPANA

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
_TABLA_EOH_OFERTA_PROV = 2066    # EOH: Establecimientos, plazas, ocupación y personal por provincias
_TABLA_RURAL_OFERTA_PROV = 2070  # Turismo Rural: Establecimientos, plazas, ocupación por provincias
_TABLA_RURAL_DEMANDA_PROV = 49380  # Turismo Rural: Viajeros y pernoctaciones por provincias

# Mapeo de códigos de "Concepto turístico" → nombre limpio de columna
_CONCEPTO_OFERTA_MAP: dict[str, str] = {
    "1": "establecimientos_abiertos",
    "2": "plazas_estimadas",
    "3": "parcelas_estimadas",
    "4": "grado_ocupacion_plazas",
    "5": "grado_ocupacion_finsemana",
    "6": "grado_ocupacion_habitaciones",
    "7": "grado_ocupacion_parcelas",
    "8": "personal_empleado",
    "D": "estancia_media",
}

_CONCEPTO_DEMANDA_MAP: dict[str, str] = {
    "A": "pernoctaciones",
    "B": "viajeros",
    "C": "pernoctaciones",  # En tabla 49380 (Rural) pernoctaciones es C
}


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


def _clean_provincial_data(
    df_raw: pd.DataFrame,
    concepto_map: dict[str, str],
    schema_key: str,
    require_total_origen: bool = False,
) -> pd.DataFrame:
    """
    Transforma datos crudos Tempus3 en formato limpio pivotado por provincia.

    Parsea ``MetaData_json`` para extraer ``COD_PROV`` (oficial INE, 2 dígitos) y
    el concepto turístico, filtra solo registros provinciales (descarta CCAA y
    Total Nacional) y pivota las métricas como columnas.

    Parameters
    ----------
    df_raw : DataFrame crudo (salida de ``_extract_series_data``).
    concepto_map : Diccionario ``{codigo_concepto: nombre_columna}``.
    schema_key : Clave del esquema en ``TABLE_SCHEMAS`` (para fallback vacío).
    require_total_origen : Si ``True``, filtra para retener únicamente la
        categoría "Total" de residencia/origen (tablas de demanda).
    """
    if df_raw.empty:
        return empty_dataframe(schema_key)

    prov_names: dict[str, str] = {
        p["cod_prov"]: p["nombre"] for p in PROVINCIAS_ESPANA
    }
    fecha_extraccion = datetime.now().isoformat()
    records: list[dict] = []

    for _, row in df_raw.iterrows():
        meta_raw = row.get("MetaData_json")
        meta: list[dict] = []
        if isinstance(meta_raw, str) and meta_raw.strip():
            try:
                meta = json.loads(meta_raw)
            except Exception:
                continue
        if not meta:
            continue

        cod_prov: Optional[str] = None
        concepto_code: Optional[str] = None
        is_dato = False
        is_total_categoria = True
        is_total_origen = True
        has_categoria_var = False
        has_origen_var = False

        for m in meta:
            v_name = m.get("T3_Variable", "")
            c_name = m.get("Nombre", "")
            c_code = str(m.get("Codigo", "")).strip()

            if v_name == "Provincias":
                if c_code and c_code != "00":
                    cod_prov = c_code.zfill(2)
            elif v_name == "Comunidades y Ciudades Autónomas":
                _ccaa_uniprov = {
                    "03": "33",  # Asturias
                    "04": "07",  # Illes Balears
                    "06": "39",  # Cantabria
                    "13": "28",  # Madrid
                    "14": "30",  # Murcia
                    "15": "31",  # Navarra
                    "17": "26",  # La Rioja
                    "18": "51",  # Ceuta
                    "19": "52",  # Melilla
                }
                if c_code in _ccaa_uniprov:
                    cod_prov = _ccaa_uniprov[c_code]
                elif c_name == "Ceuta":
                    cod_prov = "51"
                elif c_name == "Melilla":
                    cod_prov = "52"
                # Otras CCAA pluriprovinciales (Andalucía, etc.) -> None -> se descartan para no duplicar
            elif "Concepto" in v_name:
                concepto_code = c_code
            elif "Tipo de dato" in v_name:
                is_dato = c_code == "0" or "Dato" in c_name
            elif "CATEGORIA" in v_name.upper():
                has_categoria_var = True
                is_total_categoria = "Total" in c_name or c_code in ("", "0")
            elif "RESIDENCIA" in v_name.upper() or "ORIGEN" in v_name.upper():
                has_origen_var = True
                is_total_origen = c_name == "Total" or c_code in ("0", "")

        # Filtros
        if not cod_prov or not is_dato:
            continue
        if has_categoria_var and not is_total_categoria:
            continue
        if require_total_origen and has_origen_var and not is_total_origen:
            continue
        if concepto_code is None:
            continue

        col_name = concepto_map.get(concepto_code)
        if col_name is None:
            continue

        val = row.get("Valor")
        if pd.isna(val):
            continue

        records.append({
            "COD_PROV": cod_prov,
            "PROVINCIA": prov_names.get(cod_prov, ""),
            "Anyo": row.get("Anyo"),
            "Periodo": str(row.get("T3_Periodo", "")).strip(),
            "metrica": col_name,
            "Valor": float(val),
        })

    if not records:
        return empty_dataframe(schema_key)

    df_clean = pd.DataFrame(records)

    # Pivotar: cada métrica se convierte en una columna
    df_pivot = df_clean.pivot_table(
        index=["COD_PROV", "PROVINCIA", "Anyo", "Periodo"],
        columns="metrica",
        values="Valor",
        aggfunc="first",
    ).reset_index()

    df_pivot.columns.name = None
    df_pivot["_meta.fecha_extraccion"] = fecha_extraccion
    df_pivot = df_pivot.sort_values(
        ["COD_PROV", "Anyo", "Periodo"]
    ).reset_index(drop=True)

    logger.info(
        "[INE] [OK] Limpieza provincial (%s): %d filas, %d provincias.",
        schema_key, len(df_pivot), df_pivot["COD_PROV"].nunique(),
    )
    return df_pivot


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

    # ---------- Nuevos extractores de oferta y demanda provincial ----------

    def get_eoh_oferta_provincias(self, n_ultimos: int = 24) -> pd.DataFrame:
        """
        Descarga y limpia la oferta hotelera por provincias (Tabla 2065).

        CSV resultante con columnas: COD_PROV, PROVINCIA, Anyo, Periodo,
        establecimientos_abiertos, plazas_estimadas, grado_ocupacion_plazas,
        grado_ocupacion_habitaciones, grado_ocupacion_finsemana,
        personal_empleado, estancia_media.
        """
        logger.info(
            "[INE_EOH_OFERTA] -> Descargando Tabla %s (n_ultimos=%d)...",
            _TABLA_EOH_OFERTA_PROV, n_ultimos,
        )
        series = _descarga_tabla(self.client, _TABLA_EOH_OFERTA_PROV, n_ultimos)
        if not series:
            return empty_dataframe("eoh_oferta_provincias")
        df_raw = _extract_series_data(
            series, _TABLA_EOH_OFERTA_PROV, "eoh_oferta_provincias"
        )
        return _clean_provincial_data(
            df_raw, _CONCEPTO_OFERTA_MAP, "eoh_oferta_provincias"
        )

    def get_rural_oferta_provincias(self, n_ultimos: int = 24) -> pd.DataFrame:
        """
        Descarga y limpia la oferta de turismo rural por provincias (Tabla 2070).

        CSV resultante con columnas: COD_PROV, PROVINCIA, Anyo, Periodo,
        establecimientos_abiertos, plazas_estimadas, grado_ocupacion_plazas,
        grado_ocupacion_habitaciones, grado_ocupacion_finsemana,
        personal_empleado.
        """
        logger.info(
            "[INE_RURAL_OFERTA] -> Descargando Tabla %s (n_ultimos=%d)...",
            _TABLA_RURAL_OFERTA_PROV, n_ultimos,
        )
        series = _descarga_tabla(self.client, _TABLA_RURAL_OFERTA_PROV, n_ultimos)
        if not series:
            return empty_dataframe("rural_oferta_provincias")
        df_raw = _extract_series_data(
            series, _TABLA_RURAL_OFERTA_PROV, "rural_oferta_provincias"
        )
        return _clean_provincial_data(
            df_raw, _CONCEPTO_OFERTA_MAP, "rural_oferta_provincias"
        )

    def get_rural_demanda_provincias(self, n_ultimos: int = 24) -> pd.DataFrame:
        """
        Descarga y limpia la demanda de turismo rural por provincias (Tabla 49380).

        CSV resultante con columnas: COD_PROV, PROVINCIA, Anyo, Periodo,
        viajeros, pernoctaciones.
        """
        logger.info(
            "[INE_RURAL_DEMANDA] -> Descargando Tabla %s (n_ultimos=%d)...",
            _TABLA_RURAL_DEMANDA_PROV, n_ultimos,
        )
        series = _descarga_tabla(self.client, _TABLA_RURAL_DEMANDA_PROV, n_ultimos)
        if not series:
            return empty_dataframe("rural_demanda_provincias")
        df_raw = _extract_series_data(
            series, _TABLA_RURAL_DEMANDA_PROV, "rural_demanda_provincias"
        )
        return _clean_provincial_data(
            df_raw, _CONCEPTO_DEMANDA_MAP, "rural_demanda_provincias",
            require_total_origen=True,
        )

    def search_operations(self, keyword: str) -> pd.DataFrame:
        resp = self.client.get(f"{BASE_URL}/OPERACIONES_DISPONIBLES")
        df = pd.DataFrame(resp.json())
        if "Nombre" in df.columns:
            mask = df["Nombre"].str.contains(keyword, case=False, na=False)
            return df[mask]
        return df

