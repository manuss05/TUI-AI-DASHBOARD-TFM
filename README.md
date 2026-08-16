# TFM · Extractor de datos turísticos por localidad (España)

Pipeline de extracción de datos abiertos para construir un dataset relacional
de apoyo a un AI-Dashboard de gestión de oferta turística por
**municipio / provincia / comunidad autónoma**.

## 1. Qué hace

1. **Extrae** datos de varias fuentes (una por módulo en `src/extractors/`).
2. **Guarda** cada fuente como CSV independiente en `data/processed/`.
3. Todas las tablas se relacionan mediante la clave `cod_ine` (código INE del
   municipio), lo que permite hacer `JOIN` directo en pandas, SQLite o el
   motor que uses para el dashboard.

Extracción y persistencia están deliberadamente separadas (`src/extractors/`
vs `src/utils/csv_writer.py`) para poder cambiar el destino (CSV → SQLite/
Postgres) sin tocar la lógica de extracción.

## 2. Estado real de cada fuente

He sido deliberadamente honesto sobre el acceso real a cada fuente que
mencionaste, porque esto es defendible en la memoria de un TFM:

| Fuente | ¿Clave? | Nivel de detalle | Estado en este repo |
|---|---|---|---|
| **INE** (Tempus3) | No | Renta, demografía: municipio. Flujos turísticos (FRONTUR/EGATUR, EOAT): sobre todo provincia/CCAA | Implementado (`ine_extractor.py`), con descubrimiento dinámico de tablas |
| **IGN / CartoCiudad** | No | Geocodificación de municipios | Implementado con manejo defensivo de errores (`ign_extractor.py`) — verifica el contrato del endpoint antes de producción |
| **OpenStreetMap** (Nominatim + Overpass) | No | Geocodificación + conteo de POIs turísticos por municipio | Implementado y es la fuente más fiable de "oferta turística" a nivel municipal (`osm_extractor.py`) |
| **datos.gob.es** | No | Variable (agrega datasets de CCAA/ayuntamientos, muchos con detalle municipal) | Implementado como buscador de datasets (`datosgob_extractor.py`) |
| **TripAdvisor** | Sí (gratis, con aprobación) | POI, rating, nº reseñas | Implementado (`tripadvisor_extractor.py`); pide la clave en tripadvisor.com/developers |
| **Booking.com** | No disponible para uso individual/académico | — | **No implementado** — no tiene API de autoservicio; ver alternativas en `booking_extractor.py` |
| **Redes sociales** | Reddit: sí (gratis) · X/Twitter: de pago desde 2023 · Instagram: solo cuentas propias · TikTok: solo investigadores verificados | Menciones/buzz | Solo Reddit implementado (`social_reddit_extractor.py`); el resto documentado como limitación |
| **Google Places** | Sí (de pago tras cuota gratuita) | POIs, ratings | Clave prevista en `.env` pero extractor no incluido en esta versión — añádelo si tu presupuesto lo permite, reutilizando `http_client.py` |

## 3. Modelo relacional (`src/schema.py`)

```
localidades (cod_ine PK) ──┬── demografia (cod_ine FK, anio)
                            ├── renta (cod_ine FK, anio)
                            ├── turismo_oferta_osm (cod_ine FK)
                            ├── tripadvisor_pois (cod_ine FK)
                            └── redes_sociales_buzz (cod_ine FK)

turismo_flujo_ine (cod_ambito, nivel_ambito)  -- provincia/CCAA, no siempre municipio
datasets_datosgob (cod_ine_relacionado opcional) -- catálogo de datasets descubiertos
```

`cod_ine` es la clave porque es el identificador estándar y estable de la
estadística oficial española (INE, IGN, Catastro...). El `_cod_ine_provisional()`
de `src/pipeline.py` es un **hash temporal** para desarrollo — sustitúyelo por
el código INE real de 5 dígitos antes de usar el dataset en serio (se puede
obtener del Nomenclátor/Callejero del INE o de datos.gob.es).

## 4. Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # y rellena las claves que vayas obteniendo
```

## 5. Ejecución

```bash
# Pipeline completo con el listado de municipios de demo (config/settings.py)
python main.py

# Solo algunas fuentes
python main.py --sources localidades turismo_oferta_osm
```

Los CSV resultantes aparecen en `data/processed/`.

## 6. Antes de usarlo "en serio" (importante)

- **INE**: ejecuta `python -m src.extractors.ine_extractor` para descubrir en
  vivo los IDs exactos de las operaciones de renta/población/ocupación
  hotelera que necesitas, y cachéalos en `config/settings.py`. No he
  hardcodeado IDs de tabla porque cambian entre publicaciones y no puedo
  verificarlos desde este entorno sin red.
- **IGN/CartoCiudad**: confirma el contrato del endpoint REST en
  cartociudad.es/webapi antes de depender de él en producción; el módulo
  ya cae automáticamente a OSM Nominatim si falla.
- **Lista completa de municipios**: sustituye `MUNICIPIOS_DEMO` en
  `config/settings.py` por el listado completo (~8.100 municipios) —
  puedes obtenerlo del Nomenclátor del INE o de datos.gob.es.
- **Rate limits**: Overpass y Nominatim son gratuitos pero se saturan con
  8.100 municipios en bucle; para el dataset completo, procesa por lotes
  con pausas, o considera un servicio de pago/self-hosted Overpass.

## 7. Subir a GitHub (repositorio privado)

Este directorio ya está listo para convertirse en un repositorio git. Desde
tu máquina (no desde este sandbox, que no tiene acceso a tu cuenta de
GitHub):

```bash
cd tfm-turismo-espana
git init
git add .
git commit -m "Pipeline inicial de extracción de datos turísticos"

# Opción A: con GitHub CLI (crea el repo privado y hace push en un paso)
gh repo create tfm-turismo-espana --private --source=. --remote=origin --push

# Opción B: crear el repo vacío desde github.com y luego
git remote add origin https://github.com/TU_USUARIO/tfm-turismo-espana.git
git branch -M main
git push -u origin main
```

**No subas nunca el archivo `.env`** con tus claves reales — ya está excluido
en `.gitignore`.

## 8. Próximos pasos sugeridos para el TFM

- Sustituir CSV por SQLite/PostgreSQL cuando el volumen crezca (mismo
  `schema.py` sirve de base para las `CREATE TABLE`).
- Añadir un extractor de "Encuesta de Ocupación en Alojamientos Turísticos"
  del INE específico, una vez descubiertos los IDs de tabla.
- Dashboard: Streamlit/Power BI/Plotly Dash leyendo directamente los CSV de
  `data/processed/` unidos por `cod_ine`.
- Documentar en la memoria del TFM las limitaciones de granularidad
  (turismo_flujo_ine a nivel provincia/CCAA) como parte del análisis crítico
  de fuentes — es un punto metodológico legítimo, no un defecto a esconder.
