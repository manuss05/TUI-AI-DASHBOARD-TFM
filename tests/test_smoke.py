from src.schema import TABLE_SCHEMAS, empty_dataframe
from src.pipeline import _cod_ine_provisional
from src.extractors.aemet_extractor import AEMETExtractor


def test_schema_tables_have_columns():
    for table, cols in TABLE_SCHEMAS.items():
        assert len(cols) > 0


def test_empty_dataframe_matches_schema():
    for name in TABLE_SCHEMAS:
        df = empty_dataframe(name)
        assert list(df.columns) == TABLE_SCHEMAS[name]


def test_cod_ine_provisional_is_stable():
    a = _cod_ine_provisional("Madrid")
    b = _cod_ine_provisional("Madrid")
    c = _cod_ine_provisional("Barcelona")
    assert a == b
    assert a != c
    assert a.startswith("PROV_")


def test_aemet_extractor_inactive():
    ext = AEMETExtractor(api_key="")
    assert ext.is_active is False
    ext.close()
