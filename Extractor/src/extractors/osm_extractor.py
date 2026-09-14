"""Extractor de OpenStreetMap (Nominatim y Overpass) en formato crudo."""
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Optional

import requests

from config.settings import USER_AGENT
from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_MIRRORS = [
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]
_HEADERS = {"User-Agent": USER_AGENT}


class OSMExtractor:
    """Extractor OSM sin transformaciones de datos."""

    def __init__(self) -> None:
        self.client = HttpClient(min_interval=1.0)
        self._mirror_idx = 0

    def geocode_nominatim(self, query: str) -> Optional[dict]:
        """Devuelve la respuesta completa de Nominatim sin truncar."""
        try:
            params = {"q": query, "format": "json", "limit": 1}
            resp = self.client.get(NOMINATIM_URL, params=params)
            results = resp.json()
            if not results:
                return None
            r = results[0]
            return {
                "query": query,
                "place_id": r.get("place_id"),
                "osm_type": r.get("osm_type", ""),
                "osm_id": r.get("osm_id"),
                "lat": r.get("lat"),
                "lon": r.get("lon"),
                "display_name": r.get("display_name", ""),
                "class": r.get("class", ""),
                "type": r.get("type", ""),
                "importance": r.get("importance"),
                "raw_json": json.dumps(r, ensure_ascii=False),
                "_meta.fecha_extraccion": datetime.now().isoformat(),
            }
        except Exception as exc:
            logger.warning("[OSM_Nominatim] Error en '%s': %s", query, exc)
            return None

    def query_overpass_counts(
        self, query_name: str, lat: float, lon: float, radio_metros: int = 8000
    ) -> dict:
        """Ejecuta consulta de conteo en Overpass y devuelve las respuestas crudas de los elementos."""
        query = f"""
        [out:json][timeout:25];
        (
          node["tourism"="hotel"](around:{radio_metros}, {lat}, {lon});
          way["tourism"="hotel"](around:{radio_metros}, {lat}, {lon});
        )->.hoteles;
        (
          node["amenity"="restaurant"](around:{radio_metros}, {lat}, {lon});
          way["amenity"="restaurant"](around:{radio_metros}, {lat}, {lon});
        )->.restaurantes;
        (
          node["tourism"="attraction"](around:{radio_metros}, {lat}, {lon});
          way["tourism"="attraction"](around:{radio_metros}, {lat}, {lon});
        )->.atracciones;
        (
          node["tourism"="museum"](around:{radio_metros}, {lat}, {lon});
          way["tourism"="museum"](around:{radio_metros}, {lat}, {lon});
        )->.museos;
        .hoteles      out count;
        .restaurantes out count;
        .atracciones  out count;
        .museos       out count;
        """
        num_mirrors = len(OVERPASS_MIRRORS)
        start_idx = self._mirror_idx
        self._mirror_idx = (self._mirror_idx + 1) % num_mirrors
        ordered_mirrors = [OVERPASS_MIRRORS[(start_idx + i) % num_mirrors] for i in range(num_mirrors)]

        for mirror in ordered_mirrors:
            try:
                resp = requests.post(mirror, data={"data": query}, headers=_HEADERS, timeout=25.0)
                if resp.status_code == 200:
                    elements = resp.json().get("elements", [])
                    return {
                        "query_name": query_name,
                        "lat": lat,
                        "lon": lon,
                        "radio_metros": radio_metros,
                        "mirror_usado": mirror,
                        "elements_raw_json": json.dumps(elements, ensure_ascii=False),
                        "_meta.fecha_extraccion": datetime.now().isoformat(),
                    }
                elif resp.status_code in (429, 502, 503, 504):
                    logger.warning("[OSM_Overpass] Mirror %s devolvió HTTP %s para '%s', intentando mirror alternativo...", mirror, resp.status_code, query_name)
                    time.sleep(1.0)
            except Exception as exc:
                logger.warning("[OSM_Overpass] Error en mirror %s para '%s': %s", mirror, query_name, exc)
                continue

        logger.error("[OSM_Overpass] Todos los mirrors fallaron para '%s'", query_name)
        return {
            "query_name": query_name,
            "lat": lat,
            "lon": lon,
            "radio_metros": radio_metros,
            "mirror_usado": "FAILED",
            "elements_raw_json": "[]",
            "_meta.fecha_extraccion": datetime.now().isoformat(),
        }

    @staticmethod
    def parse_osm_dataframe(df_raw: "pd.DataFrame") -> "pd.DataFrame":
        """
        Parsea el DataFrame crudo de oferta_osm.csv y genera una tabla tabular con formato
        compatible con eoh_oferta_provincias (COD_PROV, PROVINCIA, etc.).
        """
        import pandas as pd
        from config.settings import PROVINCIAS_ESPANA
        cap_map = {p["capital"]: p for p in PROVINCIAS_ESPANA}

        records = []
        for _, row in df_raw.iterrows():
            cap = row.get("query_name", "")
            prov_info = cap_map.get(cap, {})
            cod_prov = str(prov_info.get("cod_prov", "")).zfill(2)
            provincia = prov_info.get("nombre", "")
            ccaa = prov_info.get("ccaa", "")

            raw_json = row.get("elements_raw_json", "[]")
            elements = []
            if isinstance(raw_json, str) and raw_json.strip():
                try:
                    elements = json.loads(raw_json)
                except Exception:
                    elements = []
            elif isinstance(raw_json, list):
                elements = raw_json

            hoteles = int(elements[0].get("tags", {}).get("total", 0)) if len(elements) > 0 else 0
            restaurantes = int(elements[1].get("tags", {}).get("total", 0)) if len(elements) > 1 else 0
            atracciones = int(elements[2].get("tags", {}).get("total", 0)) if len(elements) > 2 else 0
            museos = int(elements[3].get("tags", {}).get("total", 0)) if len(elements) > 3 else 0
            total_poi = hoteles + restaurantes + atracciones + museos

            records.append({
                "COD_PROV": cod_prov,
                "PROVINCIA": provincia,
                "CAPITAL": cap,
                "COMUNIDAD_AUTONOMA": ccaa,
                "hoteles_osm": hoteles,
                "restaurantes_osm": restaurantes,
                "atracciones_osm": atracciones,
                "museos_osm": museos,
                "total_poi_osm": total_poi,
                "lat": row.get("lat"),
                "lon": row.get("lon"),
                "radio_metros": row.get("radio_metros", 8000),
                "_meta.fecha_extraccion": row.get("_meta.fecha_extraccion", ""),
            })

        return pd.DataFrame(records).sort_values("COD_PROV").reset_index(drop=True)

    def extract_provincia_pois_polygon(
        self,
        prov_geom,
        cod_prov: str,
        prov_nombre: str,
        timeout_query: int = 90,
    ) -> "pd.DataFrame":
        """
        Descarga los POIs turísticos de OpenStreetMap dentro de la caja envolvente de la provincia
        y filtra exactamente mediante intersección espacial con el polígono provincial.
        Excluye expresamente teléfono y web. Genera columna geometry_wkt.
        """
        import geopandas as gpd
        import pandas as pd

        minx, miny, maxx, maxy = prov_geom.bounds

        query = f"""
        [out:json][timeout:{timeout_query}];
        (
          node["tourism"~"hotel|hostel|guest_house|motel|camp_site|apartment|chalet|museum|gallery|artwork|attraction|theme_park|viewpoint|zoo|aquarium"]({miny},{minx},{maxy},{maxx});
          way["tourism"~"hotel|hostel|guest_house|motel|camp_site|apartment|chalet|museum|gallery|artwork|attraction|theme_park|viewpoint|zoo|aquarium"]({miny},{minx},{maxy},{maxx});
          node["amenity"~"restaurant|bar|cafe"]({miny},{minx},{maxy},{maxx});
          way["amenity"~"restaurant|bar|cafe"]({miny},{minx},{maxy},{maxx});
        );
        out center;
        """

        num_mirrors = len(OVERPASS_MIRRORS)
        start_idx = self._mirror_idx
        self._mirror_idx = (self._mirror_idx + 1) % num_mirrors
        ordered_mirrors = [OVERPASS_MIRRORS[(start_idx + i) % num_mirrors] for i in range(num_mirrors)]

        elements = []
        mirror_exitoso = None

        for mirror in ordered_mirrors:
            try:
                resp = requests.post(
                    mirror,
                    data={"data": query},
                    headers=_HEADERS,
                    timeout=float(timeout_query + 15),
                )
                if resp.status_code == 200:
                    elements = resp.json().get("elements", [])
                    mirror_exitoso = mirror
                    break
                elif resp.status_code in (429, 502, 503, 504):
                    logger.warning(
                        "[OSM_Polygon] Mirror %s devolvió HTTP %s para provincia '%s', probando otro mirror...",
                        mirror,
                        resp.status_code,
                        prov_nombre,
                    )
                    time.sleep(1.5)
            except Exception as exc:
                logger.warning("[OSM_Polygon] Error en mirror %s para '%s': %s", mirror, prov_nombre, exc)
                continue

        if mirror_exitoso is None:
            logger.error("[OSM_Polygon] Fallaron todos los mirrors para la provincia '%s'", prov_nombre)
            return pd.DataFrame()

        logger.info(
            "[OSM_Polygon] %s: %d POIs en BBOX rectangular (Mirror: %s)",
            prov_nombre,
            len(elements),
            mirror_exitoso,
        )

        rows = []
        for el in elements:
            tags = el.get("tags", {})
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")

            if lat is None or lon is None:
                continue

            tourism = tags.get("tourism")
            amenity = tags.get("amenity")

            # Clasificación normalizada macro
            if tourism in ("hotel", "hostel", "guest_house", "motel", "camp_site", "apartment", "chalet"):
                categoria = "Alojamiento"
                subtipo = tourism
            elif amenity in ("restaurant", "bar", "cafe"):
                categoria = "Restauracion"
                subtipo = amenity
            elif tourism in ("museum", "gallery", "artwork"):
                categoria = "Cultura y Patrimonio"
                subtipo = tourism
            elif tourism in ("attraction", "theme_park", "viewpoint", "zoo", "aquarium"):
                categoria = "Ocio y Naturaleza"
                subtipo = tourism
            elif tourism:
                categoria = "Turismo General"
                subtipo = tourism
            else:
                categoria = "Servicios Turisticos"
                subtipo = amenity or "desconocido"

            nombre = tags.get("name", "Sin nombre")
            estrellas = tags.get("stars")
            capacidad = tags.get("capacity") or tags.get("rooms")
            municipio = tags.get("addr:city")
            codigo_postal = tags.get("addr:postcode")

            rows.append({
                "osm_id": el.get("id"),
                "osm_type": el.get("type"),
                "categoria": categoria,
                "subtipo": subtipo,
                "nombre": nombre,
                "cod_prov": str(cod_prov).zfill(2),
                "provincia": prov_nombre,
                "latitud": float(lat),
                "longitud": float(lon),
                "estrellas": estrellas,
                "capacidad": capacidad,
                "municipio": municipio,
                "codigo_postal": codigo_postal,
            })

        if not rows:
            return pd.DataFrame()

        df_raw = pd.DataFrame(rows)

        # Filtrado espacial con polígono de la provincia
        gdf_pois = gpd.GeoDataFrame(
            df_raw,
            geometry=gpd.points_from_xy(df_raw["longitud"], df_raw["latitud"]),
            crs="EPSG:4326",
        )

        gdf_inside = gdf_pois[gdf_pois.intersects(prov_geom)].copy()
        gdf_inside["geometry_wkt"] = gdf_inside.geometry.to_wkt()

        df_final = gdf_inside.drop(columns=["geometry"]).reset_index(drop=True)
        logger.info(
            "[OSM_Polygon] %s: %d POIs dentro del polígono oficial provincial",
            prov_nombre,
            len(df_final),
        )
        return df_final
