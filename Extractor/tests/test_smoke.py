import json
import numpy as np
import pandas as pd
import pytest

from src.extractors.aemet_extractor import AEMETExtractor
from src.extractors.datosgob_extractor import DatosGobExtractor
from src.extractors.ine_extractor import INEExtractor
from src.metrics import compute_derived_metrics, extract_monthly_viajeros_by_province, extract_population_by_province
from src.schema import TABLE_SCHEMAS, empty_dataframe


def test_schema_tables_have_columns():
    expected_tables = {
        "INE_provincias",
        "municipios_espana",
        "flujo_ine_provincia",
        "flujo_ine_localidad",
        "rentabilidad_H",
        "gasto_turistico",
        "metricas_derivadas",
        "Carto_provincias",
        "oferta_osm",
        "clima_aemet",
        "datosgob_catalogo",
    }
    for table in expected_tables:
        assert table in TABLE_SCHEMAS
        assert len(TABLE_SCHEMAS[table]) > 0


def test_empty_dataframe_matches_schema():
    for name in TABLE_SCHEMAS:
        df = empty_dataframe(name)
        assert list(df.columns) == TABLE_SCHEMAS[name]


def test_aemet_extractor_inactive():
    ext = AEMETExtractor(api_key="")
    assert ext.is_active is False
    ext.close()


def test_datosgob_extractor_theme_and_columns():
    ext = DatosGobExtractor()
    df = ext.get_theme_datasets(theme="turismo", page_size=20, max_pages=1)
    assert not df.empty
    assert len(df) >= 20
    assert list(df.columns) == TABLE_SCHEMAS["datosgob_catalogo"]
    assert (df["theme"] == "turismo").all()
    assert df["about"].iloc[0].startswith("http")


def test_datosgob_extractor_search_datasets_limit():
    ext = DatosGobExtractor()
    df = ext.search_datasets(keyword="turismo", limit=15)
    assert not df.empty
    assert len(df) == 15
    assert (df["theme"] == "turismo").all()


def test_ine_rentabilidad_H():
    ine = INEExtractor()
    df = ine.get_rentabilidad_H(n_ultimos=1)
    assert not df.empty
    assert list(df.columns) == TABLE_SCHEMAS["rentabilidad_H"]
    # Comprobar que contiene datos de ADR (2059) y RevPAR (2057)
    tablas = set(df["tabla_id"].unique())
    assert 2059 in tablas or 2057 in tablas


def test_ine_gasto_turistico():
    ine = INEExtractor()
    df = ine.get_gasto_turistico(n_ultimos=1)
    assert not df.empty
    assert list(df.columns) == TABLE_SCHEMAS["gasto_turistico"]
    tablas = set(df["tabla_id"].unique())
    assert 10839 in tablas or 10835 in tablas


def test_compute_derived_metrics_synthetic():
    # Crear datos sintéticos de población
    pob_rows = [
        {
            "COD": "P01",
            "Nombre": "Araba. Total.",
            "T3_Unidad": "Personas",
            "T3_Escala": "",
            "Fecha": "2024-01-01",
            "T3_Periodo": "",
            "T3_TipoDato": "",
            "Anyo": 2024,
            "Valor": 100000.0,
            "MetaData_json": json.dumps([
                {"T3_Variable": "Provincias", "Codigo": "01", "Nombre": "Araba/Álava"},
                {"T3_Variable": "Sexo", "Nombre": "Total"},
            ]),
            "tabla_id": 2852,
            "_meta.fecha_extraccion": "2026-09-01T00:00:00",
        },
        {
            "COD": "P28",
            "Nombre": "Madrid. Total.",
            "T3_Unidad": "Personas",
            "T3_Escala": "",
            "Fecha": "2024-01-01",
            "T3_Periodo": "",
            "T3_TipoDato": "",
            "Anyo": 2024,
            "Valor": 500000.0,
            "MetaData_json": json.dumps([
                {"T3_Variable": "Provincias", "Codigo": "28", "Nombre": "Madrid"},
                {"T3_Variable": "Sexo", "Nombre": "Total"},
            ]),
            "tabla_id": 2852,
            "_meta.fecha_extraccion": "2026-09-01T00:00:00",
        },
    ]
    df_pob = pd.DataFrame(pob_rows)

    # Crear datos sintéticos de flujos mensuales (valores: [100, 200, 300] para prov 01)
    flujo_rows = []
    # Prov 01: 3 meses con valores 100, 200, 300 -> media=200, std=100 (ddof=1), cv=0.5, total=600, presion=600/100000=0.006
    for idx, val in enumerate([100.0, 200.0, 300.0], start=1):
        flujo_rows.append({
            "COD": f"F01_{idx}",
            "Nombre": "Araba. Viajero. Total categorías. Total.",
            "T3_Unidad": "Viajeros",
            "T3_Escala": "",
            "Fecha": f"2024-{idx:02d}-01",
            "T3_Periodo": f"M{idx:02d}",
            "T3_TipoDato": "Dato",
            "Anyo": 2024,
            "Valor": val,
            "MetaData_json": json.dumps([
                {"T3_Variable": "Provincias", "Codigo": "01", "Nombre": "Araba/Álava"},
                {"T3_Variable": "Concepto turístico", "Nombre": "Viajero", "Codigo": "B"},
                {"T3_Variable": "RESIDENCIA/ORIGEN", "Nombre": "Total"},
            ]),
            "tabla_id": 2074,
            "_meta.fecha_extraccion": "2026-09-01T00:00:00",
        })

    # Prov 28: 3 meses constantes 1000.0 -> media=1000, std=0, cv=0, total=3000, presion=3000/500000=0.006
    for idx in range(1, 4):
        flujo_rows.append({
            "COD": f"F28_{idx}",
            "Nombre": "Madrid. Viajero. Total categorías. Total.",
            "T3_Unidad": "Viajeros",
            "T3_Escala": "",
            "Fecha": f"2024-{idx:02d}-01",
            "T3_Periodo": f"M{idx:02d}",
            "T3_TipoDato": "Dato",
            "Anyo": 2024,
            "Valor": 1000.0,
            "MetaData_json": json.dumps([
                {"T3_Variable": "Provincias", "Codigo": "28", "Nombre": "Madrid"},
                {"T3_Variable": "Concepto turístico", "Nombre": "Viajero", "Codigo": "B"},
                {"T3_Variable": "RESIDENCIA/ORIGEN", "Nombre": "Total"},
            ]),
            "tabla_id": 2074,
            "_meta.fecha_extraccion": "2026-09-01T00:00:00",
        })

    df_flujo = pd.DataFrame(flujo_rows)

    df_result = compute_derived_metrics(df_poblacion=df_pob, df_flujo=df_flujo)

    assert len(df_result) == 2
    assert list(df_result.columns) == TABLE_SCHEMAS["metricas_derivadas"]

    # Validar provincia 01
    row_01 = df_result[df_result["cod_prov"] == "01"].iloc[0]
    assert row_01["total_viajeros"] == pytest.approx(600.0)
    assert row_01["media_mensual_viajeros"] == pytest.approx(200.0)
    assert row_01["std_mensual_viajeros"] == pytest.approx(100.0)
    assert row_01["indice_estacionalidad"] == pytest.approx(0.5)
    assert row_01["presion_turistica"] == pytest.approx(600.0 / 100000.0)

    # Validar provincia 28
    row_28 = df_result[df_result["cod_prov"] == "28"].iloc[0]
    assert row_28["total_viajeros"] == pytest.approx(3000.0)
    assert row_28["media_mensual_viajeros"] == pytest.approx(1000.0)
    assert row_28["std_mensual_viajeros"] == pytest.approx(0.0)
    assert row_28["indice_estacionalidad"] == pytest.approx(0.0)
    assert row_28["presion_turistica"] == pytest.approx(3000.0 / 500000.0)


def test_compute_derived_metrics_empty_inputs():
    df_empty = compute_derived_metrics(df_poblacion=pd.DataFrame(), df_flujo=pd.DataFrame())
    assert list(df_empty.columns) == TABLE_SCHEMAS["metricas_derivadas"]
    assert df_empty.empty


def test_extract_population_by_province_gender_breakdown():
    """Verifica que extract_population_by_province tome la población TOTAL y no la femenina o masculina."""
    pob_rows = [
        # Albacete: Total 386464, Hombres 193205, Mujeres 193259
        {
            "COD": "DPOP160",
            "Nombre": "Albacete. Total. Total habitantes. Personas. ",
            "Valor": 386464.0,
            "MetaData_json": json.dumps([
                {"T3_Variable": "Provincias", "Nombre": "Albacete", "Codigo": "02"},
                {"T3_Variable": "Sexo", "Nombre": "Total", "Codigo": "0"},
                {"T3_Variable": "Tamaño de los municipios", "Nombre": "Total habitantes", "Codigo": "0"},
            ]),
        },
        {
            "COD": "DPOP161",
            "Nombre": "Albacete. Hombres. Total habitantes. Personas. ",
            "Valor": 193205.0,
            "MetaData_json": json.dumps([
                {"T3_Variable": "Provincias", "Nombre": "Albacete", "Codigo": "02"},
                {"T3_Variable": "Sexo", "Nombre": "Hombres", "Codigo": "1"},
                {"T3_Variable": "Tamaño de los municipios", "Nombre": "Total habitantes", "Codigo": "0"},
            ]),
        },
        {
            "COD": "DPOP162",
            "Nombre": "Albacete. Mujeres. Total habitantes. Personas. ",
            "Valor": 193259.0,
            "MetaData_json": json.dumps([
                {"T3_Variable": "Provincias", "Nombre": "Albacete", "Codigo": "02"},
                {"T3_Variable": "Sexo", "Nombre": "Mujeres", "Codigo": "2"},
                {"T3_Variable": "Tamaño de los municipios", "Nombre": "Total habitantes", "Codigo": "0"},
            ]),
        },
    ]
    df_pob = pd.DataFrame(pob_rows)
    p_map = extract_population_by_province(df_pob)

    assert "02" in p_map
    assert p_map["02"]["poblacion"] == 386464.0
    assert p_map["02"]["poblacion"] != 193259.0


def test_extract_monthly_viajeros_by_province_multi_origin():
    """Verifica que se filtren únicamente los viajeros TOTALES y no residentes/extranjeros por separado."""
    rows = []
    # 3 meses con 3 series distintas para cada mes: Total (1000), Residentes España (400), Extranjeros (600)
    for m_idx in range(1, 4):
        # 1. Total viajeros
        rows.append({
            "COD": f"V_TOT_{m_idx}",
            "Nombre": "Madrid. Viajero. Total categorías. Total. Dato. ",
            "T3_Periodo": f"M{m_idx:02d}",
            "Anyo": 2024,
            "Valor": 1000.0,
            "MetaData_json": json.dumps([
                {"T3_Variable": "Provincias", "Nombre": "Madrid", "Codigo": "28"},
                {"T3_Variable": "Concepto turístico", "Nombre": "Viajero", "Codigo": "B"},
                {"T3_Variable": "RESIDENCIA/ORIGEN", "Nombre": "Total", "Codigo": "0"},
            ]),
        })
        # 2. Residentes España
        rows.append({
            "COD": f"V_ESP_{m_idx}",
            "Nombre": "Madrid. Viajero. Total categorías. Residentes en España. Dato. ",
            "T3_Periodo": f"M{m_idx:02d}",
            "Anyo": 2024,
            "Valor": 400.0,
            "MetaData_json": json.dumps([
                {"T3_Variable": "Provincias", "Nombre": "Madrid", "Codigo": "28"},
                {"T3_Variable": "Concepto turístico", "Nombre": "Viajero", "Codigo": "B"},
                {"T3_Variable": "RESIDENCIA/ORIGEN", "Nombre": "Residentes en España", "Codigo": "1"},
            ]),
        })
        # 3. Pernoctaciones Total (no debe incluirse)
        rows.append({
            "COD": f"P_TOT_{m_idx}",
            "Nombre": "Madrid. Pernoctaciones. Total categorías. Total. Dato. ",
            "T3_Periodo": f"M{m_idx:02d}",
            "Anyo": 2024,
            "Valor": 2500.0,
            "MetaData_json": json.dumps([
                {"T3_Variable": "Provincias", "Nombre": "Madrid", "Codigo": "28"},
                {"T3_Variable": "Concepto turístico", "Nombre": "Pernoctaciones", "Codigo": "A"},
                {"T3_Variable": "RESIDENCIA/ORIGEN", "Nombre": "Total", "Codigo": "0"},
            ]),
        })

    df_flujo = pd.DataFrame(rows)
    df_extracted = extract_monthly_viajeros_by_province(df_flujo)

    assert len(df_extracted) == 3
    assert (df_extracted["viajeros"] == 1000.0).all()


def test_ine_rentabilidad_H_custom_table():
    ine = INEExtractor()
    df_2066 = ine.get_rentabilidad_H(n_ultimos=1, tables=[2066])
    assert not df_2066.empty
    assert list(df_2066.columns) == TABLE_SCHEMAS["rentabilidad_H"]
    assert 2066 in set(df_2066["tabla_id"].unique())


def test_compute_derived_metrics_real_processed_consistency():
    """Valida la consistencia matemática de las métricas derivadas con datos procesados reales."""
    df_metrics = compute_derived_metrics()
    if df_metrics.empty:
        pytest.skip("Archivos procesados no disponibles en este entorno.")

    assert len(df_metrics) == 52
    assert (df_metrics["n_meses"] == 12).all()
    assert (df_metrics["poblacion"] > 50000).all()
    assert (df_metrics["total_viajeros"] > 0).all()
    assert (df_metrics["presion_turistica"] > 0).all()
    assert (df_metrics["indice_estacionalidad"] >= 0).all()


def test_extract_population_and_viajeros_ceuta_melilla():
    """Verifica que Ceuta (51) y Melilla (52) se extraigan correctamente desde metadatos de CCAA."""
    pob_rows = [
        {
            "COD": "DPOP33147",
            "Nombre": "Ceuta. Total. Total habitantes. Personas.",
            "Valor": 83517.0,
            "MetaData_json": json.dumps([
                {"T3_Variable": "Provincias", "Nombre": "Ceuta", "Codigo": "51"},
                {"T3_Variable": "Sexo", "Nombre": "Total", "Codigo": "0"},
            ]),
        },
        {
            "COD": "DPOP33144",
            "Nombre": "Melilla. Total. Total habitantes. Personas.",
            "Valor": 86261.0,
            "MetaData_json": json.dumps([
                {"T3_Variable": "Provincias", "Nombre": "Melilla", "Codigo": "52"},
                {"T3_Variable": "Sexo", "Nombre": "Total", "Codigo": "0"},
            ]),
        },
    ]
    df_pob = pd.DataFrame(pob_rows)
    p_map = extract_population_by_province(df_pob)
    assert p_map["51"]["poblacion"] == 83517.0
    assert p_map["52"]["poblacion"] == 86261.0

    flujo_rows = [
        {
            "COD": "EOT1811",
            "Nombre": "Ceuta. Viajeros. Total.",
            "T3_Periodo": "M01",
            "Valor": 5000.0,
            "MetaData_json": json.dumps([
                {"T3_Variable": "Comunidades y Ciudades Autónomas", "Nombre": "Ceuta", "Codigo": "18"},
                {"T3_Variable": "Concepto turístico", "Nombre": "Viajero", "Codigo": "B"},
                {"T3_Variable": "RESIDENCIA/ORIGEN", "Nombre": "Total", "Codigo": "0"},
            ]),
        },
        {
            "COD": "EOT1817",
            "Nombre": "Melilla. Viajeros. Total.",
            "T3_Periodo": "M01",
            "Valor": 6000.0,
            "MetaData_json": json.dumps([
                {"T3_Variable": "Comunidades y Ciudades Autónomas", "Nombre": "Melilla", "Codigo": "19"},
                {"T3_Variable": "Concepto turístico", "Nombre": "Viajero", "Codigo": "B"},
                {"T3_Variable": "RESIDENCIA/ORIGEN", "Nombre": "Total", "Codigo": "0"},
            ]),
        },
    ]
    df_flujo = pd.DataFrame(flujo_rows)
    df_viajeros = extract_monthly_viajeros_by_province(df_flujo)
    assert len(df_viajeros) == 2
    assert set(df_viajeros["cod_prov"]) == {"51", "52"}


def test_text_only_fallback_extraction():
    """Verifica la extracción correcta por texto cuando no hay MetaData_json."""
    pob_rows = [
        {"COD": "P_ALB", "Nombre": "Albacete. Total. Total habitantes. Personas.", "Valor": 386464.0},
        {"COD": "P_MAD", "Nombre": "Madrid. Total. Total habitantes. Personas.", "Valor": 6751251.0},
        {"COD": "P_COR", "Nombre": "Coruña, A. Total. Total habitantes. Personas.", "Valor": 1120134.0},
        {"COD": "P_PAL", "Nombre": "Palmas, Las. Total. Total habitantes. Personas.", "Valor": 1128539.0},
        {"COD": "P_RIO", "Nombre": "Rioja, La. Total. Total habitantes. Personas.", "Valor": 319796.0},
    ]
    p_map = extract_population_by_province(pd.DataFrame(pob_rows))
    assert "02" in p_map and p_map["02"]["poblacion"] == 386464.0
    assert "28" in p_map and p_map["28"]["poblacion"] == 6751251.0
    assert "15" in p_map and p_map["15"]["poblacion"] == 1120134.0
    assert "35" in p_map and p_map["35"]["poblacion"] == 1128539.0
    assert "26" in p_map and p_map["26"]["poblacion"] == 319796.0

    flujo_rows = [
        {"COD": "F_ALB", "Nombre": "Albacete. Viajero. Total categorías. Total.", "T3_Periodo": "M01", "Valor": 15000.0},
        {"COD": "F_MAD", "Nombre": "Madrid. Viajero. Total categorías. Total.", "T3_Periodo": "M01", "Valor": 500000.0},
        {"COD": "F_COR", "Nombre": "A Coruña. Viajeros. Total.", "T3_Periodo": "M01", "Valor": 80000.0},
        {"COD": "F_PAL", "Nombre": "Las Palmas. Viajeros. Total.", "T3_Periodo": "M01", "Valor": 200000.0},
        {"COD": "F_TF", "Nombre": "Santa Cruz Tenerife. Viajeros. Total.", "T3_Periodo": "M01", "Valor": 180000.0},
        {"COD": "F_VIZ", "Nombre": "Vizcaya. Viajeros. Total.", "T3_Periodo": "M01", "Valor": 90000.0},
        {"COD": "F_GUI", "Nombre": "Guipúzcoa. Viajeros. Total.", "T3_Periodo": "M01", "Valor": 70000.0},
        {"COD": "F_ALA", "Nombre": "Alava. Viajeros. Total.", "T3_Periodo": "M01", "Valor": 30000.0},
    ]
    df_viaj = extract_monthly_viajeros_by_province(pd.DataFrame(flujo_rows))
    assert len(df_viaj) == 8
    assert set(df_viaj["cod_prov"]) == {"02", "28", "15", "35", "38", "48", "20", "01"}


def test_text_only_ccaa_exclusion():
    """Verifica que las series de agregados autonómicos (CCAA) se excluyan en modo texto y no dupliquen provincias."""
    flujo_rows = [
        {"COD": "CCAA_MAD", "Nombre": "Madrid (Comunidad de). Viajeros. Total.", "T3_Periodo": "M01", "Valor": 500000.0},
        {"COD": "PROV_MAD", "Nombre": "Madrid. Viajero. Total categorías. Total. Dato. ", "T3_Periodo": "M01", "Valor": 500000.0},
        {"COD": "CCAA_MUR", "Nombre": "Murcia (Región de). Viajeros. Total.", "T3_Periodo": "M01", "Valor": 120000.0},
        {"COD": "PROV_MUR", "Nombre": "Murcia. Viajero. Total categorías. Total. Dato. ", "T3_Periodo": "M01", "Valor": 120000.0},
        {"COD": "CCAA_NAV", "Nombre": "Navarra (Comunidad Foral de). Viajeros. Total.", "T3_Periodo": "M01", "Valor": 90000.0},
        {"COD": "PROV_NAV", "Nombre": "Navarra. Viajero. Total categorías. Total. Dato. ", "T3_Periodo": "M01", "Valor": 90000.0},
        {"COD": "CCAA_AND", "Nombre": "Andalucía. Viajeros. Total.", "T3_Periodo": "M01", "Valor": 1500000.0},
        {"COD": "CCAA_PV", "Nombre": "País Vasco. Viajeros. Total.", "T3_Periodo": "M01", "Valor": 300000.0},
        {"COD": "CCAA_NAC", "Nombre": "Total Nacional. Total. Total habitantes. Personas.", "T3_Periodo": "M01", "Valor": 47000000.0},
    ]
    df_viaj = extract_monthly_viajeros_by_province(pd.DataFrame(flujo_rows))
    assert len(df_viaj) == 3
    assert set(df_viaj["cod_prov"]) == {"28", "30", "31"}


def test_aemet_extractor_empty_schema():
    """Verifica que AEMETExtractor devuelva DataFrame con esquema válido cuando está inactivo o sin datos."""
    ext = AEMETExtractor(api_key="")
    df = ext.get_predicciones_municipios([])
    assert list(df.columns) == TABLE_SCHEMAS["clima_aemet"]
    assert df.empty
    ext.close()



