"""Escritura de tablas a CSV (UTF-8 con BOM)."""
import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)


def save_table(df: pd.DataFrame, table_name: str, output_dir: Path, mode: str = "overwrite") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{table_name}.csv"
    if df.empty:
        return filepath
    if mode == "append" and filepath.exists():
        df.to_csv(filepath, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(filepath, mode="w", header=True, index=False, encoding="utf-8-sig")
    logger.info("%d filas -> %s", len(df), filepath.name)
    return filepath
