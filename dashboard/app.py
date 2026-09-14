"""
TUI AI Dashboard - Matriz Estratégica de Destinos Turísticos
Segmentación Bidimensional: Nivel de Saturación Actual (INE) vs. Potencial de Diversificación (OSM & Capacidad)
"""
import json
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="TUI AI Dashboard - Gestión de Destinos",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #E2E8F0;
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# --- CARGA Y CACHÉ DE DATOS ---
@st.cache_data
def cargar_datos():
    ruta_datos = Path("Datos procesados/TurismoProvincia_Clusters.csv")
    if not ruta_datos.exists():
        from scratch.generate_dual_clusters import df_master
        df = df_master.copy()
    else:
        df = pd.read_csv(ruta_datos)
    
    df['cod_prov'] = df['cod_prov'].astype(str).str.zfill(2)
    
    # Cargar GeoJSON de provincias
    ruta_geojson = Path("Datos procesados/provincias_geojson.json")
    geojson = None
    if ruta_geojson.exists():
        with open(ruta_geojson, "r", encoding="utf-8") as f:
            geojson = json.load(f)
            
    return df, geojson


df_provincias, geojson_espana = cargar_datos()

# --- SIDEBAR: FILTROS Y SELECTORES ---
st.sidebar.markdown("## 🧭 TUI Intelligence")
st.sidebar.markdown("### 🎛️ Filtros de Navegación")

todas_ccaa = ["Todas"] + sorted(df_provincias["comunidad_autonoma"].unique().tolist())
ccaa_seleccionada = st.sidebar.selectbox("Comunidad Autónoma:", todas_ccaa)

todas_politicas = ["Todas"] + sorted(df_provincias["politica_recomendada"].unique().tolist())
politica_seleccionada = st.sidebar.selectbox("Estrategia DMO Sugerida:", todas_politicas)

# Aplicar filtros
df_filtrado = df_provincias.copy()
if ccaa_seleccionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado["comunidad_autonoma"] == ccaa_seleccionada]
if politica_seleccionada != "Todas":
    df_filtrado = df_filtrado[df_filtrado["politica_recomendada"] == politica_seleccionada]

st.sidebar.markdown("---")
st.sidebar.markdown("### 📍 Ficha de Detalle Provincial")
provincia_seleccionada = st.sidebar.selectbox(
    "Selecciona una provincia:",
    options=sorted(df_provincias["provincia"].unique().tolist()),
    index=int(df_provincias[df_provincias["provincia"] == "Madrid"].index[0]) if "Madrid" in df_provincias["provincia"].values else 0
)

# --- CABECERA PRINCIPAL ---
st.markdown('<div class="main-title">🧭 TUI Intelligence: Matriz Estratégica de Destinos</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Doble segmentación: <b>Nivel de Saturación Actual (INE)</b> frente a <b>Potencial de Diversificación y Activos (OSM & Rural)</b> para 52 provincias españolas.</div>', unsafe_allow_html=True)

# --- TABS PRINCIPALES ---
tab_cuadrante, tab_mapas, tab_ficha = st.tabs([
    "📈 1. Cuadrante Estratégico (Scatter Plot)",
    "🗺️ 2. Selector de Mapas Georreferenciados",
    "📋 3. Diagnóstico Provincial DMO"
])


# ==============================================================================
# TAB 1: CUADRANTE INTERACTIVO (SCATTER PLOT)
# ==============================================================================
with tab_cuadrante:
    st.subheader("Cuadrante Estratégico de Destinos (Presión vs. Potencial)")
    st.markdown(
        "Este cuadrante sitúa a cada provincia según su **Nivel de Saturación/Presión actual** (Eje X) y su "
        "**Índice de Activos y Capacidad Disponible** (Eje Y). Las líneas punteadas representan la mediana nacional."
    )
    
    med_x = float(df_provincias['indice_saturacion'].median())
    med_y = float(df_provincias['indice_potencial'].median())
    
    fig_scatter = px.scatter(
        df_filtrado,
        x='indice_saturacion',
        y='indice_potencial',
        color='politica_recomendada',
        hover_name='provincia',
        hover_data={
            'comunidad_autonoma': True,
            'cluster_saturacion': True,
            'cluster_potencial': True,
            'presion_turistica_hab': ':.2f',
            'activos_culturales': True,
            'capacidad_rural_libre': ':.0f',
            'margen_hotel_valle': ':.0f',
            'indice_saturacion': False,
            'indice_potencial': False
        },
        text='provincia',
        labels={
            'indice_saturacion': 'Presión y Saturación Turística Actual (Eje X) →',
            'indice_potencial': 'Capacidad y Activos Disponibles para Diversificación (Eje Y) →',
            'politica_recomendada': 'Estrategia Recomendada'
        },
        height=650,
        color_discrete_map={
            "Objetivo Prioritario: Inversión y Diversificación": "#10B981",
            "Desestacionalización y Gestión de Flujos": "#3B82F6",
            "Alerta de Saturación: Contención y Desvío de Demanda": "#EF4444",
            "Turismo Pausado / Ecoturismo de Nicho": "#F59E0B"
        }
    )
    
    fig_scatter.update_traces(
        textposition='top center',
        marker=dict(size=14, line=dict(width=1.5, color='DarkSlateGrey'), opacity=0.88),
        textfont=dict(size=10, family="sans-serif")
    )
    
    fig_scatter.add_vline(x=med_x, line_dash="dash", line_color="#9CA3AF", annotation_text="Mediana Saturación", annotation_position="top")
    fig_scatter.add_hline(y=med_y, line_dash="dash", line_color="#9CA3AF", annotation_text="Mediana Potencial", annotation_position="right")
    
    row_sel = df_provincias[df_provincias['provincia'] == provincia_seleccionada].iloc[0]
    fig_scatter.add_trace(go.Scatter(
        x=[row_sel['indice_saturacion']],
        y=[row_sel['indice_potencial']],
        mode='markers+text',
        marker=dict(size=22, color='#7C3AED', symbol='star', line=dict(width=2, color='white')),
        name=f"Seleccionada: {provincia_seleccionada}",
        text=[f"★ {provincia_seleccionada}"],
        textposition='bottom center',
        hoverinfo='skip'
    ))
    
    st.plotly_chart(fig_scatter, use_container_width=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.success("**🌟 Joyas de Oportunidad**\n\n*(Baja saturación, Alto potencial)*\n\nObjetivo prioritario de promoción e inversión turística. Provincias con alta riqueza cultural y capacidad rural sin masificación.")
    with col2:
        st.info("**⚠️ Destinos Maduros / Dinámicos**\n\n*(Alta saturación, Alto potencial)*\n\nMetrópolis y polos consolidados. Requieren desestacionalización hacia meses valle y redistribución hacia zonas periféricas.")
    with col3:
        st.error("**🛑 Hotspots al Límite**\n\n*(Alta saturación, Bajo potencial)*\n\nDestinos con alta presión turística y escaso margen de absorción. Necesidad de contención y preservación ambiental.")
    with col4:
        st.warning("**🌿 Ecoturismo de Nicho**\n\n*(Baja saturación, Bajo potencial)*\n\nProvincias de interior profundo. Estrategia orientada a experiencias de autenticidad, turismo pausado y pequeña escala.")


# ==============================================================================
# TAB 2: SELECTOR DE MAPAS GEORREFERENCIADOS
# ==============================================================================
with tab_mapas:
    st.subheader("Mapa Territorial Georreferenciado")
    
    perspectiva = st.radio(
        "Seleccione la perspectiva analítica a visualizar en el mapa:",
        options=[
            "🔴 Perspectiva 1: Nivel de Saturación y Madurez Actual (Cluster 1 - INE)",
            "🟢 Perspectiva 2: Potencial de Diversificación y Capacidad Disponible (Cluster 2 - OSM & Rural)"
        ],
        horizontal=True
    )
    
    if "Perspectiva 1" in perspectiva:
        col_color = "cluster_saturacion"
        titulo_mapa = "Segmentación Territorial por Saturación Actual (INE)"
        hover_info = {
            'cod_prov': False,
            'cluster_saturacion': True,
            'presion_turistica_hab': ':.2f',
            'ocupacion_hotel_media': ':.1f',
            'estacionalidad_cv': ':.2f',
            'politica_recomendada': True
        }
        color_map = {
            "Desaprovechado": "#10B981",
            "Destinos Maduros": "#F59E0B",
            "Hipersaturado": "#EF4444",
            "Grandes Metrópolis": "#6366F1"
        }
    else:
        col_color = "cluster_potencial"
        titulo_mapa = "Segmentación Territorial por Potencial de Activos (OSM & Capacidad Rural)"
        hover_info = {
            'cod_prov': False,
            'cluster_potencial': True,
            'activos_culturales': True,
            'restaurantes_osm': True,
            'capacidad_rural_libre': ':.0f',
            'margen_hotel_valle': ':.0f',
            'politica_recomendada': True
        }
        color_map = {
            "Alto Potencial Cultural y Desestacionalizable": "#10B981",
            "Megadestinos con Gran Capacidad Ociosa en Valle": "#3B82F6",
            "Potencial Ecoturístico y Rural de Interior": "#F59E0B",
            "Capacidad Territorial Reducida": "#9CA3AF"
        }
    
    if geojson_espana:
        if hasattr(px, "choropleth_map"):
            fig_map = px.choropleth_map(
                df_filtrado,
                geojson=geojson_espana,
                locations='cod_prov',
                featureidkey='properties.COD_PROV',
                color=col_color,
                hover_name='provincia',
                hover_data=hover_info,
                map_style="carto-positron",
                zoom=4.8,
                center={"lat": 40.4168, "lon": -3.7038},
                opacity=0.78,
                color_discrete_map=color_map,
                height=600
            )
        else:
            fig_map = px.choropleth(
                df_filtrado,
                geojson=geojson_espana,
                locations='cod_prov',
                featureidkey='properties.COD_PROV',
                color=col_color,
                hover_name='provincia',
                hover_data=hover_info,
                color_discrete_map=color_map,
                height=600
            )
            fig_map.update_geos(fitbounds="locations", visible=False)
    else:
        fig_map = px.scatter_geo(
            df_filtrado,
            lat='lat',
            lon='lon',
            color=col_color,
            hover_name='provincia',
            size='total_poi_osm',
            color_discrete_map=color_map,
            height=600
        )
        fig_map.update_geos(fitbounds="locations", visible=False)
        
    st.plotly_chart(fig_map, use_container_width=True)
    
    with st.expander("📊 Ver tabla completa de provincias y clusters"):
        st.dataframe(
            df_filtrado[[
                'cod_prov', 'provincia', 'comunidad_autonoma',
                'cluster_saturacion', 'cluster_potencial', 'politica_recomendada',
                'presion_turistica_hab', 'activos_culturales', 'capacidad_rural_libre'
            ]].rename(columns={
                'cod_prov': 'Código',
                'provincia': 'Provincia',
                'comunidad_autonoma': 'CCAA',
                'cluster_saturacion': 'Cluster Saturación',
                'cluster_potencial': 'Cluster Potencial',
                'politica_recomendada': 'Estrategia DMO',
                'presion_turistica_hab': 'Presión Turística',
                'activos_culturales': 'Activos OSM',
                'capacidad_rural_libre': 'Plazas Rurales Libres'
            }),
            use_container_width=True,
            hide_index=True
        )


# ==============================================================================
# TAB 3: DIAGNÓSTICO PROVINCIAL DMO
# ==============================================================================
with tab_ficha:
    p_data = df_provincias[df_provincias['provincia'] == provincia_seleccionada].iloc[0]
    
    st.subheader(f"Ficha Estratégica: {provincia_seleccionada} ({p_data['comunidad_autonoma']})")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric(
            label="Nivel de Saturación Actual",
            value=p_data['cluster_saturacion'],
            delta=f"Presión: {p_data['presion_turistica_hab']:.2f} hab"
        )
    with col_b:
        st.metric(
            label="Arquetipo de Potencial",
            value=p_data['cluster_potencial'],
            delta=f"Activos OSM: {int(p_data['activos_culturales'])} POIs"
        )
    with col_c:
        st.metric(
            label="Estrategia DMO Recomendada",
            value=p_data['politica_recomendada']
        )
        
    st.markdown("---")
    
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("Estacionalidad (CV)", f"{p_data['estacionalidad_cv']:.2f}")
    mcol2.metric("Ocupación Hotelera Pico", f"{p_data['ocupacion_hotel_pico']:.1f}%")
    mcol3.metric("Plazas Rurales Libres", f"{int(p_data['capacidad_rural_libre']):,} plazas")
    mcol4.metric("Margen Hotelero Valle", f"{int(p_data['margen_hotel_valle']):,} plazas")
    
    st.markdown("### 📌 Diagnóstico y Recomendaciones TUI para el Destino")
    if p_data['politica_recomendada'] == "Objetivo Prioritario: Inversión y Diversificación":
        st.success(
            f"**Diagnóstico para {provincia_seleccionada}:** Destino con excelente dotación de patrimonio cultural "
            f"({int(p_data['activos_culturales'])} museos y monumentos) y alta capacidad rural disponible "
            f"({int(p_data['capacidad_rural_libre'])} plazas libres), combinada con una baja saturación residencial. "
            f"\n\n**Recomendación TUI:** Prioridad máxima para campañas de marketing de destino, desarrollo de nuevos paquetes de turismo cultural/gastronómico y atracción de demanda de valor añadido fuera de temporada."
        )
    elif p_data['politica_recomendada'] == "Desestacionalización y Gestión de Flujos":
        st.info(
            f"**Diagnóstico para {provincia_seleccionada}:** Destino consolidado con elevada demanda pero también con gran "
            f"margen de capacidad hotelera ociosa en temporada baja ({int(p_data['margen_hotel_valle'])} plazas desocupadas en valle). "
            f"\n\n**Recomendación TUI:** Desarrollar productos turísticos específicos para primavera y otoño (turismo MICE, deportivo, gastronómico) para reducir la dependencia de los meses pico y amortiguar la presión estacional."
        )
    elif p_data['politica_recomendada'] == "Alerta de Saturación: Contención y Desvío de Demanda":
        st.error(
            f"**Diagnóstico para {provincia_seleccionada}:** Alta presión turística relativa con escaso margen de absorción adicional. "
            f"Riesgo de sobrecarga de infraestructuras y fricción comunitaria. "
            f"\n\n**Recomendación TUI:** No expandir la promoción de volumen. Fomentar el desvío de flujos hacia comarcas y provincias adyacentes de menor presión y aplicar métricas ESG de control de capacidad de carga."
        )
    else:
        st.warning(
            f"**Diagnóstico para {provincia_seleccionada}:** Destino de interior o escala territorial acotada con demanda moderada. "
            f"\n\n**Recomendación TUI:** Apostar por experiencias de turismo pausado, turismo de silencio, astroturismo y valor diferencial sin buscar volumen masivo."
        )
