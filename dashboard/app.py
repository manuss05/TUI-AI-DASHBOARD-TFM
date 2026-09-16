"""
Aplicacion apoyandonos en STREAMLIT para generar un dashboard interactivo con la información ya trabajada
"""

import json
import os
import unicodedata
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv # Carga de entorno para clave API
from google import genai


#--------------------------------------------------------------------------------
#CONFIGURACIONES INICIALES
st.set_page_config(
    page_title="TUI Group - Gestion Estrategica del Turismo",
    layout="wide")

#RUTAS PARA EXTRAER LO NECESARIO PARA LA APLICACION
DIRECTORIO_ACTUAL = Path(__file__).resolve().parent

DIRECTORIO_RAIZ = DIRECTORIO_ACTUAL.parent
RUTA_CSV_DEFECTO = DIRECTORIO_RAIZ / "Datos procesados" / "Datos pulidos" / "TurismoProvincia.csv"
RUTA_GEOJSON_DEFECTO = DIRECTORIO_ACTUAL / "provincias.geojson"
RUTA_PARQUET_DEFECTO = DIRECTORIO_RAIZ / "Extractor" / "data" / "processed" / "pois_espana_osm.parquet"
RUTA_ENV_DEFECTO = DIRECTORIO_RAIZ / ".env"

# Cargar variables de entorno desde .env
load_dotenv(dotenv_path=RUTA_ENV_DEFECTO)


# FUNCIONES PARA OPTIMIZAR EL CACHE (propuesto por IA)
@st.cache_data
def cargar_datos_provinciales(ruta_csv: str = None) -> pd.DataFrame:
    """
    Carga el dataset provincial TurismoProvincia.csv, valida su dimension
    (50 provincias, 24 columnas) y normaliza cod_prov a cadena de 2 digitos con zfill(2).
    """
    if ruta_csv is None:
        ruta_csv = RUTA_CSV_DEFECTO
    ruta_csv = Path(ruta_csv)

    if not ruta_csv.exists():
        raise FileNotFoundError(f"Archivo de datos provinciales no encontrado: {ruta_csv}")

    df = pd.read_csv(ruta_csv, sep=";", encoding="utf-8")
    df["cod_prov"] = df["cod_prov"].astype(str).str.strip().str.zfill(2)

    # Garantizar asignacion correcta de clusters de saturacion:
    # 0: 'Muy saturados' (Baleares, Canarias), 1: 'No saturados' (interior), 2: 'Saturados'
    mapa_saturacion = {0: "Muy saturados", 1: "No saturados", 2: "Saturados"}
    if "cluster_saturacion" in df.columns:
        df["saturacion"] = df["cluster_saturacion"].astype(int).map(mapa_saturacion)

    if len(df) != 50:
        raise ValueError(f"Se esperaban 50 provincias, pero se obtuvieron {len(df)}.")
    if df.isnull().sum().sum() != 0:
        raise ValueError("El dataset provincial contiene valores nulos no admitidos.")

    return df


@st.cache_data
def cargar_geojson(ruta_geojson: str = None) -> dict:
    """
    Carga la cartografia provincial simplificada de España en formato GeoJSON.
    Filtra Ceuta y Melilla (codigos 51 y 52) para coincidir con las 50 provincias del dataset.
    """
    if ruta_geojson is None:
        ruta_geojson = RUTA_GEOJSON_DEFECTO
    ruta_geojson = Path(ruta_geojson)

    if not ruta_geojson.exists():
        raise FileNotFoundError(f"Archivo cartografico GeoJSON no encontrado: {ruta_geojson}")

    with open(ruta_geojson, "r", encoding="utf-8") as f:
        geo_dict = json.load(f)

    if geo_dict.get("type") != "FeatureCollection":
        raise ValueError("El archivo GeoJSON debe ser una FeatureCollection valida.")

    # Excluir Ceuta (51) y Melilla (52) si estan presentes en el GeoJSON
    geo_dict["features"] = [
        f for f in geo_dict.get("features", [])
        if str(f.get("properties", {}).get("COD_PROV", "")).strip().zfill(2) not in ["51", "52"]
    ]

    if len(geo_dict["features"]) != 50:
        raise ValueError(f"Se esperaban 50 entidades provinciales tras excluir Ceuta y Melilla, pero se obtuvieron {len(geo_dict['features'])}.")

    return geo_dict


@st.cache_data
def cargar_pois_provincia(cod_prov: str, ruta_parquet: str = None) -> pd.DataFrame:
    """
    Carga y poda los puntos de interes de OpenStreetMap para una provincia especifica.
    Columnas seleccionadas: cod_prov, nombre, categoria, subtipo, latitud, longitud.
    """
    if ruta_parquet is None:
        ruta_parquet = RUTA_PARQUET_DEFECTO
    ruta_parquet = Path(ruta_parquet)

    if not ruta_parquet.exists():
        raise FileNotFoundError(f"Archivo Parquet de POIs no encontrado: {ruta_parquet}")

    cod_prov_normalizado = str(cod_prov).strip().zfill(2)
    columnas_poda = ["cod_prov", "nombre", "categoria", "subtipo", "latitud", "longitud"]
    df_pois = pd.read_parquet(ruta_parquet, columns=columnas_poda)
    df_filtrado = df_pois[df_pois["cod_prov"] == cod_prov_normalizado].copy()
    return df_filtrado


# ERRORES (propuesto por IA)

try:
    df_provincial = cargar_datos_provinciales()
except FileNotFoundError as error_csv:
    st.error(
        f"Error critico al cargar los datos provinciales: {error_csv}. "
        "Asegurese de que el archivo 'Datos procesados/Datos pulidos/TurismoProvincia.csv' existe."
    )
    st.stop()
except Exception as error_general_csv:
    st.error(f"Error inesperado al cargar los datos provinciales: {error_general_csv}")
    st.stop()

try:
    geojson_provincias = cargar_geojson()
except FileNotFoundError as error_geo:
    st.error(
        "No se encontro el archivo cartografico 'dashboard/provincias.geojson'. "
        "Por favor, ejecute previamente en la terminal: python dashboard/generar_geojson.py"
    )
    st.stop()
except Exception as error_general_geo:
    st.error(f"Error inesperado al cargar la cartografia: {error_general_geo}")
    st.stop()

#-------------------------------------------------------------------------------------------------
# PALETAS Y ORDEN

# Cluster 1: Saturacion (3 agrupaciones: 0: 'Muy saturados', 1: 'No saturados', 2: 'Saturados')
PALETA_SATURACION = {
    "No saturados": "#66C2A5",     # Verde azulado / turquesa suave (baja presion turistica)
    "Saturados": "#f39c12",        # Naranja / ambar (tension media-alta)
    "Muy saturados": "#e74c3c",    # Rojo coral / alerta (alta saturacion estival)
}

ORDEN_SATURACION = [
    "No saturados",
    "Saturados",
    "Muy saturados"
]

# Cluster 2: Potencial (5 agrupaciones: 0: 'Medio', 1: 'Alto', 2: 'Muy alto', 3: 'Muy bajo', 4: 'Bajo')
PALETA_POTENCIAL = {
    "Muy alto": "#2ecc71",         # Verde vivo (maxima capacidad y dinamismo)
    "Alto": "#3498db",             # Azul (alto atractivo y recursos)
    "Medio": "#FFD92F",            # Amarillo dorado (capacidad intermedia)
    "Bajo": "#e67e22",             # Naranja tierra (capacidad reducida)
    "Muy bajo": "#B3B3B3",         # Gris pizarra (minimo potencial)
}

ORDEN_POTENCIAL = [
    "Muy alto",
    "Alto",
    "Medio",
    "Bajo",
    "Muy bajo"
]

# Diccionario de metricas cuantitativas de TurismoProvincia para comparativas. funciona como desplegable
METRICAS_NUMERICAS = {
    "presion_turistica_hab": "Presion turistica (viajeros por habitante)",
    "viajeros_hotel_anual": "Viajeros hoteleros anuales",
    "ocupacion_hotel_media": "Ocupacion hotelera media (%)",
    "ocupacion_hotel_pico": "Ocupacion hotelera en mes pico (%)",
    "ocupacion_hotel_finsemana": "Ocupacion hotelera en fin de semana (%)",
    "estacionalidad_cv": "Estacionalidad (coeficiente de variacion)",
    "estancia_media_hotel": "Estancia media hotelera (dias)",
    "adr_medio": "Tarifa media diaria - ADR (EUR)",
    "revpar_max": "RevPAR maximo (EUR)",
    "plazas_hotel_media": "Plazas hoteleras medias",
    "poblacion": "Poblacion residente",
    "viajeros_rural_anual": "Viajeros rurales anuales",
    "ocupacion_rural_media": "Ocupacion rural media (%)",
    "plazas_rural_media": "Plazas rurales medias",
    "estancia_media_rural": "Estancia media rural (dias)",
    "puntos_turisticos_ine": "Puntos turisticos reconocidos (INE)"
}

#----------------------------------------------------------------------------------------------------------
# BARRA LATERAL Y FILTROS 

st.sidebar.title("Filtros Globales")
st.sidebar.markdown("Configure los filtros macro aplicables a los mapas provinciales y a la comparativa provincial.")

# Filtro por comunidad autonoma
lista_ccaa = ["Todas"] + sorted(df_provincial["comunidad_autonoma"].unique().tolist())
filtro_ccaa = st.sidebar.selectbox("Comunidad Autonoma", options=lista_ccaa, index=0)

lista_saturacion = ["Todos"] + [c for c in ORDEN_SATURACION if c in df_provincial["saturacion"].unique()] + [c for c in sorted(df_provincial["saturacion"].unique()) if c not in ORDEN_SATURACION]
filtro_saturacion = st.sidebar.selectbox("Cluster Saturacion", options=lista_saturacion, index=0)

lista_potencial = ["Todos"] + [c for c in ORDEN_POTENCIAL if c in df_provincial["potencial"].unique()] + [c for c in sorted(df_provincial["potencial"].unique()) if c not in ORDEN_POTENCIAL]
filtro_potencial = st.sidebar.selectbox("Cluster Potencial", options=lista_potencial, index=0)

# Aplicacion de filtros macro sobre el dataset para Tabs 1, 2 y 3
df_filtrado = df_provincial.copy()

if filtro_ccaa != "Todas":  #Logica: si no es Todos/as, aplica un filtro basico de pandas. repiye para los 3 filtros de la barra lateral
    df_filtrado = df_filtrado[df_filtrado["comunidad_autonoma"] == filtro_ccaa]
if filtro_saturacion != "Todos":
    df_filtrado = df_filtrado[df_filtrado["saturacion"] == filtro_saturacion]
if filtro_potencial != "Todos":
    df_filtrado = df_filtrado[df_filtrado["potencial"] == filtro_potencial]

st.sidebar.caption(f"Provincias seleccionadas: {len(df_filtrado)} de {len(df_provincial)}")

st.sidebar.divider()
st.sidebar.subheader("Ficha Provincial")

# Selector individual de provincia ordenado alfabeticamente considerando tildes en castellano
def normalizar_para_orden(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).casefold()

lista_provincias_ordenadas = sorted(
    df_provincial["provincia"].unique().tolist(),
    key=normalizar_para_orden
)

# Seleccion inicial por defecto: Madrid
idx_defecto_prov = lista_provincias_ordenadas.index("Madrid") if "Madrid" in lista_provincias_ordenadas else 0

provincia_seleccionada = st.sidebar.selectbox(
    "Seleccionar Provincia",
    options=lista_provincias_ordenadas,
    index=idx_defecto_prov
)



# ENCABEZADO
st.title("TUI Group - Gestion Estrategica del Turismo en España")
st.markdown(
    "Cuadro de mando corporativo para la toma de decisiones, planificacion de capacidad hotelera, "
    "analisis de saturacion territorial y exploracion de potencial de destinos en España."
)

tab_sat, tab_pot, tab_cuad, tab_ficha, tab_ia = st.tabs([
    "Mapa de Saturacion",
    "Mapa de Potencial",
    "Comparativa Provincial",
    "Ficha Provincial",
    "Consulta IA"
])


#-----------------------------------------------------------------------
# PANTALLA 1: MAPA DE SATURACION
with tab_sat:
    st.subheader("Mapa de Saturacion Turistica Provincial") #Titulo
    st.markdown(
        "Distribucion cartografica de las 50 provincias según su clasificación en clusters de "
        "saturación turística, evaluando la presion por habitante, la ocupación hotelera media y la estacionalidad."
    ) #Subtitulo

    if df_filtrado.empty:
        st.warning("No hay provincias que coincidan con los filtros seleccionados.")
    else:
        fig_sat = px.choropleth(
            data_frame=df_filtrado,
            geojson=geojson_provincias,
            locations="cod_prov",
            featureidkey="properties.COD_PROV",
            color="saturacion",
            color_discrete_map=PALETA_SATURACION,
            category_orders={"saturacion": ORDEN_SATURACION},
            hover_name="provincia",
            hover_data={"cod_prov": False,
                "comunidad_autonoma": True,
                "saturacion": True,
                "presion_turistica_hab": ":.2f",
                "ocupacion_hotel_media": ":.1f%",
                "temporada_alta": True,
                "viajeros_hotel_anual": ":,.0f"
            },
            labels={
                "saturacion": "Nivel de Saturacion",
                "comunidad_autonoma": "Comunidad Autonoma",
                "presion_turistica_hab": "Presion Turistica (viajeros/hab)",
                "ocupacion_hotel_media": "Ocupacion Hotelera Media",
                "temporada_alta": "Temporada Alta",
                "viajeros_hotel_anual": "Viajeros Hotel Anual"}
        )
        fig_sat.update_geos(fitbounds="locations", visible=False)
        fig_sat.update_layout(
            margin={"r": 0, "t": 20, "l": 0, "b": 0},
            height=620,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                title_text="Tipologia de Saturacion"
            ),
            dragmode=False
        )
        st.plotly_chart(fig_sat, width='stretch', config={"scrollZoom": False, "displaylogo": False})


#-----------------------------------------------------------------------
# PANTALLA 2: MAPA DE POTENCIAL

with tab_pot:
    st.subheader("Mapa de Potencial Turistico Provincial")
    st.markdown(
        "Distribucion cartografica de las 50 provincias españolas segun su clasificacion en clusters de "
        "potencial turistico y rendimiento comercial, combinando volumen de viajeros, tarifas hoteleras y capacidad rural."
    )

    if df_filtrado.empty:
        st.warning("No hay provincias que coincidan con los filtros seleccionados. Por favor, ajuste los filtros en la barra lateral.")
    else:
        fig_pot = px.choropleth(
            data_frame=df_filtrado,
            geojson=geojson_provincias,
            locations="cod_prov",
            featureidkey="properties.COD_PROV",
            color="potencial",
            color_discrete_map=PALETA_POTENCIAL,
            category_orders={"potencial": ORDEN_POTENCIAL},
            hover_name="provincia",
            hover_data={
                "cod_prov": False,
                "comunidad_autonoma": True,
                "potencial": True,
                "viajeros_hotel_anual": ":,.0f",
                "adr_medio": ":.2f",
                "revpar_max": ":.2f",
                "plazas_rural_media": ":,.0f"
            },
            labels={
                "potencial": "Nivel de Potencial",
                "comunidad_autonoma": "Comunidad Autonoma",
                "viajeros_hotel_anual": "Viajeros Hotel Anual",
                "adr_medio": "Tarifa Media Diaria - ADR (EUR)",
                "revpar_max": "RevPAR Maximo (EUR)",
                "plazas_rural_media": "Plazas Rurales Media"
            }
        )
        fig_pot.update_geos(fitbounds="locations", visible=False)
        fig_pot.update_layout(
            margin={"r": 0, "t": 20, "l": 0, "b": 0},
            height=620,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                title_text="Tipologia de Potencial"
            ),
            dragmode=False
        )
        st.plotly_chart(fig_pot, width='stretch', config={"scrollZoom": False, "displaylogo": False})


# -----------------------------------------------------------------------------
#3: COMPARATIVA PROVINCIAL (COLUMNAS HORIZONTALES)

with tab_cuad:
    st.subheader("Comparativa Provincial por Columnas Horizontales")
    st.markdown(
        "Grafico interactivo de barras horizontales para comparar el comportamiento de las provincias españolas "
        "en cualquier indicador cuantitativo de TurismoProvincia. El Eje Y muestra las provincias y el Eje X la metrica seleccionada."
    )

    if df_filtrado.empty:
        st.warning("Los filtros muestran 0 provincias.") #Mensaje por si no hay provincias
    else: #Pantalla
        # Controles y filtros de la hoja
        col_m1, col_m2, col_m3 = st.columns([3, 2, 2])
        with col_m1:
            metrica_seleccionada = st.selectbox(
                "Seleccionar metrica numerica (Eje X):",
                options=list(METRICAS_NUMERICAS.keys()),
                format_func=lambda x: METRICAS_NUMERICAS.get(x, x),
                index=0,
                key="filtro_metrica_horizontal"
            )
        with col_m2:
            orden_opcion = st.selectbox(
                "Orden de las provincias:",
                options=["Menor a mayor", "Mayor a menor", "Alfabetico (A-Z)"], #La tercera opcion sería la default
                index=0,
                key="filtro_orden_horizontal"
            )
        with col_m3:
            color_opcion = st.selectbox(
                "Colorear barras por:",
                options=["Cluster Saturacion", "Cluster Potencial", "Monocromatico"],
                index=0,
                key="filtro_color_horizontal"
            )

        # Preparacion de datos ordenados estrictamente por la metrica seleccionada
        df_grafico = df_filtrado.copy()

        # En Plotly con autorange='reversed', el primer elemento de la lista aparece arriba.
        if orden_opcion == "Menor a mayor":
            df_grafico = df_grafico.sort_values(by=metrica_seleccionada, ascending=True)
        elif orden_opcion == "Mayor a menor":
            df_grafico = df_grafico.sort_values(by=metrica_seleccionada, ascending=False)
        else:
            df_grafico = df_grafico.sort_values(by="provincia", ascending=True) #Tercera opcion, en alfabetico

        lista_orden_provincias = df_grafico["provincia"].tolist()

        # Configuracion de color segun lo marcado al inicio del archivo
        if color_opcion == "Cluster Saturacion":
            columna_color = "saturacion"
            mapa_colores = PALETA_SATURACION #Usamos paleta del inicio
            titulo_leyenda = "Cluster Saturacion"
            orden_categorias = {"saturacion": ORDEN_SATURACION}
        elif color_opcion == "Cluster Potencial":
            columna_color = "potencial"
            mapa_colores = PALETA_POTENCIAL
            titulo_leyenda = "Cluster Potencial"
            orden_categorias = {"potencial": ORDEN_POTENCIAL}
        else:
            columna_color = None
            mapa_colores = None
            titulo_leyenda = None
            orden_categorias = None

        etiqueta_metrica = METRICAS_NUMERICAS.get(metrica_seleccionada, metrica_seleccionada)
        altura_dinamica = max(480, len(df_grafico) * 22)

        # Crear grafico de barras horizontales con barmode overlay para no fragmentar el grosor de las barras
        fig_bar = px.bar(
            data_frame=df_grafico,
            x=metrica_seleccionada,
            y="provincia",
            orientation="h",
            color=columna_color,
            color_discrete_map=mapa_colores,
            category_orders=orden_categorias,
            text=metrica_seleccionada,
            hover_name="provincia",
            hover_data={
                "comunidad_autonoma": True,
                "saturacion": True,
                "potencial": True,
                metrica_seleccionada: True,
                "provincia": False
            },
            labels={
                metrica_seleccionada: etiqueta_metrica,
                "provincia": "Provincia",
                "saturacion": "Cluster Saturacion",
                "potencial": "Cluster Potencial"
            },
            template="plotly_white",
            height=altura_dinamica,
            barmode="overlay"
        )

        es_decimal = df_grafico[metrica_seleccionada].dtype == float and df_grafico[metrica_seleccionada].max() < 1000
        fig_bar.update_traces(
            texttemplate="%{text:.2f}" if es_decimal else "%{text:,.0f}",
            textposition="outside",
            cliponaxis=False
        )

        # linea de media nacional
        media_nacional = float(df_provincial[metrica_seleccionada].mean())
        texto_media = f"Media Nacional: {media_nacional:.2f}" if es_decimal else f"Media Nacional: {media_nacional:,.0f}"
        fig_bar.add_vline(
            x=media_nacional,
            line_dash="dash",
            line_color="#e11d48", #color rojo
            annotation_text=texto_media,
            annotation_position="top right",
            annotation_font=dict(size=10, color="#e11d48")
        )

        # Fijar categoryorder='array' y autorange='reversed' para respetar el orden estricto de la metrica
        fig_bar.update_layout(
            margin=dict(l=10, r=40, t=30, b=40),
            xaxis=dict(
                title=etiqueta_metrica,
                gridcolor="#f3f4f6"
            ),
            yaxis=dict(
                title="Provincia",
                tickfont=dict(size=11),
                categoryorder="array",
                categoryarray=lista_orden_provincias,
                autorange="reversed"
            ),
            legend=dict(
                title_text=titulo_leyenda,
                orientation="h",
                yanchor="bottom",
                y=1.01,
                xanchor="right",
                x=1
            )
        )
        st.plotly_chart(fig_bar, width='stretch')

        # Resumen estadistico
        st.subheader("Resumen Estadistico del Indicador Seleccionado")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)

        idx_max = df_grafico[metrica_seleccionada].idxmax()
        idx_min = df_grafico[metrica_seleccionada].idxmin()
        fila_max = df_grafico.loc[idx_max]
        fila_min = df_grafico.loc[idx_min]
        mediana_nacional = float(df_provincial[metrica_seleccionada].median())

        formato_val = (lambda v: f"{v:.2f}") if es_decimal else (lambda v: f"{v:,.0f}".replace(",", "."))

        with col_s1:
            st.metric(
                label="Provincia Lider",
                value=fila_max["provincia"],
                delta=formato_val(fila_max[metrica_seleccionada])
            )
        with col_s2:
            st.metric(
                label="Provincia Menor",
                value=fila_min["provincia"],
                delta=formato_val(fila_min[metrica_seleccionada])
            )
        with col_s3:
            st.metric(
                label="Media Nacional",
                value=formato_val(media_nacional)
            )
        with col_s4:
            st.metric(
                label="Mediana Nacional",
                value=formato_val(mediana_nacional)
            )


# -----------------------------------------------------------------------------
#4: FICHA PROVINCIAL

with tab_ficha:
    st.subheader(f"Ficha Estrategica Provincial: {provincia_seleccionada}")
    st.markdown("Indicadores detallados de capacidad, demanda hotelera, estacionalidad y puntos de interes turistico.")

    fila_provincia = df_provincial[df_provincial["provincia"] == provincia_seleccionada].iloc[0]
    cod_prov_sel = str(fila_provincia["cod_prov"]).zfill(2)

    # Bloque de metricas clave estructuradas en tarjetas st.metric
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric(
            label="Poblacion",
            value=f"{int(fila_provincia['poblacion']):,}".replace(",", ".")
        )
        st.metric(
            label="Presion Turistica",
            value=f"{fila_provincia['presion_turistica_hab']:.2f} hab/tur"
        )
    with col_m2:
        st.metric(
            label="Viajeros Hoteleros Anuales",
            value=f"{int(fila_provincia['viajeros_hotel_anual']):,}".replace(",", ".")
        )
        st.metric(
            label="Ocupacion Hotelera Media",
            value=f"{fila_provincia['ocupacion_hotel_media']:.1f}%"
        )
    with col_m3:
        st.metric(
            label="Tarifa Diaria Media (ADR)",
            value=f"{fila_provincia['adr_medio']:.2f} EUR"
        )
        st.metric(
            label="Estacionalidad (CV)",
            value=f"{fila_provincia['estacionalidad_cv']:.2f}"
        )

    col_m4, col_m5, col_m6 = st.columns(3)
    with col_m4:
        st.metric(
            label="Plazas Rurales Medias",
            value=f"{int(fila_provincia['plazas_rural_media']):,}".replace(",", ".")
        )
    with col_m5:
        st.metric(
            label="RevPAR Maximo Temporada",
            value=f"{fila_provincia['revpar_max']:.2f} EUR"
        )
    with col_m6:
        st.metric(
            label="Plazas Hoteleras Medias",
            value=f"{int(fila_provincia['plazas_hotel_media']):,}".replace(",", ".")
        )

    # Indicadores cualitativos de cluster
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.info(f"Clasificacion de Saturacion: {fila_provincia['saturacion']} (Cluster {fila_provincia['cluster_saturacion']})")
    with col_info2:
        st.info(f"Clasificacion de Potencial: {fila_provincia['potencial']} (Cluster {fila_provincia['cluster_potencial']})")

    st.divider()
    st.subheader(f"Mapa de Puntos de Interes Turistico (POIs) - {provincia_seleccionada}")

    try:
        df_pois_provincia = cargar_pois_provincia(cod_prov_sel)

        if df_pois_provincia.empty:
            st.info(f"No se registraron puntos de interes turistico para la provincia de {provincia_seleccionada}.")
        else:
            categorias_disponibles = sorted(df_pois_provincia["categoria"].unique().tolist())
            opciones_cat = ["Todas las categorias"] + categorias_disponibles
            categoria_seleccionada = st.selectbox(
                "Filtrar por categoria de POI en el mapa",
                options=opciones_cat,
                index=0
            )

            if categoria_seleccionada == "Todas las categorias":
                df_pois_mostrar = df_pois_provincia
            else:
                df_pois_mostrar = df_pois_provincia[df_pois_provincia["categoria"] == categoria_seleccionada]

            st.caption(f"Visualizando {len(df_pois_mostrar)} puntos de interes de un total de {len(df_pois_provincia)} en la provincia.")

            # Centro del mapa: Madrid (lat=40.4168, lon=-3.7038) como coordenada de referencia inicial y fallback
            if not df_pois_mostrar.empty and pd.notnull(df_pois_mostrar["latitud"]).any():
                lat_centro = float(df_pois_mostrar["latitud"].mean())
                lon_centro = float(df_pois_mostrar["longitud"].mean())
            else:
                lat_centro = 40.4168
                lon_centro = -3.7038

            # Mapa interactivo de POIs utilizando px.scatter_map (compatible con Plotly 7.0+)
            fig_pois = px.scatter_map(
                data_frame=df_pois_mostrar,
                lat="latitud",
                lon="longitud",
                center={"lat": lat_centro, "lon": lon_centro},
                color="categoria",
                hover_name="nombre",
                hover_data={
                    "categoria": True,
                    "subtipo": True,
                    "latitud": False,
                    "longitud": False,
                    "cod_prov": False
                },
                zoom=8,
                map_style="open-street-map",
                title=f"Ubicacion de POIs - {provincia_seleccionada}"
            )
            fig_pois.update_layout(
                margin={"r": 0, "t": 40, "l": 0, "b": 0},
                height=550,
                map=dict(
                    style="open-street-map",
                    center=dict(lat=lat_centro, lon=lon_centro),
                    zoom=8
                )
            )
            st.plotly_chart(fig_pois, width='stretch')

            # Resumen cuantitativo por categoria
            with st.expander("Ver distribucion de POIs por categoria"):
                conteo_cats = df_pois_provincia["categoria"].value_counts().reset_index()
                conteo_cats.columns = ["Categoria", "Total POIs"]
                st.dataframe(conteo_cats, width='stretch', hide_index=True)

    except FileNotFoundError as error_poi_file:
        st.warning(f"Archivo de puntos de interes no disponible: {error_poi_file}. Mapa de POIs omitido.")
    except Exception as error_poi_general:
        st.error(f"Error al procesar el mapa de puntos de interes: {error_poi_general}")


# -----------------------------------------------------------------------------
# PANTALLA 5: CONSULTA IA

with tab_ia:
    st.subheader("Consulta Estrategica Asistida por Inteligencia Artificial")
    st.markdown(
        "Herramienta de consultoria turistica automatizada potenciada por Google Gemini. "
        "Filtre el contexto territorial de decision y formule su consulta estrategica en lenguaje natural."
    )

    st.markdown("#### Filtrado de Contexto Territorial y Clusters")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        ia_provincia = st.selectbox(
            "Provincia (Contexto)",
            options=["Todas"] + lista_provincias_ordenadas,
            key="ia_filtro_provincia"
        )
        ia_ccaa = st.selectbox(
            "Comunidad Autonoma (Contexto)",
            options=lista_ccaa,
            key="ia_filtro_ccaa"
        )
    with col_f2:
        ia_saturacion = st.selectbox(
            "Cluster Saturacion (Contexto)",
            options=lista_saturacion,
            key="ia_filtro_saturacion"
        )
        ia_potencial = st.selectbox(
            "Cluster Potencial (Contexto)",
            options=lista_potencial,
            key="ia_filtro_potencial"
        )

    # Filtrar subconjunto de contexto para la IA
    df_ia_contexto = df_provincial.copy()
    if ia_provincia != "Todas":
        df_ia_contexto = df_ia_contexto[df_ia_contexto["provincia"] == ia_provincia]
    if ia_ccaa != "Todas":
        df_ia_contexto = df_ia_contexto[df_ia_contexto["comunidad_autonoma"] == ia_ccaa]
    if ia_saturacion != "Todos":
        df_ia_contexto = df_ia_contexto[df_ia_contexto["saturacion"] == ia_saturacion]
    if ia_potencial != "Todos":
        df_ia_contexto = df_ia_contexto[df_ia_contexto["potencial"] == ia_potencial]

    st.caption(f"Contexto activo para la IA: {len(df_ia_contexto)} provincias incluidas en el analisis.")

    pregunta_estrategica = st.text_area(
        "Plantee su consulta estrategica para TUI Group (o dejela en blanco para un analisis general del contexto filtrado):",
        placeholder="Ejemplo: Que acciones debe emprender TUI Group para descongestionar destinos saturados y acelerar el desarrollo en destinos de alto potencial con estacionalidad baja?",
        height=120
    )

    col_btn1, col_btn2 = st.columns(2)
    boton_generar_prompt = col_btn1.button("Generar Prompt para IA")
    boton_consultar = col_btn2.button("Consultar Asesor IA")

    # Construccion del prompt contextualizado a partir de los filtros y la pregunta
    columnas_contexto = [
        "provincia", "comunidad_autonoma", "saturacion", "potencial",
        "presion_turistica_hab", "viajeros_hotel_anual", "ocupacion_hotel_media",
        "estacionalidad_cv", "adr_medio", "plazas_rural_media"
    ]
    tabla_resumen = df_ia_contexto[columnas_contexto].to_string(index=False)
    consulta_texto = pregunta_estrategica.strip() if pregunta_estrategica.strip() else "Realiza un diagnostico comparativo y recomendaciones de actuacion para las provincias filtradas."

    prompt_completo = f"""Eres un asesor senior en direccion estrategica de turismo para TUI Group en España.
Tu mision es proporcionar recomendaciones viables, analiticas y fundamentadas en datos reales.

DATOS ESTADISTICOS DE LAS PROVINCIAS SELECCIONADAS (N={len(df_ia_contexto)}):
{tabla_resumen}

CONSULTA DEL DIRECTIVO DE TUI GROUP:
{consulta_texto}

DIRECTRICES OBLIGATORIAS:
1. Responde de forma ejecutiva, estructurada con encabezados y vinetas en formato Markdown.
2. Basa tus recomendaciones en las metricas cuantitativas provistas (presion turistica, ocupacion, ADR, estacionalidad, plazas).
3. Redacta la respuesta completamente en idioma español formal.
4. Prohibicion absoluta de caracteres emoji en la respuesta.
"""

    if boton_generar_prompt:
        st.markdown("#### Prompt Generado para la Inteligencia Artificial")
        st.markdown("Este es el prompt estructurado a partir de los filtros seleccionados y su consulta:")
        st.code(prompt_completo, language="markdown")

    if boton_consultar:
        st.markdown("#### Prompt Enviado a la Inteligencia Artificial")
        with st.expander("Ver detalle del prompt estructurado", expanded=False):
            st.code(prompt_completo, language="markdown")

        api_key_gemini = os.getenv("GEMINI_API_KEY")
        if not api_key_gemini or not api_key_gemini.strip():
            st.error("No se ha encontrado la clave GEMINI_API_KEY en el archivo .env. Por favor, configure una clave valida.")
        else:
            with st.spinner("Consultando al asesor de inteligencia artificial Gemini..."):
                try:
                    cliente_genai = genai.Client(api_key=api_key_gemini)
                    modelos_candidatos = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest"]
                    respuesta_ia = None
                    ultimo_error_gemini = None

                    for modelo_id in modelos_candidatos:
                        try:
                            respuesta_obj = cliente_genai.models.generate_content(
                                model=modelo_id,
                                contents=prompt_completo
                            )
                            respuesta_ia = respuesta_obj.text
                            break
                        except Exception as error_llamada:
                            ultimo_error_gemini = error_llamada
                            error_texto = str(error_llamada).lower()
                            if "404" in error_texto or "not found" in error_texto or "not_found" in error_texto or "not available" in error_texto:
                                continue
                            raise error_llamada

                    if respuesta_ia is None:
                        if ultimo_error_gemini:
                            raise ultimo_error_gemini
                        else:
                            raise RuntimeError("No se obtuvo respuesta de ninguno de los modelos de Gemini.")

                    st.markdown("### Recomendaciones Estrategicas para TUI Group")
                    st.markdown(respuesta_ia)

                except Exception as error_ejecucion_ia:
                    st.error(f"Error al comunicar con la API de Google Gemini: {error_ejecucion_ia}")

