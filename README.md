# TFM - Pipeline de datos turisticos (Espana)

Pipeline de extraccion de datos abiertos para un dataset relacional de turismo por municipio/provincia/CCAA.

## Fuentes

| Fuente | Clave | Datos | Extractor |
|---|---|---|---|
| **INE** (Tempus3) | No | Poblacion, flujos turisticos | `ine_extractor.py` |
| **IGN / CartoCiudad** | No | Geocodificacion municipal | `ign_extractor.py` |
| **OpenStreetMap** | No | POIs turisticos | `osm_extractor.py` |
| **datos.gob.es** | No | Datasets abiertos | `datosgob_extractor.py` |
| **AEMET OpenData** | Si (gratuita) | Prediccion meteorologica | `aemet_extractor.py` |

## Instalacion

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Ejecucion

```bash
python main.py
python main.py --sources localidades clima_aemet
```

CSV en `data/processed/`.
