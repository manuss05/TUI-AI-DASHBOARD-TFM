"""Pipeline de extracción de datos turísticos en bruto — España."""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime

import pandas as pd
from tqdm import tqdm

from config.settings import DATA_PROCESSED_DIR, DATA_RAW_DIR, PROVINCIAS_ESPANA
from src.extractors.aemet_extractor import AEMETExtractor
from src.extractors.datosgob_extractor import DatosGobExtractor
from src.extractors.ign_extractor import IGNExtractor
from src.extractors.ine_extractor import INEExtractor
from src.extractors.osm_extractor import OSMExtractor
from src.metrics import compute_derived_metrics
from src.utils.csv_writer import save_table
from src.utils.logger import get_logger, init_session_log
from src.utils.reporter import FailureReporter

logger = get_logger(__name__)


def run_pipeline(
    sources: list[str] | None = None,
    n_periodos_ine: int = 12,
    max_pages_datosgob: int | None = None,
) -> None:
    all_sources = {
        "INE_provincias", "municipios_espana",
        "flujo_ine_provincia", "flujo_ine_localidad",
        "rentabilidad_H", "gasto_turistico",
        "metricas_derivadas",
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

    df_prov: pd.DataFrame | None = None
    df_eoh_prov: pd.DataFrame | None = None

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

    # 5. Indicadores de Rentabilidad Hotelera (ADR / RevPAR - Tablas 2059, 2057)
    if "rentabilidad_H" in sources:
        logger.info("--- FASE 5: Rentabilidad Hotelera (INE ADR/RevPAR) ---")
        try:
            df_rent = ine.get_rentabilidad_H(n_ultimos=n_periodos_ine)
            if not df_rent.empty:
                save_table(df_rent, "rentabilidad_H", DATA_PROCESSED_DIR)
            else:
                reporter.record("INE_Rentabilidad", "Nacional", "DataFrame vacio.")
        except Exception as exc:
            reporter.record("INE_Rentabilidad", "Nacional", str(exc), exc)

    # 6. Gasto Turístico (EGATUR - Tablas 10839, 10835)
    if "gasto_turistico" in sources:
        logger.info("--- FASE 6: Gasto Turistico (INE EGATUR) ---")
        try:
            df_gasto = ine.get_gasto_turistico(n_ultimos=n_periodos_ine)
            if not df_gasto.empty:
                save_table(df_gasto, "gasto_turistico", DATA_PROCESSED_DIR)
            else:
                reporter.record("INE_EGATUR", "Nacional", "DataFrame vacio.")
        except Exception as exc:
            reporter.record("INE_EGATUR", "Nacional", str(exc), exc)

    # 7. Métricas Derivadas (Presión Turística y Estacionalidad)
    if "metricas_derivadas" in sources:
        logger.info("--- FASE 7: Metricas Derivadas (Presion y Estacionalidad) ---")
        try:
            df_deriv = compute_derived_metrics(
                df_poblacion=df_prov,
                df_flujo=df_eoh_prov,
                processed_dir=DATA_PROCESSED_DIR,
                auto_fetch_if_missing=True,
            )
            if not df_deriv.empty:
                save_table(df_deriv, "metricas_derivadas", DATA_PROCESSED_DIR)
            else:
                reporter.record("Metricas_Derivadas", "Nacional", "DataFrame vacio.")
        except Exception as exc:
            reporter.record("Metricas_Derivadas", "Nacional", str(exc), exc)

    # 8. Geocodificación CartoCiudad
    carto_rows: list[dict] = []
    if "Carto_provincias" in sources:
        logger.info("--- FASE 8: Geocodificacion CartoCiudad ---")
        for p in tqdm(PROVINCIAS_ESPANA, desc="CartoCiudad"):
            geo = ign.geocode(p["capital"])
            if geo:
                carto_rows.append(geo)
            else:
                reporter.record("CartoCiudad", p["capital"], "Sin resultados.")
        if carto_rows:
            save_table(pd.DataFrame(carto_rows), "Carto_provincias", DATA_PROCESSED_DIR)

    # 9. Oferta OSM
    if "turismo_oferta_osm" in sources:
        logger.info("--- FASE 9: POIs OSM ---")
        cache_file = DATA_RAW_DIR / "osm_cache.json"
        osm_cache = {}
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    osm_cache = json.load(f)
            except Exception:
                osm_cache = {}

        osm_rows: list[dict] = []
        for p in tqdm(PROVINCIAS_ESPANA, desc="OSM POIs"):
            cap = p["capital"]
            if cap in osm_cache and osm_cache[cap].get("mirror_usado") != "FAILED":
                osm_rows.append(osm_cache[cap])
                continue

            geo_nom = osm.geocode_nominatim(f"{cap}, España")
            if geo_nom and geo_nom.get("lat") and geo_nom.get("lon"):
                lat = float(geo_nom["lat"])
                lon = float(geo_nom["lon"])
                counts = osm.query_overpass_counts(cap, lat=lat, lon=lon)
                osm_rows.append(counts)
                if counts.get("mirror_usado") != "FAILED":
                    osm_cache[cap] = counts
                    try:
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump(osm_cache, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
            else:
                reporter.record("OSM", cap, "No se pudo geocodificar para Overpass.")
            time.sleep(1.0)
        if osm_rows:
            save_table(pd.DataFrame(osm_rows), "oferta_osm", DATA_PROCESSED_DIR)

    # 10. AEMET OpenData
    if "clima_aemet" in sources:
        logger.info("--- FASE 10: AEMET OpenData ---")
        aemet = AEMETExtractor()
        if not aemet.is_active:
            reporter.record_skip("AEMET", "AEMET_API_KEY no configurada.")
        else:
            try:
                # Obtenemos climatología del año anterior y actual por defecto (puedes ajustar años)
                anio_actual = datetime.now().year
                df_clima = aemet.get_climatologias_provinciales(anio_ini=anio_actual - 1, anio_fin=anio_actual)
                if not df_clima.empty:
                    save_table(df_clima, "clima_aemet", DATA_PROCESSED_DIR)
                else:
                    reporter.record("AEMET", "Nacional", "DataFrame vacio.")
            except Exception as exc:
                reporter.record("AEMET", "Nacional", str(exc), exc)
            finally:
                aemet.close()

    # 11. Catálogo datos.gob.es
    if "datosgob" in sources:
        logger.info("--- FASE 11: datos.gob.es ---")
        datosgob = DatosGobExtractor()
        try:
            df_gob = datosgob.get_theme_datasets(
                theme="turismo", page_size=50, max_pages=max_pages_datosgob
            )
            if not df_gob.empty:
                save_table(df_gob, "datosgob_catalogo", DATA_PROCESSED_DIR)
            else:
                reporter.record("DatosGob", "turismo", "DataFrame vacio.")
        except Exception as exc:
            reporter.record("DatosGob", "turismo", str(exc), exc)

    reporter.save(DATA_PROCESSED_DIR)
    logger.info("Pipeline completado con éxito. Archivos en: %s", DATA_PROCESSED_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de datos turísticos crudos de España")
    parser.add_argument("--sources", nargs="+", default=None)
    parser.add_argument("--periodos-ine", type=int, default=12)
    parser.add_argument("--max-pages-datosgob", type=int, default=None, help="Límite opcional de páginas para datos.gob.es")
    args = parser.parse_args()
    run_pipeline(
        sources=args.sources,
        n_periodos_ine=args.periodos_ine,
        max_pages_datosgob=args.max_pages_datosgob,
    )


if __name__ == "__main__":
    main()

