# TUI Group - Gestión Estratégica del Turismo (España)

Dashboard analítico interactivo desarrollado para la toma de decisiones y gestión turística estratégica de TUI Group en España (TFM). Combina datos del INE, cartografía oficial y puntos de interés de OpenStreetMap para clasificar las provincias según su saturación y potencial turístico (clustering K-Means), integrando además prescripciones estratégicas generadas mediante Inteligencia Artificial conectada a Google Gemini.

**Dashboard web desplegada en Azure:**
[https://dashboardtuispain-augjh4a0h9arbpan.spaincentral-01.azurewebsites.net/](https://dashboardtuispain-augjh4a0h9arbpan.spaincentral-01.azurewebsites.net/)

---

## Requisitos previos

- Python 3.12 o superior.
- Clave de API de Google Gemini (Google AI Studio) para las consultas de IA.

---

## Instalación

1. **Crear y activar entorno virtual:**

   - **Windows:**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
2. **Instalar dependencias:**

   ```bash
   pip install -r requirements.txt
   ```
3. **Configurar variables de entorno:**
   Copia el archivo `.env.example` a `.env` y añade tu clave:

   ```env
   GEMINI_API_KEY="clave"
   ```

---

## Ejecución

### Dashboard interactivo (Streamlit)

```bash
streamlit run dashboard/app.py
```

Se abrirá automáticamente en tu navegador en `http://localhost:8501`.

*(Opcional)* Para ejecutar el pipeline de extracción de datos abiertos:

```bash
python Extractor/main.py
```

### Cuadernos Jupyter (Local y Google Colab)

Los cuadernos (`01_limpieza_y_revision.ipynb` y `02_EDA_y_clustering.ipynb`) incorporan autodetección de entorno:

- **Local:** Ajusta `sys.path` y rutas relativas de forma transparente.
- **Google Colab:** Monta Google Drive, posiciona el directorio de trabajo en la carpeta del proyecto e instala dependencias adicionales (`geopandas`, `duckdb`, `pyarrow`).

> **Nota sobre los datos:** Siguiendo las buenas prácticas habituales, los conjuntos de datos generados (`.csv` y `.parquet`) deberían incluirse en el `.gitignore`. No obstante, para agilizar los tiempos de ejecución, evitar esperas prolongadas en las llamadas a las APIs y facilitar una reproducción inmediata tanto en local como en Google Colab, se han incluido y versionado directamente en el repositorio.
