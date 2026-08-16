"""
Logger unificado para todo el pipeline.

Escribe simultáneamente a:
  - stdout (consola, forzado a UTF-8 para compatibilidad Windows).
  - data/logs/log_sesion_<YYYYMMDD_HHMMSS>.txt (UTF-8).

Formato de línea:
  2026-08-16 12:34:56 | INFO    | [CartoCiudad] Toledo -> cod_ine=45168
"""
import io
import logging
import sys
from datetime import datetime
from pathlib import Path

_session_file_handler: logging.FileHandler | None = None
_LOG_DIR = Path(__file__).resolve().parents[2] / "data" / "logs"


def _build_formatter() -> logging.Formatter:
    return logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def init_session_log(log_dir: Path | None = None) -> Path:
    """
    Crea el fichero de log de sesión y lo registra globalmente.
    Llama a esta función UNA VEZ al inicio de main()/pipeline.

    Devuelve la ruta al fichero creado.
    """
    global _session_file_handler

    target_dir = log_dir or _LOG_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = target_dir / f"log_sesion_{ts}.txt"

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_build_formatter())

    _session_file_handler = file_handler
    return log_path


def get_logger(name: str) -> logging.Logger:
    """
    Devuelve un logger con handler de consola (stdout) y, si se inicializó
    la sesión, también con handler de fichero.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        # Ya configurado; añadir file handler si aún no está
        if _session_file_handler and _session_file_handler not in logger.handlers:
            logger.addHandler(_session_file_handler)
        return logger

    logger.setLevel(logging.DEBUG)

    # Handler de consola — forzamos UTF-8 para que los símbolos de
    # estado (OK, SKIP, FAIL) no rompan en consolas Windows (cp1252).
    _utf8_stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    ) if hasattr(sys.stdout, "buffer") else sys.stdout
    console = logging.StreamHandler(_utf8_stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(_build_formatter())
    logger.addHandler(console)

    # Handler de fichero (si la sesión ya fue inicializada)
    if _session_file_handler:
        logger.addHandler(_session_file_handler)

    return logger
