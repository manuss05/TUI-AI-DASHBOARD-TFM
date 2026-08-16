"""
Configuración central del proyecto.
Carga variables de entorno desde .env y define rutas y parámetros comunes.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Rutas ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"

DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# --- Claves API (opcionales según la fuente) ---
TRIPADVISOR_API_KEY = os.getenv("TRIPADVISOR_API_KEY", "")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "tfm-turismo-espana/0.1")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")

# --- Parámetros de red ---
REQUEST_TIMEOUT = 30          # segundos
DEFAULT_SLEEP_BETWEEN_CALLS = 1.0  # segundos, para respetar rate limits (Nominatim exige >=1s)
USER_AGENT = "tfm-turismo-espana-datascience/0.1 (uso academico; contacto: tu_email@example.com)"

# --- Ámbito del estudio ---
# Lista de municipios objetivo para las pruebas iniciales del pipeline.
# En producción, sustitúyela por el listado completo de municipios del INE
# (ver src/extractors/ine_extractor.py -> get_tables / discover).
MUNICIPIOS_DEMO = [
    {"nombre": "Madrid", "provincia": "Madrid", "ccaa": "Comunidad de Madrid"},
    {"nombre": "Barcelona", "provincia": "Barcelona", "ccaa": "Cataluña"},
    {"nombre": "Sevilla", "provincia": "Sevilla", "ccaa": "Andalucía"},
    {"nombre": "Valencia", "provincia": "Valencia/València", "ccaa": "Comunitat Valenciana"},
    {"nombre": "San Sebastián", "provincia": "Gipuzkoa", "ccaa": "País Vasco"},
    {"nombre": "Santiago de Compostela", "provincia": "A Coruña", "ccaa": "Galicia"},
    {"nombre": "Mérida", "provincia": "Badajoz", "ccaa": "Extremadura"},
]
