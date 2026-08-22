"""Esquema relacional del proyecto."""

TABLE_SCHEMAS = {
    "INE_provincias": [
        "INE_Pob_PROV.provincia", "INE_Pob_PROV.poblacion_total", "INE_Pob_PROV.anio",
        "INE_Pob_PROV.cod_serie", "INE_Pob_PROV.fuente", "_meta.cod_prov",
        "_meta.capital", "_meta.ccaa", "_meta.fecha_extraccion"
    ],
    "municipios_espana": [
        "INE_Pob_MUN.nombre_municipio", "INE_Pob_MUN.poblacion_oficial",
        "INE_Pob_MUN.anio", "INE_Pob_MUN.cod_serie", "INE_Pob_MUN.fuente",
        "_meta.fecha_extraccion"
    ],
    "Carto_provincias": [
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
    ],
    "clima_aemet": [
        "AEMET_Clima.cod_ine", "AEMET_Clima.nombre_municipio", "AEMET_Clima.provincia",
        "AEMET_Clima.fecha_prediccion", "AEMET_Clima.temp_max", "AEMET_Clima.temp_min",
        "AEMET_Clima.sens_termica_max", "AEMET_Clima.sens_termica_min",
        "AEMET_Clima.humedad_max", "AEMET_Clima.humedad_min",
        "AEMET_Clima.prob_precipitacion_pct", "AEMET_Clima.estado_cielo_desc",
        "AEMET_Clima.viento_dir", "AEMET_Clima.viento_vel_kmh", "AEMET_Clima.uv_max",
        "AEMET_Clima.fuente", "_meta.cod_ine_clave", "_meta.nombre_municipio",
        "_meta.fecha_extraccion"
    ]
}


def empty_dataframe(table_name: str):
    import pandas as pd
    if table_name not in TABLE_SCHEMAS:
        raise ValueError(f"Tabla desconocida: {table_name}")
    return pd.DataFrame(columns=TABLE_SCHEMAS[table_name])
