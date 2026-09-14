import pandas as pd


def crear_fecha(
    df: pd.DataFrame,
    col_anyo: str = "Anyo",
    col_periodo: str = "Periodo",
    col_prov: str = "COD_PROV",
    nombre_col_fecha: str = "Fecha",
) -> pd.DataFrame:
    df = df.copy()

    # Limpiar el periodo (quitar 'M' y asegurar 2 dígitos con zfill)
    mes_limpio = (
        df[col_periodo]
        .astype(str)
        .str.upper()
        .str.replace("M", "", regex=False)
        .str.strip()
        .str.zfill(2)
    )

    # Crear la fecha YYYY-MM-01
    df[nombre_col_fecha] = pd.to_datetime(
        df[col_anyo].astype(str) + "-" + mes_limpio,
        format="%Y-%m"
    )

    # Ordenar por provincia y fecha si la columna de provincia existe
    cols_orden = [c for c in [col_prov, nombre_col_fecha] if c in df.columns]
    if cols_orden:
        df = df.sort_values(by=cols_orden).reset_index(drop=True)

    return df


def calcular_variacion_interanual(
    df: pd.DataFrame,
    columna_metrica: str | list[str],
    col_grupo: str = "COD_PROV",
    periodos: int = 12,
    sufijo: str = "_var_interanual_%",
) -> pd.DataFrame:
    df = df.copy()

    metricas = [columna_metrica] if isinstance(columna_metrica, str) else columna_metrica

    for col in metricas:
        if col in df.columns:
            nombre_nueva_col = f"{col}{sufijo}"
            if col_grupo in df.columns:
                df[nombre_nueva_col] = (
                    df.groupby(col_grupo)[col].pct_change(periods=periodos) * 100
                )
            else:
                df[nombre_nueva_col] = df[col].pct_change(periods=periodos) * 100

    return df