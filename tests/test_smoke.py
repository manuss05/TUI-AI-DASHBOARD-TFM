from src.extractors.aemet_extractor import AEMETExtractor
from src.schema import TABLE_SCHEMAS, empty_dataframe


def test_schema_tables_have_columns():
    for table, cols in TABLE_SCHEMAS.items():
        assert len(cols) > 0


def test_empty_dataframe_matches_schema():
    for name in TABLE_SCHEMAS:
        df = empty_dataframe(name)
        assert list(df.columns) == TABLE_SCHEMAS[name]


def test_aemet_extractor_inactive():
    ext = AEMETExtractor(api_key="")
    assert ext.is_active is False
    ext.close()
