"""
Orquestador del pipeline de extracción.

Recorre la lista de municipios objetivo y, para cada uno, llama a los
extractores disponibles, acumulando resultados por TABLA (no por
municipio), de forma que al final se escribe un CSV por tabla del modelo
relacional (ver src/schema.py). Cada extractor es independiente: si uno
falla para un municipio, se registra el error y se continúa con el resto,
para que una fuente caída no tumbe todo el pipeline.
"""
import argparse
from datetime import datetime
import hashlib
import pandas as pd
from tqdm import tqdm

from config.settings import DATA_PROCESSED_DIR, MUNICIPIOS_DEMO
from src.utils.csv_writer import save_table
from src.utils.logger import get_logger
from src.extractors.ign_extractor import IGNExtractor
from src.extractors.osm_extractor import OSMExtractor
from src.extractors.tripadvisor_extractor import TripAdvisorExtractor
from src.extractors.social_reddit_extractor import RedditExtractor

logger = get_logger(__name__)


def _cod_ine_provisional(nombre_municipio: str) -> str:
    """
    Genera un identificador ESTABLE provisional a partir del nombre,
    para poder relacionar tablas entre sí durante el desarrollo.
    SUSTITUIR por el código INE real (5 dígitos) en producción: puedes
    obtenerlo del "Callejero"/Nomenclátor oficial del INE o de la
    relación de municipios de datos.gob.es. Dejarlo aquí evita romper las
    claves foráneas mientras integras esa fuente.
    """
    return hashlib.md5(nombre_municipio.encode("utf-8")).hexdigest()[:8]


def run_pipeline(municipios: list[dict] | None = None, sources: list[str] | None = None):
    municipios = municipios or MUNICIPIOS_DEMO
    sources = sources or ["localidades", "turismo_oferta_osm", "tripadvisor_pois", "redes_sociales_buzz"]

    ign = IGNExtractor()
    osm = OSMExtractor()

    localidades_rows = []
    oferta_osm_rows = []
    tripadvisor_rows = []
    social_rows = []

    for m in tqdm(municipios, desc="Extrayendo municipios"):
        nombre = m["nombre"]
        cod_ine = m.get("cod_ine") or _cod_ine_provisional(nombre)

        # --- Geolocalización: IGN primero, OSM Nominatim como respaldo ---
        if "localidades" in sources:
            geo = ign.geocode(nombre) or osm.geocode_nominatim(nombre)
            if geo:
                localidades_rows.append({
                    "cod_ine": cod_ine,
                    "nombre_municipio": nombre,
                    "provincia": m.get("provincia"),
                    "comunidad_autonoma": m.get("ccaa"),
                    "latitud": geo["latitud"],
                    "longitud": geo["longitud"],
                    "superficie_km2": None,  # completar con INE/IGN si se requiere
                    "fuente": geo["fuente"],
                    "fecha_extraccion": datetime.utcnow().isoformat(),
                })
            else:
                logger.error("No se pudo geolocalizar '%s' con ninguna fuente", nombre)

        # --- Oferta turística objetiva vía OSM ---
        if "turismo_oferta_osm" in sources:
            try:
                counts = osm.poi_counts(nombre)
                counts["cod_ine"] = cod_ine
                oferta_osm_rows.append(counts)
            except Exception as e:
                logger.error("Fallo extrayendo POIs OSM de '%s': %s", nombre, e)

        # --- TripAdvisor (requiere API key) ---
        if "tripadvisor_pois" in sources:
            try:
                ta = TripAdvisorExtractor()
                if ta.api_key:
                    df_ta = ta.get_pois_for_municipio(nombre, cod_ine)
                    if not df_ta.empty:
                        tripadvisor_rows.append(df_ta)
            except Exception as e:
                logger.error("Fallo extrayendo TripAdvisor de '%s': %s", nombre, e)

        # --- Reddit (requiere credenciales) ---
        if "redes_sociales_buzz" in sources:
            try:
                rd = RedditExtractor()
                df_rd = rd.count_mentions(nombre, cod_ine)
                if not df_rd.empty:
                    social_rows.append(df_rd)
            except Exception as e:
                logger.error("Fallo extrayendo Reddit de '%s': %s", nombre, e)

    # --- Persistencia en formato relacional (un CSV por tabla) ---
    if localidades_rows:
        save_table(pd.DataFrame(localidades_rows), "localidades", DATA_PROCESSED_DIR)
    if oferta_osm_rows:
        save_table(pd.DataFrame(oferta_osm_rows), "turismo_oferta_osm", DATA_PROCESSED_DIR)
    if tripadvisor_rows:
        save_table(pd.concat(tripadvisor_rows, ignore_index=True), "tripadvisor_pois", DATA_PROCESSED_DIR)
    if social_rows:
        save_table(pd.concat(social_rows, ignore_index=True), "redes_sociales_buzz", DATA_PROCESSED_DIR)

    logger.info("Pipeline finalizado. Revisa los CSV en %s", DATA_PROCESSED_DIR)


def main():
    parser = argparse.ArgumentParser(description="Pipeline de extracción de datos turísticos por municipio")
    parser.add_argument(
        "--sources", nargs="+",
        default=["localidades", "turismo_oferta_osm", "tripadvisor_pois", "redes_sociales_buzz"],
        help="Subconjunto de fuentes a ejecutar",
    )
    args = parser.parse_args()
    run_pipeline(sources=args.sources)


if __name__ == "__main__":
    main()
