"""
Cliente HTTP compartido por todos los extractores.
Aplica reintentos con backoff exponencial (tenacity) y respeta un
User-Agent identificable, algo que exigen explícitamente APIs como
OSM Nominatim/Overpass.
"""
import time
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import REQUEST_TIMEOUT, USER_AGENT, DEFAULT_SLEEP_BETWEEN_CALLS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HttpClient:
    def __init__(self, base_headers: dict | None = None, min_interval: float = DEFAULT_SLEEP_BETWEEN_CALLS):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        if base_headers:
            self.session.headers.update(base_headers)
        self.min_interval = min_interval
        self._last_call = 0.0

    def _throttle(self):
        elapsed = time.time() - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.time()

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout, requests.HTTPError)),
        reraise=True,
    )
    def get(self, url: str, params: dict | None = None, headers: dict | None = None) -> requests.Response:
        self._throttle()
        resp = self.session.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 429:
            logger.warning("Rate limit alcanzado en %s, esperando antes de reintentar...", url)
            time.sleep(5)
            resp.raise_for_status()
        resp.raise_for_status()
        return resp

    def post(self, url: str, json: dict | None = None, data=None, headers: dict | None = None) -> requests.Response:
        self._throttle()
        resp = self.session.post(url, json=json, data=data, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp
