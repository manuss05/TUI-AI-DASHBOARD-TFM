"""
Orquestador del pipeline de extracción — Cobertura Nacional de España (100% Territorio Español).

Fases:
  0. Inicialización       — Log de sesión, reporter, directorios.
  1. Maestro Provincias   — 52 provincias y ciudades autónomas oficiales de España (INE Tabla 2852).
  2. Maestro Municipios   — 8.138 municipios del censo oficial de España (INE Tabla 29005).
  3. Flujos INE Prov      — EOH mensual para todas las provincias y CCAA de España (INE Tabla 2074).
  4. Flujos INE Localidad — EOH mensual para los 113 puntos turísticos de España (INE Tabla 2078).
  5. Geocodificación      — CartoCiudad (cod_ine real) para capitales y puntos turísticos.
  6. Oferta OSM           — POIs turísticos vía Overpass.
  7. TripAdvisor          — POIs con rating (si TRIPADVISOR_API_KEY está configurada).
  8. Datos Abiertos       — Catálogo de datasets turísticos nacionales (datos.gob.es).
  9. Cierre               — Guarda reporte_fallos.csv y resumen de ejecución.

Convención de nombres de columna:  Origen.NombreColumna
Encoding de todos los CSV:          UTF-8 con BOM (utf-8-sig)
"""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from config.settings import DATA_PROCESSED_DIR, PROVINCIAS_ESPANA
from src.utils.logger import get_logger, init_session_log
from src.utils.csv_writer import save_table
from src.utils.reporter import FailureReporter

from src.extractors.ign_extractor import IGNExtractor
from src.extractors.osm_extractor import OSMExtractor
from src.extractors.ine_extractor import INEExtractor
from src.extractors.tripadvisor_extractor import TripAdvisorExtractor
from src.extractors.datosgob_extractor import DatosGobExtractor

logger = get_logger(__name__)


def _cod_ine_provisional(nombre: str) -> str:
    """Hash temporal de 8 caracteres usado como fallback de cod_ine."""
    return "PROV_" + hashlib.md5(nombre.encode("utf-8")).hexdigest()[:8]


def _banner(texto: str) -> None:
    """Imprime un encabezado de fase en consola y en el log."""
    logger.info("")
    logger.info("=" * 65)
    logger.info("  %s", texto)
    logger.info("=" * 65)


def run_pipeline(
    sources: list[str] | None = None,
    n_periodos_ine: int = 12,
) -> None:
    """
    Ejecuta el pipeline de extracción sobre todo el territorio español.
    """
    all_sources = {
        "provincias",
        "municipios_espana",
        "flujo_ine_provincia",
        "flujo_ine_localidad",
        "localidades",
        "turismo_oferta_osm",
        "tripadvisor",
        "datosgob",
    }
    sources = set(sources) if sources else all_sources

    # ── FASE 0: Inicialización ──────────────────────────────────────────
    _banner("FASE 0 · Inicialización del pipeline (Ámbito: España Completa)")

    log_path = init_session_log()
    logger.info("Log de sesión → %s", log_path)
    logger.info("Fuentes activas: %s", ", ".join(sorted(sources)))
    logger.info("Períodos históricos INE a descargar: %d meses", n_periodos_ine)

    reporter = FailureReporter()
    ine      = INEExtractor()
    ign      = IGNExtractor()
    osm      = OSMExtractor()

    # ── FASE 1: Maestro de Provincias de España (INE Tabla 2852) ────────
    df_prov = pd.DataFrame()
    if "provincias" in sources:
        _banner("FASE 1 · Maestro de las 52 Provincias y Ciudades Autónomas de España (INE Tabla 2852)")
        try:
            df_ine_pob_prov = ine.get_maestro_provincias(n_ultimos=1)
            if not df_ine_pob_prov.empty:
                # Cruzar con metadatos oficiales de PROVINCIAS_ESPANA
                df_meta = pd.DataFrame(PROVINCIAS_ESPANA)
                
                # Normalización de nombres para merge robusto
                df_prov = df_ine_pob_prov.copy()
                
                # Mapear metadatos por proximidad de nombre o asignación
                cod_prov_map = {p["nombre"].lower(): p["cod_prov"] for p in PROVINCIAS_ESPANA}
                capital_map  = {p["nombre"].lower(): p["capital"] for p in PROVINCIAS_ESPANA}
                ccaa_map     = {p["nombre"].lower(): p["ccaa"] for p in PROVINCIAS_ESPANA}

                def _find_meta(prov_name: str, mapping: dict) -> str:
                    pn = prov_name.lower().strip()
                    for k, v in mapping.items():
                        if k in pn or pn in k:
                            return v
                    return ""

                df_prov["_meta.cod_prov"] = df_prov["INE_Pob_PROV.provincia"].apply(lambda x: _find_meta(x, cod_prov_map))
                df_prov["_meta.capital"]  = df_prov["INE_Pob_PROV.provincia"].apply(lambda x: _find_meta(x, capital_map))
                df_prov["_meta.ccaa"]     = df_prov["INE_Pob_PROV.provincia"].apply(lambda x: _find_meta(x, ccaa_map))
                df_prov["_meta.fecha_extraccion"] = datetime.utcnow().isoformat()

                save_table(df_prov, "provincias", DATA_PROCESSED_DIR)
            else:
                reporter.record("INE_Pob_PROV", "Nacional", "La descarga de provincias devolvió un DataFrame vacío.")
        except Exception as exc:
            reporter.record("INE_Pob_PROV", "Nacional", str(exc), exc)

    # ── FASE 2: Maestro de Todos los Municipios de España (INE Tabla 29005)
    if "municipios_espana" in sources:
        _banner("FASE 2 · Censo Oficial de los 8.138 Municipios de España (INE Tabla 29005)")
        try:
            df_ine_mun_pob = ine.get_maestro_municipios(n_ultimos=1)
            if not df_ine_mun_pob.empty:
                save_table(df_ine_mun_pob, "municipios_espana", DATA_PROCESSED_DIR)
            else:
                reporter.record("INE_Pob_MUN", "Nacional", "La descarga de municipios devolvió un DataFrame vacío.")
        except Exception as exc:
            reporter.record("INE_Pob_MUN", "Nacional", str(exc), exc)

    # ── FASE 3: Flujos Turísticos INE — Provincias y CCAA (Tabla 2074) ───
    if "flujo_ine_provincia" in sources:
        _banner("FASE 3 · Flujos Turísticos EOH por Provincias y CCAA de España (INE Tabla 2074)")
        try:
            df_eoh_prov = ine.get_eoh_provincias(n_ultimos=n_periodos_ine)
            if not df_eoh_prov.empty:
                save_table(df_eoh_prov, "flujo_ine_provincia", DATA_PROCESSED_DIR)
            else:
                reporter.record("INE_EOH_PROV", "Nacional", "La descarga de EOH provincial devolvió un DataFrame vacío.")
        except Exception as exc:
            reporter.record("INE_EOH_PROV", "Nacional", str(exc), exc)

    # ── FASE 4: Flujos Turísticos INE — Localidades Turísticas (Tabla 2078)
    if "flujo_ine_localidad" in sources:
        _banner("FASE 4 · Flujos Turísticos EOH por Localidad Turística (113 Puntos) (INE Tabla 2078)")
        try:
            df_eoh_mun = ine.get_eoh_municipios(n_ultimos=n_periodos_ine)
            if not df_eoh_mun.empty:
                save_table(df_eoh_mun, "flujo_ine_localidad", DATA_PROCESSED_DIR)
            else:
                reporter.record("INE_EOH_MUN", "Nacional", "La descarga de EOH municipal devolvió un DataFrame vacío.")
        except Exception as exc:
            reporter.record("INE_EOH_MUN", "Nacional", str(exc), exc)

    # ── FASE 5: Geocodificación de Capitales Provinciales y Puntos Clave ──
    localidades_rows: list[dict] = []
    if "localidades" in sources:
        _banner("FASE 5 · Geocodificación oficial CartoCiudad/IGN de Capitales y Puntos Clave")
        
        # Geocodificar las 52 capitales provinciales
        targets = [{"nombre": p["capital"], "provincia": p["nombre"], "ccaa": p["ccaa"]} for p in PROVINCIAS_ESPANA]
        
        for t in tqdm(targets, desc="Geocodificando Provincias"):
            nombre = t["nombre"]
            geo = ign.geocode(nombre)
            if geo is None:
                nom_geo = osm.geocode_nominatim(nombre)
                if nom_geo:
                    cod_ine = _cod_ine_provisional(nombre)
                    geo = {
                        "CartoCiudad.cod_ine":          cod_ine,
                        "CartoCiudad.nombre_municipio": nombre,
                        "CartoCiudad.provincia":        t.get("provincia", ""),
                        "CartoCiudad.ccaa":             t.get("ccaa", ""),
                        "CartoCiudad.latitud":          nom_geo["OSM_Nominatim.latitud"],
                        "CartoCiudad.longitud":         nom_geo["OSM_Nominatim.longitud"],
                        "_meta.fuente_geocod":          "OSM_Nominatim_fallback",
                        "_meta.fecha_extraccion":       nom_geo["_meta.fecha_extraccion"],
                    }
                else:
                    reporter.record("IGN+OSM_Nominatim", nombre, "No se pudo geocodificar la capital.")
                    continue

            fila = dict(geo)
            fila["_meta.cod_ine_clave"]    = fila["CartoCiudad.cod_ine"]
            fila["_meta.nombre_municipio"] = nombre
            if not fila.get("CartoCiudad.provincia"):
                fila["CartoCiudad.provincia"] = t.get("provincia", "")
            if not fila.get("CartoCiudad.ccaa"):
                fila["CartoCiudad.ccaa"] = t.get("ccaa", "")

            localidades_rows.append(fila)

        if localidades_rows:
            save_table(pd.DataFrame(localidades_rows), "localidades", DATA_PROCESSED_DIR)

    # ── FASE 6: Oferta OSM (POIs Turísticos) ─────────────────────────────
    if "turismo_oferta_osm" in sources:
        _banner("FASE 6 · Oferta Turística de Capitales (OSM Overpass — POIs)")
        oferta_osm_rows: list[dict] = []
        base = localidades_rows if localidades_rows else [
            {"_meta.cod_ine_clave": _cod_ine_provisional(p["capital"]),
             "_meta.nombre_municipio": p["capital"]}
            for p in PROVINCIAS_ESPANA
        ]

        for fila in tqdm(base, desc="POIs OSM"):
            nombre  = fila["_meta.nombre_municipio"]
            cod_ine = fila["_meta.cod_ine_clave"]
            lat     = fila.get("CartoCiudad.latitud")
            lon     = fila.get("CartoCiudad.longitud")
            try:
                counts = osm.poi_counts(nombre, lat=lat, lon=lon)
                counts["_meta.cod_ine_clave"]    = cod_ine
                counts["_meta.nombre_municipio"] = nombre
                oferta_osm_rows.append(counts)

                poi_keys = ["OSM_Overpass.num_hoteles", "OSM_Overpass.num_restaurantes",
                            "OSM_Overpass.num_atracciones", "OSM_Overpass.num_museos"]
                if all(counts.get(k) is None for k in poi_keys):
                    reporter.record(
                        "OSM_Overpass", nombre,
                        "Overpass devolvió valores nulos (rate-limit o timeout)."
                    )
            except Exception as exc:
                reporter.record("OSM_Overpass", nombre, str(exc), exc)

        if oferta_osm_rows:
            save_table(pd.DataFrame(oferta_osm_rows), "oferta_osm", DATA_PROCESSED_DIR)

    # ── FASE 7: TripAdvisor ──────────────────────────────────────────────
    if "tripadvisor" in sources:
        _banner("FASE 7 · POIs TripAdvisor (requiere API key)")
        ta = TripAdvisorExtractor()
        if not ta.is_active:
            reporter.record_skip(
                "TripAdvisor",
                "TRIPADVISOR_API_KEY no configurada en .env. Solicita la clave en tripadvisor.com/developers.",
            )

    # ── FASE 8: Datos Abiertos Nacionales (datos.gob.es) ────────────────
    if "datosgob" in sources:
        _banner("FASE 8 · Catálogo Nacional de Datasets Abiertos (datos.gob.es)")
        datosgob = DatosGobExtractor()
        keywords = ["turismo", "ocupación hotelera", "turismo rural", "alojamientos turísticos"]
        datosgob_frames: list[pd.DataFrame] = []

        for kw in keywords:
            try:
                df_gob = datosgob.search_datasets(kw, limit=20)
                if not df_gob.empty:
                    datosgob_frames.append(df_gob)
                else:
                    reporter.record(
                        "DatosGob", kw,
                        f"Búsqueda '{kw}' en datos.gob.es devolvió DataFrame vacío o error."
                    )
            except Exception as exc:
                reporter.record("DatosGob", kw, str(exc), exc)

        if datosgob_frames:
            df_total_gob = pd.concat(datosgob_frames, ignore_index=True)
            if "DatosGob.url_recurso" in df_total_gob.columns:
                df_total_gob = df_total_gob.drop_duplicates(subset=["DatosGob.url_recurso"])
            save_table(df_total_gob, "datosgob_catalogo", DATA_PROCESSED_DIR)

    # ── FASE 9: Cierre y Reporte de Fallos ───────────────────────────────
    _banner("FASE 9 · Cierre del pipeline y Generación de Reporte")

    reporter.save(DATA_PROCESSED_DIR)
    print(reporter.summary())

    logger.info("Pipeline nacional completado.")
    logger.info("Archivos CSV generados en: %s", DATA_PROCESSED_DIR)
    logger.info("Log de sesión guardado en: %s", log_path)


# ── Punto de entrada CLI ───────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline Nacional de Extracción de Datos Turísticos de España (TFM)"
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=None,
        metavar="FUENTE",
        help=(
            "Fuentes a ejecutar. Opciones: provincias, municipios_espana, "
            "flujo_ine_provincia, flujo_ine_localidad, localidades, "
            "turismo_oferta_osm, tripadvisor, datosgob. "
            "Por defecto ejecuta todas."
        ),
    )
    parser.add_argument(
        "--periodos-ine",
        type=int,
        default=12,
        metavar="N",
        help="Número de períodos mensuales a descargar del INE (por defecto: 12).",
    )
    args = parser.parse_args()
    run_pipeline(sources=args.sources, n_periodos_ine=args.periodos_ine)


if __name__ == "__main__":
    main()
