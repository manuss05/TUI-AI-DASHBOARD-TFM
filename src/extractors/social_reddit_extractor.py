"""
Extractor de "buzz" social vía Reddit (PRAW), como proxy de popularidad
turística online.

Reddit es, de las redes sociales grandes, la que mantiene una API
gratuita razonablemente accesible en 2026 (requiere registrar una app en
https://www.reddit.com/prefs/apps, gratis, cuota generosa para uso no
comercial).

Estado real de otras redes (decisión metodológica para tu memoria de
TFM):
  - X/Twitter: desde 2023 el acceso de lectura relevante requiere un
    plan de pago (Basic/Pro); el tier gratuito es muy limitado. Si tu
    universidad/TFM no cubre ese coste, no es viable como fuente
    recurrente.
  - Instagram Graph API: solo da datos de CUENTAS PROPIAS de empresa/
    creador que tú administres, no búsqueda pública por localización;
    además exige revisión de la app por Meta. No sirve para "mencionas de
    turistas sobre un municipio" de forma general.
  - TikTok Research API: existe pero el acceso está restringido a
    investigadores verificados institucionalmente (proceso de solicitud
    específico, no inmediato).

Por eso este pipeline usa Reddit como fuente social principal y deja las
demás documentadas como trabajo futuro condicionado a aprobación.
"""
from datetime import datetime
import pandas as pd
import praw

from config.settings import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from src.utils.logger import get_logger

logger = get_logger(__name__)

SUBREDDITS_VIAJES_ESPANA = ["Spain", "SpainTravel", "spainforfun", "es"]


class RedditExtractor:
    def __init__(self):
        if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET):
            logger.warning("Credenciales de Reddit no configuradas: define REDDIT_CLIENT_ID/SECRET en .env")
        self.reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )

    def count_mentions(self, municipio: str, cod_ine: str, limit: int = 100) -> pd.DataFrame:
        rows = []
        for sub in SUBREDDITS_VIAJES_ESPANA:
            try:
                count = sum(1 for _ in self.reddit.subreddit(sub).search(municipio, limit=limit))
            except Exception as e:
                logger.warning("Fallo buscando '%s' en r/%s: %s", municipio, sub, e)
                count = None
            rows.append({
                "cod_ine": cod_ine,
                "fuente_social": "Reddit",
                "canal": f"r/{sub}",
                "num_menciones": count,
                "fecha_extraccion": datetime.utcnow().isoformat(),
            })
        return pd.DataFrame(rows)
