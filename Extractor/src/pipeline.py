"""Pipeline de extracción de datos turísticos en bruto — España."""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime

import pandas as pd
from tqdm import tqdm

from config.settings import (
    CARTOGRAFIA_SHP,
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    OSM_POLYGONS_CACHE_DIR,
    PROVINCIAS_ESPANA,
    ROOT_PROCESSED_DIR,
)
from src.extractors.aemet_extractor import AEMETExtractor
from src.extractors.datosgob_extractor import DatosGobExtractor
from src.extractors.ign_extractor import IGNExtractor
from src.extractors.ine_extractor import INEExtractor
from src.extractors.osm_extractor import OSMExtractor
from src.metrics import compute_derived_metrics
from src.utils.csv_writer import save_parquet, save_table
from src.utils.logger import get_logger, init_session_log
from src.utils.reporter import FailureReporter

logger = get_logger(__name__)


def run_pipeline(
    sources: list[str] | None = None,
    n_periodos_ine: int = 24,
    max_pages_datosgob: int | None = None,
    cod_prov: list[str] | None = None,
) -> None:
    all_sources = {
        "INE_provincias", "municipios_espana",
        "flujo_ine_provincia", "flujo_ine_localidad",
        "rentabilidad_H", "gasto_turistico",
        "metricas_derivadas",
        "eoh_oferta_provincias", "rural_oferta_provincias", "rural_demanda_provincias",
        "Carto_provincias", "turismo_oferta_osm", "pois_espana_osm",
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
            df_osm_raw = pd.DataFrame(osm_rows)
            save_table(df_osm_raw, "oferta_osm", DATA_PROCESSED_DIR)
            df_osm_parsed = osm.parse_osm_dataframe(df_osm_raw)
            save_table(df_osm_parsed, "osm_oferta_provincias", DATA_PROCESSED_DIR)

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

    # 12. Oferta Hotelera EOH (Tabla 2065)
    if "eoh_oferta_provincias" in sources:
        logger.info("--- FASE 12: Oferta Hotelera EOH (INE 2065) ---")
        try:
            df_eoh_of = ine.get_eoh_oferta_provincias(n_ultimos=n_periodos_ine)
            if not df_eoh_of.empty:
                save_table(df_eoh_of, "eoh_oferta_provincias", DATA_PROCESSED_DIR)
            else:
                reporter.record("INE_EOH_Oferta", "Nacional", "DataFrame vacio.")
        except Exception as exc:
            reporter.record("INE_EOH_Oferta", "Nacional", str(exc), exc)

    # 13. Turismo Rural Oferta (Tabla 2070)
    if "rural_oferta_provincias" in sources:
        logger.info("--- FASE 13: Turismo Rural Oferta (INE 2070) ---")
        try:
            df_rur_of = ine.get_rural_oferta_provincias(n_ultimos=n_periodos_ine)
            if not df_rur_of.empty:
                save_table(df_rur_of, "rural_oferta_provincias", DATA_PROCESSED_DIR)
            else:
                reporter.record("INE_Rural_Oferta", "Nacional", "DataFrame vacio.")
        except Exception as exc:
            reporter.record("INE_Rural_Oferta", "Nacional", str(exc), exc)

    # 14. Turismo Rural Demanda (Tabla 49380)
    if "rural_demanda_provincias" in sources:
        logger.info("--- FASE 14: Turismo Rural Demanda (INE 49380) ---")
        try:
            df_rur_dem = ine.get_rural_demanda_provincias(n_ultimos=n_periodos_ine)
            if not df_rur_dem.empty:
                save_table(df_rur_dem, "rural_demanda_provincias", DATA_PROCESSED_DIR)
            else:
                reporter.record("INE_Rural_Demanda", "Nacional", "DataFrame vacio.")
        except Exception as exc:
            reporter.record("INE_Rural_Demanda", "Nacional", str(exc), exc)

    # 15. POIs Georreferenciados Provinciales (OSM + Delimitación Poligonal)
    if "pois_espana_osm" in sources:
        logger.info("--- FASE 15: POIs OSM delimitados por polígono provincial ---")
        try:
            import geopandas as gpd

            if not CARTOGRAFIA_SHP.exists():
                reporter.record("POIs_OSM_Polygon", "Nacional", f"No se encontró cartografía en {CARTOGRAFIA_SHP}")
            else:
                logger.info("Cargando y disolviendo capas provinciales desde %s...", CARTOGRAFIA_SHP.name)
                gdf_muni = gpd.read_file(CARTOGRAFIA_SHP)
                gdf_muni["COD_PROV"] = gdf_muni["COD_PROV"].astype(str).str.zfill(2)
                gdf_provs = gdf_muni.dissolve(by="COD_PROV", as_index=False)[["COD_PROV", "geometry"]].to_crs(epsg=4326)

                if cod_prov:
                    target_codes = {str(c).zfill(2) for c in cod_prov}
                    gdf_provs = gdf_provs[gdf_provs["COD_PROV"].isin(target_codes)].copy()
                    logger.info("Filtrando ejecución para %d provincias: %s", len(gdf_provs), sorted(target_codes))

                prov_dfs: list[pd.DataFrame] = []
                cfg_by_code = {p["cod_prov"]: p for p in PROVINCIAS_ESPANA}

                for _, p_row in tqdm(gdf_provs.iterrows(), total=len(gdf_provs), desc="POIs Provinciales OSM"):
                    c_code = p_row["COD_PROV"]
                    prov_info = cfg_by_code.get(c_code, {})
                    prov_nombre = prov_info.get("nombre", f"Prov_{c_code}")
                    prov_geom = p_row["geometry"]

                    # Corrección cartográfica para Canarias: en shapefiles temáticos oficiales (Munic04_ESP.shp),
                    # las islas están en el 'recuadro peninsular' desplazado artificialmente al SO de Cádiz.
                    # Las trasladamos a su posición geográfica real WGS84 para consultar OpenStreetMap:
                    if c_code == "38":  # Santa Cruz de Tenerife
                        from shapely.affinity import translate
                        prov_geom = translate(prov_geom, xoff=-5.5131308, yoff=-6.5775784)
                    elif c_code == "35":  # Las Palmas
                        from shapely.affinity import translate
                        prov_geom = translate(prov_geom, xoff=-5.6379886, yoff=-6.7167058)

                    safe_nombre = prov_nombre.replace("/", "_").replace(" ", "_")
                    cache_prov_file = OSM_POLYGONS_CACHE_DIR / f"{c_code}_{safe_nombre}.parquet"

                    if cache_prov_file.exists():
                        try:
                            df_cached = pd.read_parquet(cache_prov_file)
                            if not df_cached.empty:
                                prov_dfs.append(df_cached)
                                continue
                        except Exception as c_err:
                            logger.warning("Error leyendo caché para %s: %s", prov_nombre, c_err)

                    try:
                        df_prov_pois = osm.extract_provincia_pois_polygon(
                            prov_geom=prov_geom,
                            cod_prov=c_code,
                            prov_nombre=prov_nombre,
                        )
                        if not df_prov_pois.empty:
                            df_prov_pois.to_parquet(cache_prov_file, index=False, engine="pyarrow")
                            prov_dfs.append(df_prov_pois)
                        else:
                            logger.info("Provincia %s sin POIs devueltos.", prov_nombre)
                    except Exception as p_err:
                        reporter.record("POIs_OSM_Polygon", prov_nombre, str(p_err), p_err)

                    time.sleep(1.5)

                if prov_dfs:
                    df_all_pois = pd.concat(prov_dfs, ignore_index=True)
                    df_all_pois = df_all_pois.drop_duplicates(subset=["osm_id"]).reset_index(drop=True)

                    pq_path = save_parquet(df_all_pois, "pois_espana_osm", DATA_PROCESSED_DIR)
                    logger.info("Guardado Parquet nacional: %s (%d registros)", pq_path, len(df_all_pois))

                    if ROOT_PROCESSED_DIR.exists():
                        root_pq = ROOT_PROCESSED_DIR / "pois_espana_osm.parquet"
                        df_all_pois.to_parquet(root_pq, index=False, engine="pyarrow")
                        logger.info("Sincronizado con raíz: %s", root_pq)
                else:
                    reporter.record("POIs_OSM_Polygon", "Nacional", "No se recopilaron POIs provinciales.")

        except Exception as exc:
            logger.error("Error en FASE 15 POIs OSM: %s", exc)
            reporter.record("POIs_OSM_Polygon", "Nacional", str(exc), exc)

    reporter.save(DATA_PROCESSED_DIR)
    logger.info("Pipeline completado con éxito. Archivos en: %s", DATA_PROCESSED_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de datos turísticos crudos de España")
    parser.add_argument("--sources", nargs="+", default=None)
    parser.add_argument("--periodos-ine", type=int, default=24)
    parser.add_argument("--max-pages-datosgob", type=int, default=None, help="Límite opcional de páginas para datos.gob.es")
    parser.add_argument("--cod-prov", nargs="+", default=None, help="Códigos provinciales específicos a extraer (ej: 40 28)")
    args = parser.parse_args()
    run_pipeline(
        sources=args.sources,
        n_periodos_ine=args.periodos_ine,
        max_pages_datosgob=args.max_pages_datosgob,
        cod_prov=args.cod_prov,
    )


if __name__ == "__main__":
    main()

