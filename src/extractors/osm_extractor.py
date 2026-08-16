"""
Extractor de OpenStreetMap.

Dos servicios, ambos gratuitos y sin necesidad de clave, pero con
políticas de uso estrictas que este cliente respeta (1 req/seg, User-Agent
identificable — ver config/settings.py):

1. Nominatim (geocodificación): https://nominatim.org/release-docs/latest/api/Search/
2. Overpass API (consulta de POIs turísticos): https://overpass-api.de/

Sirven como fuente de "oferta turística objetiva" a nivel de municipio
(número de hoteles, restaurantes, museos, atracciones), algo que ni INE ni
CartoCiudad ofrecen desagregado por localidad.
"""
from datetime import datetime
from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


class OSMExtractor:
    def __init__(self):
        # Nominatim exige explícitamente min. 1 segundo entre peticiones.
        self.client = HttpClient(min_interval=1.1)

    def geocode_nominatim(self, query: str, country: str = "España") -> dict | None:
        params = {"q": f"{query}, {country}", "format": "json", "limit": 1}
        resp = self.client.get(NOMINATIM_URL, params=params)
        results = resp.json()
        if not results:
            logger.warning("Nominatim no encontró resultados para '%s'", query)
            return None
        r = results[0]
        return {
            "query": query,
            "latitud": float(r["lat"]),
            "longitud": float(r["lon"]),
            "fuente": "OSM-Nominatim",
            "fecha_extraccion": datetime.utcnow().isoformat(),
        }

    def poi_counts(self, municipio: str) -> dict:
        """
        Cuenta POIs de interés turístico dentro del límite administrativo
        del municipio, usando Overpass QL.
        """
        query = f"""
        [out:json][timeout:60];
        area["name"="{municipio}"]["boundary"="administrative"]->.a;
        (
          node["tourism"="hotel"](area.a);
          way["tourism"="hotel"](area.a);
        )->.hoteles;
        (
          node["amenity"="restaurant"](area.a);
          way["amenity"="restaurant"](area.a);
        )->.restaurantes;
        (
          node["tourism"="attraction"](area.a);
          way["tourism"="attraction"](area.a);
        )->.atracciones;
        (
          node["tourism"="museum"](area.a);
          way["tourism"="museum"](area.a);
        )->.museos;
        (.hoteles; .restaurantes; .atracciones; .museos;)->.todos;
        .hoteles out count;
        .restaurantes out count;
        .atracciones out count;
        .museos out count;
        """
        try:
            resp = self.client.post(OVERPASS_URL, data={"data": query})
            data = resp.json()
            counts = [int(el["tags"]["total"]) for el in data.get("elements", []) if el.get("type") == "count"]
            # El orden de salida sigue el orden de las líneas "out count;"
            keys = ["num_hoteles", "num_restaurantes", "num_atracciones_turisticas", "num_museos"]
            result = dict(zip(keys, counts + [0] * (len(keys) - len(counts))))
        except Exception as e:
            logger.warning("Fallo consultando Overpass para '%s': %s", municipio, e)
            result = {"num_hoteles": None, "num_restaurantes": None,
                       "num_atracciones_turisticas": None, "num_museos": None}

        result["num_alojamientos"] = result.get("num_hoteles")
        result["fuente"] = "OSM-Overpass"
        result["fecha_extraccion"] = datetime.utcnow().isoformat()
        return result
