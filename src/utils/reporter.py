"""Registro de fallos del pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FailureRecord:
    modulo: str
    ambito: str
    tipo_error: str
    mensaje: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class FailureReporter:

    def __init__(self) -> None:
        self._records: list[FailureRecord] = []

    def record(self, modulo: str, ambito: str, mensaje: str, exc: Optional[BaseException] = None) -> None:
        tipo = type(exc).__name__ if exc else "Error"
        self._records.append(FailureRecord(modulo=modulo, ambito=ambito, tipo_error=tipo, mensaje=mensaje))
        logger.warning("[FALLO] %s | %s: %s", modulo, ambito, mensaje[:120])

    def record_skip(self, modulo: str, motivo: str) -> None:
        self._records.append(FailureRecord(modulo=modulo, ambito="-", tipo_error="Omitido", mensaje=motivo))
        logger.warning("[SKIP] %s: %s", modulo, motivo)

    def save(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / "reporte_fallos.csv"
        cols = ["_meta.timestamp", "_meta.modulo", "_meta.ambito", "_meta.tipo_error", "_meta.mensaje"]
        if self._records:
            rows = [{"_meta.timestamp": r.timestamp, "_meta.modulo": r.modulo, "_meta.ambito": r.ambito,
                     "_meta.tipo_error": r.tipo_error, "_meta.mensaje": r.mensaje} for r in self._records]
            df = pd.DataFrame(rows, columns=cols)
        else:
            df = pd.DataFrame(columns=cols)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info("Reporte: %d fallos -> %s", len(self._records), filepath.name)
        return filepath
