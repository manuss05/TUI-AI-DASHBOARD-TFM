"""
Registro y reporte de fallos del pipeline.

Uso:
    reporter = FailureReporter()
    reporter.record("OSM_Overpass", "Toledo", "Timeout al consultar Overpass", exc)
    ...
    reporter.save(DATA_PROCESSED_DIR)   # escribe reporte_fallos.csv

Columnas del CSV de fallos (todas con prefijo _meta para distinguirlas):
    _meta.timestamp      — Cuándo ocurrió el error (ISO 8601).
    _meta.modulo         — Nombre del extractor / paso que falló.
    _meta.ambito         — Municipio, provincia o ámbito afectado.
    _meta.tipo_error     — Nombre de la clase de excepción (p.ej. Timeout).
    _meta.mensaje        — Mensaje de error completo.
"""
from __future__ import annotations

import traceback
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
    """Acumula fallos durante el pipeline y los exporta al final."""

    def __init__(self) -> None:
        self._records: list[FailureRecord] = []

    def record(
        self,
        modulo: str,
        ambito: str,
        mensaje: str,
        exc: Optional[BaseException] = None,
    ) -> None:
        """
        Registra un fallo.

        Parámetros
        ----------
        modulo   : Nombre del módulo/extractor que falló.
        ambito   : Municipio, provincia o ámbito donde ocurrió.
        mensaje  : Descripción legible del error.
        exc      : Excepción capturada (opcional, para extraer el tipo).
        """
        tipo = type(exc).__name__ if exc else "Error"
        detalle = f"{mensaje} | {traceback.format_exc(limit=3).strip()}" if exc else mensaje

        rec = FailureRecord(
            modulo=modulo,
            ambito=ambito,
            tipo_error=tipo,
            mensaje=detalle,
        )
        self._records.append(rec)
        logger.warning("[reporter] ✗  %s | %s → %s: %s", modulo, ambito, tipo, mensaje)

    def record_skip(self, modulo: str, motivo: str) -> None:
        """Registra un módulo omitido por falta de credenciales u otra razón."""
        rec = FailureRecord(
            modulo=modulo,
            ambito="—",
            tipo_error="Omitido",
            mensaje=motivo,
        )
        self._records.append(rec)
        logger.warning("[reporter] ⊘  %s omitido → %s", modulo, motivo)

    def has_failures(self) -> bool:
        return len(self._records) > 0

    def summary(self) -> str:
        if not self._records:
            return "✔ Sin fallos registrados."
        lines = [f"\n{'='*60}", "  RESUMEN DE FALLOS DEL PIPELINE", f"{'='*60}"]
        for r in self._records:
            lines.append(f"  [{r.modulo}] {r.ambito} — {r.tipo_error}: {r.mensaje[:120]}")
        lines.append(f"{'='*60}")
        lines.append(f"  Total fallos: {len(self._records)}")
        lines.append(f"{'='*60}\n")
        return "\n".join(lines)

    def save(self, output_dir: Path) -> Path:
        """
        Escribe reporte_fallos.csv en UTF-8 con BOM.
        Si no hay fallos escribe igualmente el CSV (vacío con cabeceras)
        para confirmar que el pipeline terminó sin errores.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / "reporte_fallos.csv"

        cols = [
            "_meta.timestamp",
            "_meta.modulo",
            "_meta.ambito",
            "_meta.tipo_error",
            "_meta.mensaje",
        ]

        if self._records:
            rows = [
                {
                    "_meta.timestamp": r.timestamp,
                    "_meta.modulo": r.modulo,
                    "_meta.ambito": r.ambito,
                    "_meta.tipo_error": r.tipo_error,
                    "_meta.mensaje": r.mensaje,
                }
                for r in self._records
            ]
            df = pd.DataFrame(rows, columns=cols)
        else:
            df = pd.DataFrame(columns=cols)

        df.to_csv(filepath, index=False, encoding="utf-8-sig")

        if self._records:
            logger.warning(
                "[reporter] ⚠  Reporte de fallos guardado (%d entradas) → %s",
                len(self._records),
                filepath.name,
            )
        else:
            logger.info(
                "[reporter] ✔  Sin fallos. Reporte vacío guardado → %s",
                filepath.name,
            )

        return filepath
