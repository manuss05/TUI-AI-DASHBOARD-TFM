# Cuadro de Mando Estrategico - TUI Group Espana

Cuadro de mando analitico interactivo desarrollado en Streamlit para el analisis del turismo provincial en Espana, enmarcado en el Trabajo de Fin de Master (TFM) sobre gestion turistica estrategica para TUI Group.

La aplicacion permite a los directores estrategicos segmentar las 52 demarcaciones provinciales de Espana mediante tecnicas de agrupamiento (K-Means), analizar la relacion entre saturacion y potencial turistico, explorar puntos de interes geograficos (POIs) y realizar consultas analiticas mediante inteligencia artificial conectada a la API de Google Gemini.

## Estructura y Funcionalidades del Cuadro de Mando

El cuadro de mando se organiza en cinco pestanas analiticas principales:

- Pestana 1: Mapa de Saturacion
  Visualizacion coropletica de Espana con las 52 provincias clasificadas segun su nivel de saturacion turistica ("Desaprovechado", "Destinos maduros", "Grandes metropolis", "Hipersaturado"). Incluye etiquetas y metricas en ventana emergente (tooltip).

- Pestana 2: Mapa de Potencial
  Visualizacion coropletica de Espana con las 52 provincias clasificadas segun su nivel de potencial turistico ("Potencial bajo", "Potencial alto", "Ciudades pequenas", "Destinos estrella").

- Pestana 3: Comparativa Provincial
  Grafico interactivo de columnas/barras horizontales con las provincias en el Eje Y y un Eje X seleccionable entre las variables numericas de TurismoProvincia (presion turistica, ocupacion, estacionalidad, ADR, plazas rurales, etc.). Incluye ordenacion personalizable, coloreo por cluster o monocromatico, linea de media nacional y resumen estadistico.

- Pestana 4: Ficha Provincial y POIs
  Selector provincial en barra lateral que despliega un panel resumen con indicadores clave (poblacion, ocupacion hotelera, estacionalidad, ADR, plazas rurales, etc.) y un mapa cartografico interactivo con los puntos de interes (POIs) de la provincia extraidos de OpenStreetMap, categorizados y filtrables.

- Pestana 5: Consulta IA con Google Gemini
  Modulo de asistencia analitica impulsado por modelos de Google Gemini (gemini-2.5-flash y gemini-3.6-flash). Permite filtrar la tabla provincial por Comunidad Autonoma, provincia y tipologia de cluster, plantear preguntas analiticas en lenguaje natural y obtener respuestas contextualizadas en tiempo real.

## Pasos para la Puesta en Marcha

Para desplegar y ejecutar la aplicacion en local, siga estrictamente estos tres pasos secuenciales:

### Paso 1: Instalacion de dependencias
Instale los paquetes de Python requeridos a partir del archivo de dependencias ubicado en la raiz del proyecto:

```bash
pip install -r requirements.txt
```

### Paso 2: Preprocesamiento cartografico
Ejecute el script de preparacion cartografica para transformar el shapefile municipal en un archivo GeoJSON provincial simplificado y validado (`dashboard/provincias.geojson`). Este paso debe ejecutarse una unica vez de forma previa al lanzamiento del cuadro de mando:

```bash
python dashboard/generar_geojson.py
```

El script genera `dashboard/provincias.geojson` con un tamano optimizado (menor a 1 MB), reproyectado al sistema WGS84 (EPSG:4326) y garantizando la presencia de las 52 entidades provinciales identificadas por su codigo `COD_PROV`.

### Paso 3: Ejecucion del cuadro de mando
Inicie el servidor interactivo de Streamlit para abrir la aplicacion en el navegador web predeterminado:

```bash
streamlit run dashboard/app.py
```

## Requisitos y Configuracion Adicional

- Version de Python: Se recomienda Python 3.10 o superior (compatible con Python 3.12).
- Credenciales de Inteligencia Artificial: Para el funcionamiento de la Pestana 5 (Consulta IA), configure su clave de API de Google Gemini en el archivo `.env` en la raiz del proyecto con la variable:
  ```env
  GEMINI_API_KEY=su_clave_aqui
  ```
- Politica de codificacion: Todos los archivos y textos de interfaz siguen una politica estricta de Cero Emojis para compatibilidad plena con terminales Windows y entornos corporativos.
