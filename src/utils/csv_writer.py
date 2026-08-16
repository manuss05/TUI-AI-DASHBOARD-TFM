"""
Escritura de las tablas del modelo relacional a CSV.
Cada tabla se guarda en un CSV independiente dentro de data/processed/,
enlazable por la clave 'cod_ine' (ver src/schema.py).
"""
import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)


def save_table(df: pd.DataFrame, table_name: str, output_dir: Path, mode: str = "overwrite") -> Path:
    """
    Guarda un DataFrame como CSV.
    mode="overwrite": sobrescribe el fichero.
    mode="append": añade filas a un CSV existente (crea cabecera si no existe).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{table_name}.csv"

    if mode == "append" and filepath.exists():
        df.to_csv(filepath, mode="a", header=False, index=False, encoding="utf-8")
    else:
        df.to_csv(filepath, mode="w", header=True, index=False, encoding="utf-8")

    logger.info("Guardadas %d filas en %s", len(df), filepath)
    return filepath
