"""Escritura de tablas a CSV (UTF-8 con BOM)."""
from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


def save_table(df: pd.DataFrame, table_name: str, output_dir: Path, mode: str = "overwrite") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{table_name}.csv"
    if df.empty:
        return filepath
    try:
        if mode == "append" and filepath.exists():
            df.to_csv(filepath, mode="a", header=False, index=False, encoding="utf-8-sig")
        else:
            df.to_csv(filepath, mode="w", header=True, index=False, encoding="utf-8-sig")
    except PermissionError as exc:
        fallback_path = output_dir / f"{table_name}_actualizado.csv"
        logger.warning(
            "No se pudo escribir en %s (bloqueado por otro proceso como Excel). Guardando copia en %s. Detalle: %s",
            filepath.name,
            fallback_path.name,
            exc,
        )
        df.to_csv(fallback_path, mode="w", header=True, index=False, encoding="utf-8-sig")
        filepath = fallback_path
    logger.info("%d filas -> %s", len(df), filepath.name)
    return filepath
