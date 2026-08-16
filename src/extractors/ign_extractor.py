"""
Extractor del IGN (Instituto Geográfico Nacional) vía CartoCiudad,
su geocodificador oficial. Portal de referencia: https://www.cartociudad.es/

AVISO: no he podido verificar en vivo (este entorno no tiene salida a
Internet) los nombres exactos de parámetros del endpoint REST actual de
CartoCiudad. Antes de usar en producción, confirma el contrato del
endpoint en https://www.cartociudad.es/webapi/index.html. La función
geocode() está escrita según la especificación documentada, pero incluye
manejo de errores explícito para que un cambio de formato no rompa el
pipeline en silencio.

Como respaldo robusto y bien documentado se usa OSM Nominatim
(ign_extractor -> geocode ; osm_extractor -> geocode_nominatim), que sí es
estable y de uso gratuito respetando 1 petición/segundo.
"""
from datetime import datetime
from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

CARTOCIUDAD_URL = "https://www.cartociudad.es/geocoder/api/geocoder/findJsonp"


class IGNExtractor:
    def __init__(self):
        self.client = HttpClient()

    def geocode(self, query: str) -> dict | None:
        """
        Geocodifica un municipio usando CartoCiudad (IGN).
        Devuelve dict con lat/lon o None si falla (usar OSM como fallback).
        """
        try:
            resp = self.client.get(CARTOCIUDAD_URL, params={"q": query, "type": "json"})
            data = resp.json()
            # La estructura exacta puede variar; se maneja de forma defensiva.
            if isinstance(data, list) and data:
                candidato = data[0]
            elif isinstance(data, dict):
                candidato = data
            else:
                return None

            lat = candidato.get("lat") or candidato.get("y")
            lon = candidato.get("lng") or candidato.get("lon") or candidato.get("x")
            if lat is None or lon is None:
                return None

            return {
                "query": query,
                "latitud": float(lat),
                "longitud": float(lon),
                "fuente": "IGN-CartoCiudad",
                "fecha_extraccion": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.warning("Fallo geocodificando '%s' con CartoCiudad: %s. Usa el fallback OSM.", query, e)
            return None
