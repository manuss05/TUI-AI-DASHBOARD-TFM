"""Logger del pipeline."""
import logging
import sys
from datetime import datetime
from pathlib import Path

_session_file_handler: logging.FileHandler | None = None
_LOG_DIR = Path(__file__).resolve().parents[2] / "data" / "logs"


def init_session_log(log_dir: Path | None = None) -> Path:
    global _session_file_handler
    target_dir = log_dir or _LOG_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    _session_file_handler = fh
    return log_path


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        if _session_file_handler and _session_file_handler not in logger.handlers:
            logger.addHandler(_session_file_handler)
        return logger
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(ch)
    if _session_file_handler:
        logger.addHandler(_session_file_handler)
    return logger
