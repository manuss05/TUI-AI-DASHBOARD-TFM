"""
Tests de humo: no requieren red, comprueban que el esquema y la
generación provisional de códigos son consistentes. Ejecutar con:
    pytest tests/
"""
from src.schema import TABLE_SCHEMAS, empty_dataframe
from src.pipeline import _cod_ine_provisional


def test_schema_tables_have_columns():
    for table, cols in TABLE_SCHEMAS.items():
        assert len(cols) > 0, f"La tabla {table} no tiene columnas definidas"


def test_empty_dataframe_matches_schema():
    df = empty_dataframe("localidades")
    assert list(df.columns) == TABLE_SCHEMAS["localidades"]


def test_cod_ine_provisional_is_stable():
    a = _cod_ine_provisional("Madrid")
    b = _cod_ine_provisional("Madrid")
    c = _cod_ine_provisional("Barcelona")
    assert a == b
    assert a != c
    assert len(a) == 8
