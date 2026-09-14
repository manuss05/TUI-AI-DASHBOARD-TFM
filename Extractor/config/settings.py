import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Rutas
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
DATA_LOGS_DIR = BASE_DIR / "data" / "logs"

DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
DATA_LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Rutas globales y cartografías
CARTOGRAFIA_SHP = BASE_DIR.parent / "cartografias" / "Munic04_ESP.shp"
ROOT_PROCESSED_DIR = BASE_DIR.parent / "Datos procesados"
OSM_POLYGONS_CACHE_DIR = DATA_RAW_DIR / "osm_provincias_cache"
OSM_POLYGONS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Claves API
AEMET_API_KEY = os.getenv("AEMET_API_KEY", "")

# Parametros de red
REQUEST_TIMEOUT = 30
DEFAULT_SLEEP_BETWEEN_CALLS = 1.1
USER_AGENT = "TFM-Turismo-Espana-ManuelSantos-UCM/1.0 (manuel.santos@tfm-turismo.es)"

# Provincias de España (50 + 2 ciudades autonomas)
PROVINCIAS_ESPANA = [
    {"cod_prov": "01", "nombre": "Araba/Álava", "capital": "Vitoria-Gasteiz", "ccaa": "País Vasco"},
    {"cod_prov": "02", "nombre": "Albacete", "capital": "Albacete", "ccaa": "Castilla-La Mancha"},
    {"cod_prov": "03", "nombre": "Alicante/Alacant", "capital": "Alicante", "ccaa": "Comunitat Valenciana"},
    {"cod_prov": "04", "nombre": "Almería", "capital": "Almería", "ccaa": "Andalucía"},
    {"cod_prov": "05", "nombre": "Ávila", "capital": "Ávila", "ccaa": "Castilla y León"},
    {"cod_prov": "06", "nombre": "Badajoz", "capital": "Badajoz", "ccaa": "Extremadura"},
    {"cod_prov": "07", "nombre": "Balears, Illes", "capital": "Palma", "ccaa": "Illes Balears"},
    {"cod_prov": "08", "nombre": "Barcelona", "capital": "Barcelona", "ccaa": "Cataluña"},
    {"cod_prov": "09", "nombre": "Burgos", "capital": "Burgos", "ccaa": "Castilla y León"},
    {"cod_prov": "10", "nombre": "Cáceres", "capital": "Cáceres", "ccaa": "Extremadura"},
    {"cod_prov": "11", "nombre": "Cádiz", "capital": "Cádiz", "ccaa": "Andalucía"},
    {"cod_prov": "12", "nombre": "Castellón/Castelló", "capital": "Castellón de la Plana", "ccaa": "Comunitat Valenciana"},
    {"cod_prov": "13", "nombre": "Ciudad Real", "capital": "Ciudad Real", "ccaa": "Castilla-La Mancha"},
    {"cod_prov": "14", "nombre": "Córdoba", "capital": "Córdoba", "ccaa": "Andalucía"},
    {"cod_prov": "15", "nombre": "A Coruña", "capital": "A Coruña", "ccaa": "Galicia"},
    {"cod_prov": "16", "nombre": "Cuenca", "capital": "Cuenca", "ccaa": "Castilla-La Mancha"},
    {"cod_prov": "17", "nombre": "Girona", "capital": "Girona", "ccaa": "Cataluña"},
    {"cod_prov": "18", "nombre": "Granada", "capital": "Granada", "ccaa": "Andalucía"},
    {"cod_prov": "19", "nombre": "Guadalajara", "capital": "Guadalajara", "ccaa": "Castilla-La Mancha"},
    {"cod_prov": "20", "nombre": "Gipuzkoa", "capital": "Donostia/San Sebastián", "ccaa": "País Vasco"},
    {"cod_prov": "21", "nombre": "Huelva", "capital": "Huelva", "ccaa": "Andalucía"},
    {"cod_prov": "22", "nombre": "Huesca", "capital": "Huesca", "ccaa": "Aragón"},
    {"cod_prov": "23", "nombre": "Jaén", "capital": "Jaén", "ccaa": "Andalucía"},
    {"cod_prov": "24", "nombre": "León", "capital": "León", "ccaa": "Castilla y León"},
    {"cod_prov": "25", "nombre": "Lleida", "capital": "Lleida", "ccaa": "Cataluña"},
    {"cod_prov": "26", "nombre": "La Rioja", "capital": "Logroño", "ccaa": "La Rioja"},
    {"cod_prov": "27", "nombre": "Lugo", "capital": "Lugo", "ccaa": "Galicia"},
    {"cod_prov": "28", "nombre": "Madrid", "capital": "Madrid", "ccaa": "Comunidad de Madrid"},
    {"cod_prov": "29", "nombre": "Málaga", "capital": "Málaga", "ccaa": "Andalucía"},
    {"cod_prov": "30", "nombre": "Murcia", "capital": "Murcia", "ccaa": "Región de Murcia"},
    {"cod_prov": "31", "nombre": "Navarra", "capital": "Pamplona/Iruña", "ccaa": "Comunidad Foral de Navarra"},
    {"cod_prov": "32", "nombre": "Ourense", "capital": "Ourense", "ccaa": "Galicia"},
    {"cod_prov": "33", "nombre": "Asturias", "capital": "Oviedo", "ccaa": "Principado de Asturias"},
    {"cod_prov": "34", "nombre": "Palencia", "capital": "Palencia", "ccaa": "Castilla y León"},
    {"cod_prov": "35", "nombre": "Las Palmas", "capital": "Las Palmas de Gran Canaria", "ccaa": "Canarias"},
    {"cod_prov": "36", "nombre": "Pontevedra", "capital": "Pontevedra", "ccaa": "Galicia"},
    {"cod_prov": "37", "nombre": "Salamanca", "capital": "Salamanca", "ccaa": "Castilla y León"},
    {"cod_prov": "38", "nombre": "Santa Cruz de Tenerife", "capital": "Santa Cruz de Tenerife", "ccaa": "Canarias"},
    {"cod_prov": "39", "nombre": "Cantabria", "capital": "Santander", "ccaa": "Cantabria"},
    {"cod_prov": "40", "nombre": "Segovia", "capital": "Segovia", "ccaa": "Castilla y León"},
    {"cod_prov": "41", "nombre": "Sevilla", "capital": "Sevilla", "ccaa": "Andalucía"},
    {"cod_prov": "42", "nombre": "Soria", "capital": "Soria", "ccaa": "Castilla y León"},
    {"cod_prov": "43", "nombre": "Tarragona", "capital": "Tarragona", "ccaa": "Cataluña"},
    {"cod_prov": "44", "nombre": "Teruel", "capital": "Teruel", "ccaa": "Aragón"},
    {"cod_prov": "45", "nombre": "Toledo", "capital": "Toledo", "ccaa": "Castilla-La Mancha"},
    {"cod_prov": "46", "nombre": "Valencia/València", "capital": "València", "ccaa": "Comunitat Valenciana"},
    {"cod_prov": "47", "nombre": "Valladolid", "capital": "Valladolid", "ccaa": "Castilla y León"},
    {"cod_prov": "48", "nombre": "Bizkaia", "capital": "Bilbao", "ccaa": "País Vasco"},
    {"cod_prov": "49", "nombre": "Zamora", "capital": "Zamora", "ccaa": "Castilla y León"},
    {"cod_prov": "50", "nombre": "Zaragoza", "capital": "Zaragoza", "ccaa": "Aragón"},
    {"cod_prov": "51", "nombre": "Ceuta", "capital": "Ceuta", "ccaa": "Ciudad Autónoma de Ceuta"},
    {"cod_prov": "52", "nombre": "Melilla", "capital": "Melilla", "ccaa": "Ciudad Autónoma de Melilla"},
]
