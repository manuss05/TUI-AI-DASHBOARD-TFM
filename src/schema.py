"""
Modelo relacional del proyecto — Ámbito Nacional de España.

Niveles territoriales:
  1. `provincias`: Las 52 provincias y ciudades autónomas oficiales de España,
     con códigos INE de 2 dígitos, población oficial y CCAA.
  2. `municipios_espana`: El censo oficial completo de los 8.138 municipios de España
     procedente del Padrón Continuo del INE (Tabla 29005).
  3. `localidades`: Localidades geocodificadas con coordenadas IGN/OSM y cod_ine.
  4. `flujo_ine_provincia`: Series temporales mensuales de viajeros y pernoctaciones
     para todas las provincias y CCAA de España (INE EOH Tabla 2074).
  5. `flujo_ine_localidad`: Series temporales mensuales de viajeros y pernoctaciones
     para los 113 puntos turísticos clave de España (INE EOH Tabla 2078).
  6. `oferta_osm`: Métricas de POIs de alojamiento y turismo.
  7. `datosgob_catalogo`: Catálogo nacional de datasets abiertos sobre turismo.
"""

TABLE_SCHEMAS = {
    "provincias": [
        "INE_Pob_PROV.provincia", "INE_Pob_PROV.poblacion_total", "INE_Pob_PROV.anio",
        "INE_Pob_PROV.cod_serie", "INE_Pob_PROV.fuente", "_meta.cod_prov",
        "_meta.capital", "_meta.ccaa", "_meta.fecha_extraccion"
    ],
    "municipios_espana": [
        "INE_Pob_MUN.nombre_municipio", "INE_Pob_MUN.poblacion_oficial",
        "INE_Pob_MUN.anio", "INE_Pob_MUN.cod_serie", "INE_Pob_MUN.fuente",
        "_meta.fecha_extraccion"
    ],
    "localidades": [
        "CartoCiudad.cod_ine", "CartoCiudad.nombre_municipio", "CartoCiudad.provincia",
        "CartoCiudad.ccaa", "CartoCiudad.latitud", "CartoCiudad.longitud",
        "_meta.fuente_geocod", "_meta.fecha_extraccion", "_meta.cod_ine_clave",
        "_meta.nombre_municipio"
    ],
    "flujo_ine_provincia": [
        "INE_EOH_PROV.ambito", "INE_EOH_PROV.indicador", "INE_EOH_PROV.residencia",
        "INE_EOH_PROV.nombre_serie_completo", "INE_EOH_PROV.cod_serie",
        "INE_EOH_PROV.anio", "INE_EOH_PROV.periodo", "INE_EOH_PROV.valor",
        "INE_EOH_PROV.fuente", "INE_EOH_PROV.tabla_id", "_meta.fecha_extraccion"
    ],
    "flujo_ine_localidad": [
        "INE_EOH_MUN.punto_turistico", "INE_EOH_MUN.indicador", "INE_EOH_MUN.residencia",
        "INE_EOH_MUN.nombre_serie_completo", "INE_EOH_MUN.cod_serie",
        "INE_EOH_MUN.anio", "INE_EOH_MUN.periodo", "INE_EOH_MUN.valor",
        "INE_EOH_MUN.fuente", "INE_EOH_MUN.tabla_id", "_meta.fecha_extraccion"
    ],
    "oferta_osm": [
        "OSM_Overpass.num_hoteles", "OSM_Overpass.num_restaurantes",
        "OSM_Overpass.num_atracciones", "OSM_Overpass.num_museos",
        "OSM_Overpass.fuente", "OSM_Overpass.fecha_extraccion",
        "_meta.cod_ine_clave", "_meta.nombre_municipio"
    ],
    "datosgob_catalogo": [
        "DatosGob.titulo_dataset", "DatosGob.descripcion", "DatosGob.url_recurso",
        "DatosGob.formato", "DatosGob.publicador", "DatosGob.fuente",
        "_meta.fecha_extraccion"
    ]
}


def empty_dataframe(table_name: str):
    import pandas as pd
    if table_name not in TABLE_SCHEMAS:
        raise ValueError(f"Tabla desconocida: {table_name}")
    return pd.DataFrame(columns=TABLE_SCHEMAS[table_name])
