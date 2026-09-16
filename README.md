# TUI Group - Gestión Estratégica del Turismo (España)

Dashboard analítico interactivo desarrollado para la toma de decisiones y gestión turística estratégica de TUI Group en España (TFM). Combina datos del INE, cartografía oficial y puntos de interés de OpenStreetMap para clasificar las provincias según su saturación y potencial turístico (clustering K-Means), integrando además prescripciones estratégicas generadas mediante Inteligencia Artificial conectada a Google Gemini.

🌐 **Aplicación web desplegada en Azure:**  
[https://dashboardtuispain-augjh4a0h9arbpan.spaincentral-01.azurewebsites.net/](https://dashboardtuispain-augjh4a0h9arbpan.spaincentral-01.azurewebsites.net/)

---

## Requisitos previos

- Python 3.10 o superior (compatible con 3.11 y 3.12).
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
   GEMINI_API_KEY=tu_clave_de_gemini
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
