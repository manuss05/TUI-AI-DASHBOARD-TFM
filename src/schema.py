"""Esquema relacional del proyecto con columnas crudas."""
import pandas as pd

TABLE_SCHEMAS = {
    "INE_provincias": [
        "COD", "Nombre", "T3_Unidad", "T3_Escala", "Fecha", "T3_Periodo",
        "T3_TipoDato", "Anyo", "Valor", "MetaData_json", "tabla_id", "_meta.fecha_extraccion"
    ],
    "municipios_espana": [
        "COD", "Nombre", "T3_Unidad", "T3_Escala", "Fecha", "T3_Periodo",
        "T3_TipoDato", "Anyo", "Valor", "MetaData_json", "tabla_id", "_meta.fecha_extraccion"
    ],
    "flujo_ine_provincia": [
        "COD", "Nombre", "T3_Unidad", "T3_Escala", "Fecha", "T3_Periodo",
        "T3_TipoDato", "Anyo", "Valor", "MetaData_json", "tabla_id", "_meta.fecha_extraccion"
    ],
    "flujo_ine_localidad": [
        "COD", "Nombre", "T3_Unidad", "T3_Escala", "Fecha", "T3_Periodo",
        "T3_TipoDato", "Anyo", "Valor", "MetaData_json", "tabla_id", "_meta.fecha_extraccion"
    ],
    "Carto_provincias": [
        "query", "id", "muniCode", "provinceCode", "muni", "province",
        "comunidadAutonoma", "lat", "lng", "type", "state", "raw_json", "_meta.fecha_extraccion"
    ],
    "oferta_osm": [
        "query_name", "lat", "lon", "radio_metros", "mirror_usado",
        "elements_raw_json", "_meta.fecha_extraccion"
    ],
    "clima_aemet": [
        "id_municipio", "nombre", "provincia", "elaborado", "fecha",
        "dia_raw_json", "_meta.fecha_extraccion"
    ],
    "datosgob_catalogo": [
        "keyword_busqueda", "about", "title_raw", "description_raw",
        "publisher_raw", "distribution_raw", "modified", "_meta.fecha_extraccion"
    ]
}


def empty_dataframe(table_name: str) -> pd.DataFrame:
    if table_name not in TABLE_SCHEMAS:
        raise ValueError(f"Tabla desconocida: {table_name}")
    return pd.DataFrame(columns=TABLE_SCHEMAS[table_name])
