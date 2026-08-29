"""Pipeline de extracción de datos turísticos en bruto — España."""
from __future__ import annotations

import argparse
from datetime import datetime

import pandas as pd
from tqdm import tqdm

from config.settings import DATA_PROCESSED_DIR, PROVINCIAS_ESPANA
from src.extractors.aemet_extractor import AEMETExtractor
from src.extractors.datosgob_extractor import DatosGobExtractor
from src.extractors.ign_extractor import IGNExtractor
from src.extractors.ine_extractor import INEExtractor
from src.extractors.osm_extractor import OSMExtractor
from src.utils.csv_writer import save_table
from src.utils.logger import get_logger, init_session_log
from src.utils.reporter import FailureReporter

logger = get_logger(__name__)


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
    logger.info("Fuentes activas: %s", ", ".join(sorted(sources)))

    reporter = FailureReporter()
    ine = INEExtractor()
    ign = IGNExtractor()
    osm = OSMExtractor()

    # 1. Provincias (INE Tabla 2852)
    if "INE_provincias" in sources:
        logger.info("--- FASE 1: Provincias (INE 2852) ---")
        try:
            df_prov = ine.get_maestro_provincias(n_ultimos=1)
            if not df_prov.empty:
                save_table(df_prov, "INE_provincias", DATA_PROCESSED_DIR)
            else:
                reporter.record("INE_Pob_PROV", "Nacional", "DataFrame vacio.")
        except Exception as exc:
            reporter.record("INE_Pob_PROV", "Nacional", str(exc), exc)

    # 2. Municipios (INE Tabla 29005)
    if "municipios_espana" in sources:
        logger.info("--- FASE 2: Municipios (INE 29005) ---")
        try:
            df_mun = ine.get_maestro_municipios(n_ultimos=1)
            if not df_mun.empty:
                save_table(df_mun, "municipios_espana", DATA_PROCESSED_DIR)
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

    # 5. Geocodificación CartoCiudad
    carto_rows: list[dict] = []
    if "Carto_provincias" in sources:
        logger.info("--- FASE 5: Geocodificacion CartoCiudad ---")
        for p in tqdm(PROVINCIAS_ESPANA, desc="CartoCiudad"):
            geo = ign.geocode(p["capital"])
            if geo:
                carto_rows.append(geo)
            else:
                reporter.record("CartoCiudad", p["capital"], "Sin resultados.")
        if carto_rows:
            save_table(pd.DataFrame(carto_rows), "Carto_provincias", DATA_PROCESSED_DIR)

    # 6. Oferta OSM
    if "turismo_oferta_osm" in sources:
        logger.info("--- FASE 6: POIs OSM ---")
        osm_rows: list[dict] = []
        for p in tqdm(PROVINCIAS_ESPANA, desc="OSM POIs"):
            geo_nom = osm.geocode_nominatim(f"{p['capital']}, España")
            if geo_nom and geo_nom.get("lat") and geo_nom.get("lon"):
                lat = float(geo_nom["lat"])
                lon = float(geo_nom["lon"])
                counts = osm.query_overpass_counts(p["capital"], lat=lat, lon=lon)
                osm_rows.append(counts)
            else:
                reporter.record("OSM", p["capital"], "No se pudo geocodificar para Overpass.")
        if osm_rows:
            save_table(pd.DataFrame(osm_rows), "oferta_osm", DATA_PROCESSED_DIR)

    # 7. AEMET OpenData
    if "clima_aemet" in sources:
        logger.info("--- FASE 7: AEMET OpenData ---")
        aemet = AEMETExtractor()
        if not aemet.is_active:
            reporter.record_skip("AEMET", "AEMET_API_KEY no configurada.")
        else:
            targets_aemet = [{"cod_ine": p["cod_prov"] + "001"} for p in PROVINCIAS_ESPANA]
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

    # 8. Catálogo datos.gob.es
    if "datosgob" in sources:
        logger.info("--- FASE 8: datos.gob.es ---")
        datosgob = DatosGobExtractor()
        keywords = ["turismo", "ocupación hotelera", "turismo rural"]
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
            save_table(df_total_gob, "datosgob_catalogo", DATA_PROCESSED_DIR)

    reporter.save(DATA_PROCESSED_DIR)
    logger.info("Pipeline completado con éxito. Archivos en: %s", DATA_PROCESSED_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de datos turísticos crudos de España")
    parser.add_argument("--sources", nargs="+", default=None)
    parser.add_argument("--periodos-ine", type=int, default=12)
    args = parser.parse_args()
    run_pipeline(sources=args.sources, n_periodos_ine=args.periodos_ine)


if __name__ == "__main__":
    main()
