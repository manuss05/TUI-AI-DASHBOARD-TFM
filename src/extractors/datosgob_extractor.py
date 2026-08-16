"""
Extractor de datos.gob.es — catálogo nacional de datos abiertos
(agrega datasets de ministerios, comunidades autónomas y ayuntamientos,
muchos de ellos sobre turismo, ocupación hotelera, pernoctaciones, etc.).

API real ("apidata"): https://datos.gob.es/es/apidata
Portal de documentación: https://datos.gob.es/es/accessible-apis

No requiere clave. Este extractor NO descarga los datos finales (el
formato de cada dataset lo decide su publicador: CSV, XLSX, JSON, API
propia...), sino que busca datasets relevantes y expone sus recursos
descargables, para que decidas cuáles incorporar al pipeline (muchos
ayuntamientos/CCAA publican aquí sus propias estadísticas turísticas
municipales, que es justo el nivel de detalle que el INE no siempre
ofrece).
"""
from datetime import datetime
import pandas as pd
from src.utils.http_client import HttpClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://datos.gob.es/apidata/catalog/dataset"


class DatosGobExtractor:
    def __init__(self):
        self.client = HttpClient()

    def search_datasets(self, keyword: str, limit: int = 20) -> pd.DataFrame:
        """
        Busca datasets por palabra clave (p.ej. "turismo", "ocupación
        hotelera", "pernoctaciones", "<nombre_municipio> turismo").
        """
        params = {"q": keyword, "_pageSize": limit}
        try:
            resp = self.client.get(f"{BASE_URL}.json", params=params)
            data = resp.json()
        except Exception as e:
            logger.warning("Fallo consultando datos.gob.es para '%s': %s", keyword, e)
            return pd.DataFrame(columns=["titulo_dataset", "descripcion", "url_recurso", "formato", "publicador"])

        items = data.get("result", {}).get("items", []) if isinstance(data, dict) else []
        rows = []
        for item in items:
            titulo = item.get("title", {}).get("_value") if isinstance(item.get("title"), dict) else item.get("title")
            descripcion = item.get("description", {}).get("_value") if isinstance(item.get("description"), dict) else item.get("description")
            publicador = item.get("publisher")
            for dist in item.get("distribution", []):
                rows.append({
                    "titulo_dataset": titulo,
                    "descripcion": descripcion,
                    "url_recurso": dist.get("accessURL") or dist.get("downloadURL"),
                    "formato": dist.get("format"),
                    "publicador": publicador,
                    "fecha_extraccion": datetime.utcnow().isoformat(),
                })
        return pd.DataFrame(rows)
