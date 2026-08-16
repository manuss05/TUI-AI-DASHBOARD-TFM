"""
Extractor del INE (Instituto Nacional de Estadística).

API pública real, gratuita, SIN clave: "Tempus3" (JSON-Stat / JSON simple).
Documentación oficial: https://www.ine.es/dyngs/DataLab/manual.html?cid=45
Base URL: https://servicios.ine.es/wstempus/js/ES/

Diseño deliberado: en vez de "hardcodear" IDs de tablas concretas (que
cambian de una publicación a otra y no debo dar por buenos sin poder
verificarlos en vivo desde este entorno), este módulo implementa un flujo
de DESCUBRIMIENTO:
  1. search_operations(keyword)   -> encuentra la "operación estadística"
     (p.ej. "Cifras de Población", "Atlas de distribución de renta de los
     hogares").
  2. get_tables_for_operation(id) -> lista las tablas de esa operación.
  3. get_table_data(table_id)     -> descarga los datos de una tabla.

Antes de usarlo en serio, ejecuta search_operations() para confirmar los
IDs exactos de las operaciones/tablas que necesitas (renta, población,
ocupación hotelera) y anótalos en config/settings.py para no repetir la
búsqueda cada vez.
"""
from datetime import datetime
import pandas as pd

from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://servicios.ine.es/wstempus/js/ES"


class INEExtractor:
    def __init__(self):
        self.client = HttpClient()

    def search_operations(self, keyword: str) -> pd.DataFrame:
        """Busca operaciones estadísticas del INE cuyo nombre contenga `keyword`."""
        resp = self.client.get(f"{BASE_URL}/OPERACIONES_DISPONIBLES")
        data = resp.json()
        df = pd.DataFrame(data)
        if "Nombre" in df.columns:
            mask = df["Nombre"].str.contains(keyword, case=False, na=False)
            return df[mask][["Id", "Cod_IOE", "Nombre"]]
        return df

    def get_tables_for_operation(self, operation_id: int) -> pd.DataFrame:
        """Lista las tablas asociadas a una operación (p.ej. la de Renta o Población)."""
        resp = self.client.get(f"{BASE_URL}/TABLAS_OPERACION/{operation_id}")
        data = resp.json()
        return pd.DataFrame(data)

    def get_table_data(self, table_id: int, n_ultimos: int | None = None) -> pd.DataFrame:
        """
        Descarga los datos de una tabla concreta.
        `n_ultimos`: si se indica, solo trae los N últimos periodos publicados.
        """
        url = f"{BASE_URL}/DATOS_TABLA/{table_id}"
        params = {}
        if n_ultimos:
            params["nult"] = n_ultimos
        resp = self.client.get(url, params=params)
        data = resp.json()

        rows = []
        for serie in data:
            nombre_serie = serie.get("Nombre", "")
            for dato in serie.get("Data", []):
                rows.append({
                    "nombre_serie": nombre_serie,
                    "anio": dato.get("Anyo"),
                    "periodo": dato.get("NombrePeriodo"),
                    "valor": dato.get("Valor"),
                    "fecha_extraccion": datetime.utcnow().isoformat(),
                })
        return pd.DataFrame(rows)


if __name__ == "__main__":
    # Ejemplo de descubrimiento manual (requiere red):
    ine = INEExtractor()
    print(ine.search_operations("renta"))
    print(ine.search_operations("población"))
    print(ine.search_operations("ocupación"))
