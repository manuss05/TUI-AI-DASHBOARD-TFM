import pandas as pd
import json

def añadir_prefijo_col(df, 
                       id, 
                       prefijo):
    
    """Fórmula para incluir prefijos en los df antes de realizar el merge()
    df = dataframe
    id= columna de identificador (COD_INE O COD_PROV)
    prefijo: prefijo a incluir"""
    
    df[id] = df[id].astype('Int64')
    return df.set_index(id).add_prefix(prefijo).reset_index()



def estacionador(df, 
                 *columnas):
    
    """Para transformar en las columnas seleccionadas el mes formato M01 a su estacion"""
    #Definimos valores de estaciones
    orden_estaciones = ['Invierno', 'Primavera', 'Verano', 'Otoño']
    mapa_estaciones = {
        'M01': 'Invierno', 'M02': 'Invierno', 'M03': 'Invierno', 
        
        'M04': 'Primavera', 'M05': 'Primavera', 'M06': 'Primavera',
        
        'M07': 'Verano', 'M08': 'Verano', 'M09': 'Verano',
        
        'M10': 'Otoño', 'M11': 'Otoño', 'M12': 'Otoño',} #Dict para transformar variables en estaciones y agrupar
    
    #listamos columnas
    if not columnas:
        cols_a_transformar = [col for col in df.columns if 'periodo' in col.lower()]
    else:
        cols_a_transformar = list(columnas)
        
    for col in cols_a_transformar:
        if col in df.columns:
            # Limpiar espacios y pasar a mayúsculas por seguridad
            df[col] = df[col].astype(str).str.strip().str.upper()
            df[col] = df[col].map(mapa_estaciones).fillna(df[col])
            # Convertir a categórico ordenado
            df[col] = pd.Categorical(df[col], categories=orden_estaciones, ordered=True)
    return df



def cambiar_tipodato(df, 
                     colnumeric,
                     colfloat,
                     colcat):
    """Cambiar coma decimal por punto
    Y transformar a categórica o numérica si procede"""
    
    for col in colfloat:
        df[col] = (
            df[col]
            .astype("string")
            .str.strip()
            .str.replace(",", ".", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="raise")

    df = df.astype({
        **{col: "Int64" for col in colnumeric},
        **{col: "category" for col in colcat},
    })
    return df



def obtener_codigo_INE(df):
    """Formula definida para extraer un valor específico de una columna específica de varios dfs
    El valor extraido es el ultimo del primer diccionario que encontramos"""
    try:
        elementos = json.loads(df) if isinstance(df, str) else df
        if isinstance(elementos, list):
            for item in elementos:
                variable = item.get('T3_Variable', '').lower()
                # Sirve tanto para 'PUNTOS TURÍSTICOS' (flujo) como para 'Municipios' (padrón)
                if 'punto' in variable or 'muni' in variable:
                    return item.get('Codigo')
    except (json.JSONDecodeError, TypeError, IndexError):
        return None
    return None

def obtener_codigo_provincia_INE(df):
    try:
        elementos = json.loads(df) if isinstance(df, str) else df
        if isinstance(elementos, list):
            for item in elementos:
                # Buscamos únicamente la dimensión de Provincias
                if 'prov' in item.get('T3_Variable', '').lower():
                    return item.get('Codigo')
    except Exception:
        return None
    return None

def crear_fecha(
    df: pd.DataFrame,
    col_anyo: str = 'Anyo',
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