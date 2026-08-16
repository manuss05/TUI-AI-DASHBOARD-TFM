"""
Modelo relacional del proyecto.

Tabla central: `localidades`, indexada por `cod_ine` (código INE del municipio,
clave estable y estándar en toda la estadística oficial española).
El resto de tablas son "largas" (una fila por localidad+año, o por
localidad+POI) y se relacionan con `localidades` mediante `cod_ine`,
permitiendo hacer JOIN directo en pandas/SQL para el dashboard.

IMPORTANTE sobre granularidad:
Los flujos turísticos oficiales del INE (FRONTUR/EGATUR, Encuesta de
Ocupación en Alojamientos Turísticos) se publican sobre todo a nivel de
provincia / comunidad autónoma / punto de entrada, NO a nivel de municipio.
Por eso `turismo_flujo_ine` usa `cod_ambito` + `nivel_ambito` en lugar de
`cod_ine`. Para aproximar el "flujo turístico" a nivel de municipio hay que
recurrir a proxies (densidad de alojamiento/POIs en OSM, reseñas de
TripAdvisor, menciones en redes) — de ahí las tablas turismo_oferta_osm,
tripadvisor_pois y redes_sociales_buzz.
"""

TABLE_SCHEMAS = {
    "localidades": [
        "cod_ine", "nombre_municipio", "provincia", "comunidad_autonoma",
        "latitud", "longitud", "superficie_km2", "fuente", "fecha_extraccion",
    ],
    "demografia": [
        "cod_ine", "anio", "poblacion_total", "poblacion_hombres", "poblacion_mujeres",
        "densidad_poblacion_hab_km2", "fuente", "fecha_extraccion",
    ],
    "renta": [
        "cod_ine", "anio", "renta_media_neta_hogar", "renta_media_neta_persona",
        "fuente", "fecha_extraccion",
    ],
    "turismo_flujo_ine": [
        "nivel_ambito", "cod_ambito", "nombre_ambito", "anio", "mes",
        "viajeros_nacionales", "viajeros_internacionales",
        "pernoctaciones_nacionales", "pernoctaciones_internacionales",
        "estancia_media_dias", "fuente", "fecha_extraccion",
    ],
    "turismo_oferta_osm": [
        "cod_ine", "num_alojamientos", "num_hoteles", "num_restaurantes",
        "num_atracciones_turisticas", "num_museos", "fuente", "fecha_extraccion",
    ],
    "tripadvisor_pois": [
        "cod_ine", "location_id_tripadvisor", "nombre", "categoria",
        "rating", "num_reviews", "latitud", "longitud", "fuente", "fecha_extraccion",
    ],
    "redes_sociales_buzz": [
        "cod_ine", "fuente_social", "canal", "num_menciones", "fecha_extraccion",
    ],
    "datasets_datosgob": [
        "cod_ine_relacionado", "titulo_dataset", "descripcion", "url_recurso",
        "formato", "publicador", "fecha_extraccion",
    ],
}


def empty_dataframe(table_name: str):
    import pandas as pd
    if table_name not in TABLE_SCHEMAS:
        raise ValueError(f"Tabla desconocida: {table_name}")
    return pd.DataFrame(columns=TABLE_SCHEMAS[table_name])
