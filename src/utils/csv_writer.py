"""
Escritura de las tablas del modelo relacional a CSV.

Reglas:
  - Encoding: utf-8-sig (UTF-8 con BOM) para compatibilidad con Excel español.
  - Cada escritura imprime una línea de confirmación en consola.
  - Las columnas llegan ya nombradas con la convención Origen.NombreColumna
    desde los extractores; este módulo no altera los nombres.
"""
import pandas as pd
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)


def save_table(
    df: pd.DataFrame,
    table_name: str,
    output_dir: Path,
    mode: str = "overwrite",
) -> Path:
    """
    Guarda un DataFrame como CSV en UTF-8 con BOM (utf-8-sig).

    Parámetros
    ----------
    df          : DataFrame a guardar.
    table_name  : Nombre base del fichero (sin extensión).
    output_dir  : Directorio de destino (se crea si no existe).
    mode        : "overwrite" (por defecto) | "append".

    Devuelve la ruta absoluta del fichero generado.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{table_name}.csv"

    if df.empty:
        logger.warning(
            "[csv_writer] ⚠  DataFrame vacío para '%s'; no se escribe el fichero.",
            table_name,
        )
        return filepath

    if mode == "append" and filepath.exists():
        df.to_csv(
            filepath,
            mode="a",
            header=False,
            index=False,
            encoding="utf-8-sig",
        )
        logger.info(
            "[csv_writer] ↪  %d filas añadidas → %s",
            len(df),
            filepath.name,
        )
    else:
        df.to_csv(
            filepath,
            mode="w",
            header=True,
            index=False,
            encoding="utf-8-sig",
        )
        logger.info(
            "[csv_writer] ✔  %d filas guardadas → %s  [columnas: %s]",
            len(df),
            filepath.name,
            ", ".join(df.columns.tolist()),
        )

    return filepath
