"""Pipeline de extraccion de datos turisticos — Espana."""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime

import pandas as pd
from tqdm import tqdm

from config.settings import DATA_PROCESSED_DIR, PROVINCIAS_ESPANA
from src.utils.logger import get_logger, init_session_log
from src.utils.csv_writer import save_table
from src.utils.reporter import FailureReporter

from src.extractors.ign_extractor import IGNExtractor
from src.extractors.osm_extractor import OSMExtractor
from src.extractors.ine_extractor import INEExtractor
from src.extractors.datosgob_extractor import DatosGobExtractor
from src.extractors.aemet_extractor import AEMETExtractor

logger = get_logger(__name__)


def _cod_ine_provisional(nombre: str) -> str:
    return "PROV_" + hashlib.md5(nombre.encode("utf-8")).hexdigest()[:8]


def run_pipeline(
    sources: list[str] | None = None,
    n_periodos_ine: int = 12,
) -> None:
    all_sources = {
        "INE_provincias", "municipios_espana",
        "flujo_ine_provincia", "flujo_ine_localidad",
        "Carto_provincias", "turismo_oferta_osm",
        "clima_aemet", "datosgob",
    }
    sources = set(sources) if sources else all_sources

    log_path = init_session_log()
    logger.info("Fuentes: %s", ", ".join(sorted(sources)))

    reporter = FailureReporter()
    ine = INEExtractor()
    ign = IGNExtractor()
    osm = OSMExtractor()

    # 1. Provincias (INE Tabla 2852)
    df_prov = pd.DataFrame()
    if "INE_provincias" in sources:
        logger.info("--- FASE 1: Provincias (INE 2852) ---")
        try:
            df_ine_pob_prov = ine.get_maestro_provincias(n_ultimos=1)
            if not df_ine_pob_prov.empty:
                df_prov = df_ine_pob_prov.copy()
                cod_prov_map = {p["nombre"].lower(): p["cod_prov"] for p in PROVINCIAS_ESPANA}
                capital_map = {p["nombre"].lower(): p["capital"] for p in PROVINCIAS_ESPANA}
                ccaa_map = {p["nombre"].lower(): p["ccaa"] for p in PROVINCIAS_ESPANA}

                def _find_meta(prov_name, mapping):
                    pn = prov_name.lower().strip()
                    for k, v in mapping.items():
                        if k in pn or pn in k:
                            return v
                    return ""

                df_prov["_meta.cod_prov"] = df_prov["INE_Pob_PROV.provincia"].apply(lambda x: _find_meta(x, cod_prov_map))
                df_prov["_meta.capital"] = df_prov["INE_Pob_PROV.provincia"].apply(lambda x: _find_meta(x, capital_map))
                df_prov["_meta.ccaa"] = df_prov["INE_Pob_PROV.provincia"].apply(lambda x: _find_meta(x, ccaa_map))
                df_prov["_meta.fecha_extraccion"] = datetime.utcnow().isoformat()
                save_table(df_prov, "INE_provincias", DATA_PROCESSED_DIR)
            else:
                reporter.record("INE_Pob_PROV", "Nacional", "DataFrame vacio.")
        except Exception as exc:
            reporter.record("INE_Pob_PROV", "Nacional", str(exc), exc)

    # 2. Municipios (INE Tabla 29005)
    if "municipios_espana" in sources:
        logger.info("--- FASE 2: Municipios (INE 29005) ---")
        try:
            df_ine_mun_pob = ine.get_maestro_municipios(n_ultimos=1)
            if not df_ine_mun_pob.empty:
                save_table(df_ine_mun_pob, "municipios_espana", DATA_PROCESSED_DIR)
            else:
                reporter.record("INE_Pob_MUN", "Nacional", "DataFrame vacio.")
        except Exception as exc:
            reporter.record("INE_Pob_MUN", "Nacional", str(exc), exc)

    # 3. Flujos INE Provincia (Tabla 2074)
    if "flujo_ine_provincia" in sources:
        logger.info("--- FASE 3: Flujos EOH Provincia (INE 2074) ---")
        try:
            df_eoh_prov = ine.get_eoh_provincias(n_ultimos=n_periodos_ine)
            if not df_eoh_prov.empty:
                save_table(df_eoh_prov, "flujo_ine_provincia", DATA_PROCESSED_DIR)
            else:
                reporter.record("INE_EOH_PROV", "Nacional", "DataFrame vacio.")
        except Exception as exc:
            reporter.record("INE_EOH_PROV", "Nacional", str(exc), exc)

    # 4. Flujos INE Localidad (Tabla 2078)
    if "flujo_ine_localidad" in sources:
        logger.info("--- FASE 4: Flujos EOH Localidad (INE 2078) ---")
        try:
            df_eoh_mun = ine.get_eoh_municipios(n_ultimos=n_periodos_ine)
            if not df_eoh_mun.empty:
                save_table(df_eoh_mun, "flujo_ine_localidad", DATA_PROCESSED_DIR)
            else:
                reporter.record("INE_EOH_MUN", "Nacional", "DataFrame vacio.")
        except Exception as exc:
            reporter.record("INE_EOH_MUN", "Nacional", str(exc), exc)

    # 5. Geocodificacion
    localidades_rows: list[dict] = []
    if "Carto_provincias" in sources:
        logger.info("--- FASE 5: Geocodificacion (CartoCiudad/IGN) ---")
        targets = [{"nombre": p["capital"], "provincia": p["nombre"], "ccaa": p["ccaa"]} for p in PROVINCIAS_ESPANA]
        for t in tqdm(targets, desc="Geocodificando"):
            nombre = t["nombre"]
            geo = ign.geocode(nombre)
            if geo is None:
                nom_geo = osm.geocode_nominatim(nombre)
                if nom_geo:
                    geo = {
                        "CartoCiudad.cod_ine": _cod_ine_provisional(nombre),
                        "CartoCiudad.nombre_municipio": nombre,
                        "CartoCiudad.provincia": t.get("provincia", ""),
                        "CartoCiudad.ccaa": t.get("ccaa", ""),
                        "CartoCiudad.latitud": nom_geo["OSM_Nominatim.latitud"],
                        "CartoCiudad.longitud": nom_geo["OSM_Nominatim.longitud"],
                        "_meta.fuente_geocod": "OSM_Nominatim_fallback",
                        "_meta.fecha_extraccion": nom_geo["_meta.fecha_extraccion"],
                    }
                else:
                    reporter.record("IGN+OSM", nombre, "No geocodificado.")
                    continue
            fila = dict(geo)
            fila["_meta.cod_ine_clave"] = fila["CartoCiudad.cod_ine"]
            fila["_meta.nombre_municipio"] = nombre
            if not fila.get("CartoCiudad.provincia"):
                fila["CartoCiudad.provincia"] = t.get("provincia", "")
            if not fila.get("CartoCiudad.ccaa"):
                fila["CartoCiudad.ccaa"] = t.get("ccaa", "")
            localidades_rows.append(fila)
        if localidades_rows:
            save_table(pd.DataFrame(localidades_rows), "Carto_provincias", DATA_PROCESSED_DIR)

    # 6. Oferta OSM
    if "turismo_oferta_osm" in sources:
        logger.info("--- FASE 6: POIs OSM ---")
        oferta_osm_rows: list[dict] = []
        base = localidades_rows if localidades_rows else [
            {"_meta.cod_ine_clave": _cod_ine_provisional(p["capital"]),
             "_meta.nombre_municipio": p["capital"]}
            for p in PROVINCIAS_ESPANA
        ]
        for fila in tqdm(base, desc="POIs OSM"):
            nombre = fila["_meta.nombre_municipio"]
            cod_ine = fila["_meta.cod_ine_clave"]
            try:
                counts = osm.poi_counts(nombre, lat=fila.get("CartoCiudad.latitud"), lon=fila.get("CartoCiudad.longitud"))
                counts["_meta.cod_ine_clave"] = cod_ine
                counts["_meta.nombre_municipio"] = nombre
                oferta_osm_rows.append(counts)
            except Exception as exc:
                reporter.record("OSM", nombre, str(exc), exc)
        if oferta_osm_rows:
            save_table(pd.DataFrame(oferta_osm_rows), "oferta_osm", DATA_PROCESSED_DIR)

    # 7. AEMET
    if "clima_aemet" in sources:
        logger.info("--- FASE 7: AEMET OpenData ---")
        aemet = AEMETExtractor()
        if not aemet.is_active:
            reporter.record_skip("AEMET", "AEMET_API_KEY no configurada.")
        else:
            targets_aemet = localidades_rows if localidades_rows else [
                {"_meta.cod_ine_clave": p["cod_prov"] + "001", "_meta.nombre_municipio": p["capital"]}
                for p in PROVINCIAS_ESPANA
            ]
            try:
                df_clima = aemet.get_predicciones_municipios(targets_aemet)
                if not df_clima.empty:
                    save_table(df_clima, "clima_aemet", DATA_PROCESSED_DIR)
                else:
                    reporter.record("AEMET", "Nacional", "DataFrame vacio.")
            except Exception as exc:
                reporter.record("AEMET", "Nacional", str(exc), exc)
            finally:
                aemet.close()

    # 8. Datos Abiertos (datos.gob.es)
    if "datosgob" in sources:
        logger.info("--- FASE 8: datos.gob.es ---")
        datosgob = DatosGobExtractor()
        keywords = ["turismo", "ocupación hotelera", "turismo rural", "alojamientos turísticos"]
        datosgob_frames: list[pd.DataFrame] = []
        for kw in keywords:
            try:
                df_gob = datosgob.search_datasets(kw, limit=20)
                if not df_gob.empty:
                    datosgob_frames.append(df_gob)
            except Exception as exc:
                reporter.record("DatosGob", kw, str(exc), exc)
        if datosgob_frames:
            df_total_gob = pd.concat(datosgob_frames, ignore_index=True)
            if "DatosGob.url_recurso" in df_total_gob.columns:
                df_total_gob = df_total_gob.drop_duplicates(subset=["DatosGob.url_recurso"])
            save_table(df_total_gob, "datosgob_catalogo", DATA_PROCESSED_DIR)

    # Cierre
    reporter.save(DATA_PROCESSED_DIR)
    logger.info("Pipeline completado. CSV en: %s", DATA_PROCESSED_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de datos turisticos de Espana")
    parser.add_argument("--sources", nargs="+", default=None)
    parser.add_argument("--periodos-ine", type=int, default=12)
    args = parser.parse_args()
    run_pipeline(sources=args.sources, n_periodos_ine=args.periodos_ine)


if __name__ == "__main__":
    main()
