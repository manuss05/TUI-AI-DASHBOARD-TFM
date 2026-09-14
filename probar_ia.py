"""
Script de prueba para comprobar el servicio de Inteligencia Artificial (TUI AI).
Ejecutar desde la raíz del proyecto con:
    python probar_ia.py
"""
import sys
from pathlib import Path

# Aseguramos que la carpeta raíz esté en el path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dashboard.ai_service import TuiTourismAI

ai = TuiTourismAI()
print(f"Estado del servicio IA: {'Activo (Gemini API)' if ai.active else 'Modo Local / Fallback'}\n")

# Datos de ejemplo de una provincia
datos_segovia = {
    "provincia": "Segovia",
    "cod_prov": "40",
    "cuadrante": "Oportunidad de Diversificación (Alto Potencial, Baja Saturación)",
    "viajeros_total": 450000,
    "ocupacion_hotel_media": 43.1,
    "margen_hotel_valle": 4500,
    "capacidad_rural_libre": 1200,
    "cultura_y_patrimonio": 364,
    "ocio_y_naturaleza": 359,
    "restauracion": 526,
    "total_poi_osm": 1572
}

print("Generando dictamen ejecutivo para Segovia...\n")
informe_ejecutivo = ai.generar_diagnostico_provincial(datos_segovia)

# Imprimir asegurando codificación en consola
try:
    print(informe_ejecutivo)
except UnicodeEncodeError:
    print(informe_ejecutivo.encode("utf-8", errors="replace").decode("utf-8"))

# Generar informe en formato HTML profesional
archivo_html = "informe_segovia_tui.html"
ai.generar_informe_html(datos_segovia, archivo_salida=archivo_html)
print(f"\n[OK] Informe HTML corporativo TUI generado con exito en: {archivo_html}")
