"""Cálculo de métricas turísticas derivadas para provincias de España."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config.settings import DATA_PROCESSED_DIR, PROVINCIAS_ESPANA
from src.schema import TABLE_SCHEMAS, empty_dataframe
from src.utils.logger import get_logger

import unicodedata

logger = get_logger(__name__)


def _normalize_text(text: str) -> str:
    """Normaliza texto eliminando diacríticos, convirtiendo a minúsculas y limpiando espacios."""
    n = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in n if not unicodedata.combining(c)).lower().strip()


_CCAA_NON_PROV: list[str] = [
    "total nacional", "nacional", "andalucia", "aragon", "castilla y leon",
    "castilla-la mancha", "castilla - la mancha", "cataluna", "comunitat valenciana",
    "extremadura", "galicia", "pais vasco", "canarias",
    "madrid (comunidad de)", "murcia (region de)", "navarra (comunidad foral de)",
    "asturias (principado de)", "principado de asturias", "baleares (illes)", "rioja (la)",
    "cantabria. viajeros. total",
]

_PROV_ALIASES: dict[str, list[str]] = {
    "01": ["araba/alava", "araba", "alava", "vitoria", "vitoria-gasteiz"],
    "02": ["albacete"],
    "03": ["alicante/alacant", "alicante", "alacant"],
    "04": ["almeria"],
    "05": ["avila"],
    "06": ["badajoz"],
    "07": ["balears, illes", "illes balears", "baleares", "balears", "palma"],
    "08": ["barcelona"],
    "09": ["burgos"],
    "10": ["caceres"],
    "11": ["cadiz"],
    "12": ["castellon/castello", "castellon", "castello", "castellon de la plana"],
    "13": ["ciudad real"],
    "14": ["cordoba"],
    "15": ["a coruna", "coruna, a", "coruna (a)", "coruna", "la coruna"],
    "16": ["cuenca"],
    "17": ["girona", "gerona"],
    "18": ["granada"],
    "19": ["guadalajara"],
    "20": ["gipuzkoa", "guipuzcoa"],
    "21": ["huelva"],
    "22": ["huesca"],
    "23": ["jaen"],
    "24": ["leon"],
    "25": ["lleida", "lerida"],
    "26": ["la rioja", "rioja, la", "rioja"],
    "27": ["lugo"],
    "28": ["madrid"],
    "29": ["malaga"],
    "30": ["murcia"],
    "31": ["navarra", "nafarroa", "pamplona"],
    "32": ["ourense", "orense"],
    "33": ["asturias", "oviedo"],
    "34": ["palencia"],
    "35": ["las palmas", "palmas, las", "palmas (las)", "palmas"],
    "36": ["pontevedra"],
    "37": ["salamanca"],
    "38": ["santa cruz de tenerife", "santa cruz tenerife", "tenerife", "s.c. tenerife"],
    "39": ["cantabria", "santander"],
    "40": ["segovia"],
    "41": ["sevilla"],
    "42": ["soria"],
    "43": ["tarragona"],
    "44": ["teruel"],
    "45": ["toledo"],
    "46": ["valencia/valencia", "valencia"],
    "47": ["valladolid"],
    "48": ["bizkaia", "vizcaya", "bilbao"],
    "49": ["zamora"],
    "50": ["zaragoza"],
    "51": ["ceuta"],
    "52": ["melilla"],
}

_PROV_LOOKUP: dict[str, str] = {}
_PROV_CANONICAL_NAME: dict[str, str] = {p["cod_prov"]: p["nombre"] for p in PROVINCIAS_ESPANA}

for _cod, _aliases in _PROV_ALIASES.items():
    for _alias in _aliases:
        _norm = _normalize_text(_alias)
        _PROV_LOOKUP[_norm] = _cod

_SORTED_ALIASES = sorted(_PROV_LOOKUP.keys(), key=lambda x: -len(x))


def _match_prov_from_text(nombre: str) -> tuple[str | None, str | None]:
    """Extrae (cod_prov, nombre_oficial) analizando el texto del campo Nombre con normalización de diacríticos."""
    if not nombre:
        return None, None
    norm_name = _normalize_text(nombre)
    for ccaa in _CCAA_NON_PROV:
        if (
            norm_name.startswith(ccaa + ".")
            or norm_name.startswith(ccaa + " ")
            or norm_name.startswith(ccaa + "/")
            or norm_name.startswith(ccaa + ",")
            or norm_name == ccaa
        ):
            return None, None
    for alias in _SORTED_ALIASES:
        if (
            norm_name.startswith(alias + ".")
            or norm_name.startswith(alias + " ")
            or norm_name.startswith(alias + "/")
            or norm_name.startswith(alias + ",")
            or norm_name == alias
        ):
            cod = _PROV_LOOKUP[alias]
            return cod, _PROV_CANONICAL_NAME.get(cod, alias)
    return None, None


def extract_population_by_province(df_pob: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Extrae la población total residente por código de provincia a partir de INE Tabla 2852."""
    pob_map: dict[str, dict[str, Any]] = {}
    if df_pob.empty:
        return pob_map

    # Ordenar cronológicamente para retener de forma determinista la última cifra
    df_sorted = df_pob
    sort_cols = [c for c in ["Anyo", "Fecha"] if c in df_pob.columns]
    if sort_cols:
        df_sorted = df_pob.sort_values(by=sort_cols, ascending=True, na_position="first")

    for _, row in df_sorted.iterrows():
        meta_raw = row.get("MetaData_json")
        meta: list[dict] = []
        if isinstance(meta_raw, str) and meta_raw.strip():
            try:
                meta = json.loads(meta_raw)
            except Exception:
                meta = []

        prov_code: str | None = None
        prov_name: str | None = None
        is_total_sex = False
        has_sex_var = False
        is_ccaa_region = False

        if meta:
            for m in meta:
                v_name = m.get("T3_Variable", "")
                c_name = m.get("Nombre", "")
                c_code = str(m.get("Codigo", "")).strip()

                if v_name == "Provincias":
                    if c_code and c_code != "00":
                        prov_code = c_code.zfill(2)
                        prov_name = c_name
                    elif c_code == "00":
                        is_ccaa_region = True
                elif v_name == "Comunidades y Ciudades Autónomas":
                    if c_code == "18" or c_name == "Ceuta":
                        prov_code = "51"
                        prov_name = "Ceuta"
                    elif c_code == "19" or c_name == "Melilla":
                        prov_code = "52"
                        prov_name = "Melilla"
                    else:
                        is_ccaa_region = True
                elif v_name == "Sexo":
                    has_sex_var = True
                    if c_name == "Total" or c_code == "0":
                        is_total_sex = True
        else:
            nombre = str(row.get("Nombre", ""))
            norm_name = _normalize_text(nombre)
            # Fallback por texto solo si no hay metadatos estructurados
            if "hombres" not in norm_name and "mujeres" not in norm_name:
                if (
                    ". total." in norm_name
                    or norm_name.startswith("total.")
                    or ". total " in norm_name
                    or " total." in norm_name
                    or norm_name.endswith(". total")
                    or norm_name.endswith(". total.")
                ):
                    is_total_sex = True
            prov_code, prov_name = _match_prov_from_text(nombre)

        valid_sex = is_total_sex if has_sex_var else (is_total_sex or not meta)

        if prov_code and not is_ccaa_region and valid_sex:
            val = row.get("Valor")
            if pd.notna(val):
                pob_map[prov_code] = {
                    "cod_prov": prov_code,
                    "provincia": prov_name or "",
                    "poblacion": float(val),
                }

    return pob_map


def extract_monthly_viajeros_by_province(df_flujo: pd.DataFrame) -> pd.DataFrame:
    """Extrae las observaciones mensuales de viajeros totales por provincia desde INE Tabla 2074."""
    if df_flujo.empty:
        return pd.DataFrame()

    records: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for _, row in df_flujo.iterrows():
        meta_raw = row.get("MetaData_json")
        meta: list[dict] = []
        if isinstance(meta_raw, str) and meta_raw.strip():
            try:
                meta = json.loads(meta_raw)
            except Exception:
                meta = []

        prov_code: str | None = None
        prov_name: str | None = None
        is_viajero = False
        is_total_origen = False
        has_concepto_var = False
        has_origen_var = False
        is_ccaa_region = False

        if meta:
            for m in meta:
                v_name = m.get("T3_Variable", "")
                c_name = m.get("Nombre", "")
                c_code = str(m.get("Codigo", "")).strip()

                if v_name == "Provincias":
                    if c_code and c_code != "00":
                        prov_code = c_code.zfill(2)
                        prov_name = c_name
                    elif c_code == "00":
                        is_ccaa_region = True
                elif v_name == "Comunidades y Ciudades Autónomas":
                    if c_code == "18" or c_name == "Ceuta":
                        prov_code = "51"
                        prov_name = "Ceuta"
                    elif c_code == "19" or c_name == "Melilla":
                        prov_code = "52"
                        prov_name = "Melilla"
                    else:
                        is_ccaa_region = True
                elif "Concepto" in v_name:
                    has_concepto_var = True
                    if "Viajero" in c_name or c_code == "B":
                        is_viajero = True
                elif "RESIDENCIA" in v_name or "ORIGEN" in v_name:
                    has_origen_var = True
                    if c_name == "Total" or c_code == "0":
                        is_total_origen = True
        else:
            nombre_str = str(row.get("Nombre", ""))
            norm_str = _normalize_text(nombre_str)
            if "viajer" in norm_str and "pernoctac" not in norm_str:
                is_viajero = True
            if "residentes en espa" not in norm_str and "residentes en el extranjero" not in norm_str:
                if (
                    ". total." in norm_str
                    or ". total " in norm_str
                    or norm_str.endswith(". total")
                    or norm_str.endswith(". total.")
                    or "total categor" in norm_str
                ):
                    is_total_origen = True
            prov_code, prov_name = _match_prov_from_text(nombre_str)

        valid_concepto = is_viajero if has_concepto_var else is_viajero
        valid_origen = is_total_origen if has_origen_var else is_total_origen

        if prov_code and not is_ccaa_region and valid_concepto and valid_origen:
            val = row.get("Valor")
            if pd.notna(val):
                periodo = str(row.get("T3_Periodo", "")).strip()
                anyo = row.get("Anyo")
                key = (prov_code, str(anyo), periodo)
                if key not in seen_keys:
                    seen_keys.add(key)
                    records.append({
                        "cod_prov": prov_code,
                        "provincia": prov_name or "",
                        "periodo": periodo,
                        "anyo": anyo,
                        "viajeros": float(val),
                    })

    return pd.DataFrame(records)


def compute_derived_metrics(
    df_poblacion: pd.DataFrame | None = None,
    df_flujo: pd.DataFrame | None = None,
    processed_dir: Path | None = None,
    auto_fetch_if_missing: bool = False,
) -> pd.DataFrame:
    """
    Calcula métricas derivadas de turismo por provincia:
    1. Presión turística = total de viajeros / población residente.
    2. Índice de estacionalidad = coeficiente de variación (CV = std / media) de viajeros mensuales.
    """
    out_dir = processed_dir or DATA_PROCESSED_DIR

    # Cargar datos de población si no se proporcionaron
    if df_poblacion is None:
        pob_file = out_dir / "INE_provincias.csv"
        if pob_file.exists():
            try:
                df_poblacion = pd.read_csv(pob_file)
            except Exception as exc:
                logger.warning("[Metricas] Error leyendo %s: %s", pob_file, exc)
                df_poblacion = pd.DataFrame()
        else:
            df_poblacion = pd.DataFrame()

    # Cargar datos de flujo si no se proporcionaron
    if df_flujo is None:
        flujo_file = out_dir / "flujo_ine_provincia.csv"
        if flujo_file.exists():
            try:
                df_flujo = pd.read_csv(flujo_file)
            except Exception as exc:
                logger.warning("[Metricas] Error leyendo %s: %s", flujo_file, exc)
                df_flujo = pd.DataFrame()
        else:
            df_flujo = pd.DataFrame()

    if (df_poblacion.empty or df_flujo.empty) and auto_fetch_if_missing:
        from src.extractors.ine_extractor import INEExtractor
        ine = INEExtractor()
        if df_poblacion.empty:
            logger.info("[Metricas] Descargando datos de poblacion de provincias del INE...")
            df_poblacion = ine.get_maestro_provincias(n_ultimos=1)
        if df_flujo.empty:
            logger.info("[Metricas] Descargando datos de flujos EOH de provincias del INE...")
            df_flujo = ine.get_eoh_provincias(n_ultimos=12)

    if df_poblacion.empty or df_flujo.empty:
        logger.warning("[Metricas] Datos de población o flujo vacíos; retornando esquema vacío.")
        return empty_dataframe("metricas_derivadas")

    pob_map = extract_population_by_province(df_poblacion)
    df_viajeros = extract_monthly_viajeros_by_province(df_flujo)

    if df_viajeros.empty:
        logger.warning("[Metricas] No se pudieron extraer datos de viajeros mensuales por provincia.")
        return empty_dataframe("metricas_derivadas")

    # Mapeo de nombres oficiales desde settings como fallback
    nombres_provincias = {p["cod_prov"]: p["nombre"] for p in PROVINCIAS_ESPANA}

    records: list[dict[str, Any]] = []
    fecha_extraccion = datetime.now().isoformat()

    for cod_prov, grp in df_viajeros.groupby("cod_prov"):
        cod_prov_str = str(cod_prov).zfill(2)
        prov_name = (
            grp["provincia"].dropna().iloc[0]
            if not grp["provincia"].dropna().empty
            else nombres_provincias.get(cod_prov_str, "")
        )

        viajeros_series = grp["viajeros"].dropna()
        n_meses = len(viajeros_series)
        total_viajeros = float(viajeros_series.sum()) if n_meses > 0 else 0.0
        media_viajeros = float(viajeros_series.mean()) if n_meses > 0 else 0.0
        std_viajeros = float(viajeros_series.std(ddof=1)) if n_meses > 1 else 0.0

        # Coeficiente de variación (índice de estacionalidad)
        indice_estacionalidad = (std_viajeros / media_viajeros) if media_viajeros > 0 else 0.0

        pob_info = pob_map.get(cod_prov_str, {})
        poblacion = pob_info.get("poblacion", np.nan)

        # Presión turística
        presion_turistica = (
            (total_viajeros / poblacion) if (pd.notna(poblacion) and poblacion > 0) else np.nan
        )

        records.append({
            "cod_prov": cod_prov_str,
            "provincia": prov_name,
            "poblacion": poblacion,
            "total_viajeros": total_viajeros,
            "media_mensual_viajeros": media_viajeros,
            "std_mensual_viajeros": std_viajeros,
            "presion_turistica": presion_turistica,
            "indice_estacionalidad": indice_estacionalidad,
            "n_meses": n_meses,
            "_meta.fecha_extraccion": fecha_extraccion,
        })

    if not records:
        return empty_dataframe("metricas_derivadas")

    # Ordenar por código de provincia
    df_metrics = pd.DataFrame(records).sort_values("cod_prov").reset_index(drop=True)
    logger.info("[Metricas] [OK] Calculadas metricas derivadas para %d provincias.", len(df_metrics))
    return df_metrics


