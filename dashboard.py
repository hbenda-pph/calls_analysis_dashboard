# =============================================================================
# CALLS ANALYSIS DASHBOARD - ANÁLISIS DE PUNTOS DE INFLEXIÓN
# =============================================================================
# 
# Dashboard interactivo para análisis de puntos de inflexión en llamadas
# de ServiceTitan por compañía con soporte multiidioma.
# 
# INSTRUCCIONES:
# 1. Instalar Streamlit: pip install streamlit
# 2. Ejecutar: streamlit run dashboard.py
# 3. Abrir en navegador: http://localhost:8501
# 4. Cambiar idioma: ?lang=es o ?lang=en
# =============================================================================

import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from scipy.interpolate import make_interp_spline
from google.cloud import bigquery
import gettext
import locale
import os
import warnings
warnings.filterwarnings('ignore')

# Configuración de la página
st.set_page_config(
    page_title="ServiceTitan - Inflection Points Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CONFIGURACIÓN DE GETTEXT
# =============================================================================

def setup_gettext():
    """Configurar GETTEXT para traducciones"""
    
    # Detectar idioma del navegador o parámetro URL
    lang = st.query_params.get("lang", "en")
    
    # Si no hay parámetro, detectar idioma del sistema
    if lang == "en" and "lang" not in st.query_params:
        try:
            system_lang = locale.getdefaultlocale()[0][:2]
            if system_lang in ["es", "en"]:
                lang = system_lang
        except:
            lang = "en"
    
    # Configurar GETTEXT
    try:
        translation = gettext.translation(
            'messages', 
            'locales', 
            languages=[lang],
            fallback=True
        )
        translation.install()
        return translation.gettext
    except Exception as e:
        st.warning(f"Translation error: {e}. Using English.")
        return lambda x: x

# Configurar traducciones
_ = setup_gettext()

# =============================================================================
# FUNCIONES BASE (copiadas de base_functions_notebook.py)
# =============================================================================

@st.cache_data
def get_calls_info():
    """
    Extrae información consolidada de llamadas de ServiceTitan desde BigQuery.
    """
    try:
        client = bigquery.Client()
        
        query = f"""
           SELECT company_id AS `company_id`
                , COUNT(DISTINCT(campaign_id)) AS `campaigns`
                , COUNT(lead_call_customer_id) AS `customers`
                , location_state AS `state`
                , EXTRACT(YEAR FROM DATE(lead_call_created_on)) AS `year`
                , EXTRACT(MONTH FROM DATE(lead_call_created_on)) AS `month`
                , COUNT(lead_call_id) AS `calls`
             FROM `pph-central.silver.vw_consolidated_call_lead_location`
            WHERE DATE(lead_call_created_on) < DATE("2025-09-01")
            GROUP BY company_id, location_state, EXTRACT(YEAR FROM DATE(lead_call_created_on)), EXTRACT(MONTH FROM DATE(lead_call_created_on))
            ORDER BY company_id, location_state, EXTRACT(YEAR FROM DATE(lead_call_created_on)), EXTRACT(MONTH FROM DATE(lead_call_created_on))
        """
        
        query_job = client.query(query)
        results = query_job.result()
        
        calls_df = pd.DataFrame(results.to_dataframe())
        return calls_df
        
    except Exception as e:
        st.error(f"❌ {_('Error loading data. Check BigQuery connection.')}: {str(e)}")
        return None

def calculate_monthly_percentages(calls_df, company_id):
    """
    Calcula el porcentaje de llamadas por mes para una compañía específica.
    """
    # Filtrar datos de la compañía
    company_data = calls_df[calls_df['company_id'] == company_id].copy()
    
    if company_data.empty:
        return None, None, None
    
    # Agrupar por mes y sumar llamadas
    monthly_totals = company_data.groupby('month')['calls'].sum()
    
    # Crear array completo para los 12 meses
    monthly_calls = np.zeros(12)
    for month, calls in monthly_totals.items():
        monthly_calls[month - 1] = calls  # month es 1-12, array es 0-11
    
    # Calcular total y porcentajes
    total_calls = np.sum(monthly_calls)
    monthly_percentages = (monthly_calls / total_calls) * 100 if total_calls > 0 else np.zeros(12)
    
    return monthly_calls, monthly_percentages, total_calls

# =============================================================================
# FUNCIÓN DE ANÁLISIS (adaptada del script original)
# =============================================================================

def analyze_inflection_points_streamlit(calls_df, company_id):
    """
    Analiza los puntos de inflexión para una compañía específica (versión Streamlit)
    """
    # Calcular porcentajes mensuales
    monthly_calls, monthly_percentages, total_calls = calculate_monthly_percentages(calls_df, company_id)
    
    if monthly_percentages is None:
        return None, None, None, None, None, None
    
    # Crear array de meses (1-12)
    months = np.arange(1, 13)
    calls = monthly_percentages
    
    # Encontrar picos (máximos locales)
    peaks, _ = find_peaks(calls, height=np.mean(calls), distance=2)
    
    # Encontrar valles (mínimos locales)
    valleys, _ = find_peaks(-calls, height=-np.mean(calls), distance=2)
    
    return months, calls, peaks, valleys, total_calls, monthly_calls

def create_inflection_chart(months, calls, peaks, valleys, company_id):
    """
    Crea el gráfico de puntos de inflexión para Streamlit
    """
    # Crear figura
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Línea suave
    if len(months) > 3:
        x_smooth = np.linspace(months.min(), months.max(), 100)
        spl = make_interp_spline(months, calls, k=3)
        y_smooth = spl(x_smooth)
        ax.plot(x_smooth, y_smooth, '-', color='blue', linewidth=3, alpha=0.8)
    
    # Datos originales
    ax.plot(months, calls, 'o-', color='blue', linewidth=2, markersize=8, alpha=0.7)
    
    # Marcar picos
    if len(peaks) > 0:
        ax.plot(months[peaks], calls[peaks], '^', color='red', markersize=12, 
                label=f'Peaks ({len(peaks)})', markeredgecolor='darkred', markeredgewidth=2)
        
        # Anotar picos
        for peak in peaks:
            ax.annotate(f'Peak\nMonth {months[peak]}\n{calls[peak]:.1f}%', 
                        xy=(months[peak], calls[peak]), 
                        xytext=(months[peak], calls[peak] + np.max(calls)*0.1),
                        ha='center', va='bottom',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="red", alpha=0.7),
                        arrowprops=dict(arrowstyle='->', color='red'))
    
    # Marcar valles
    if len(valleys) > 0:
        ax.plot(months[valleys], calls[valleys], 'v', color='green', markersize=12,
                label=f'Valleys ({len(valleys)})', markeredgecolor='darkgreen', markeredgewidth=2)
        
        # Anotar valles
        for valley in valleys:
            ax.annotate(f'Valley\nMonth {months[valley]}\n{calls[valley]:.1f}%', 
                        xy=(months[valley], calls[valley]), 
                        xytext=(months[valley], calls[valley] - np.max(calls)*0.1),
                        ha='center', va='top',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="green", alpha=0.7),
                        arrowprops=dict(arrowstyle='->', color='green'))
    
    # Configurar gráfico
    ax.set_title(f'Inflection Points - Company {company_id}\nPeaks and Valleys Analysis in Calls', 
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('Month', fontsize=12)
    ax.set_ylabel('Percentage of Total Calls (%)', fontsize=12)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

# =============================================================================
# INTERFAZ DE STREAMLIT
# =============================================================================

def main():
    # Título principal
    st.title(_("ServiceTitan - Inflection Points Analysis"))
    st.markdown("---")
    
    # Sidebar para controles
    st.sidebar.header(_("Controls"))
    
    # Cargar datos
    with st.spinner(_("Loading data from BigQuery...")):
        calls_df = get_calls_info()
    
    if calls_df is None:
        st.error(_("Error loading data. Check BigQuery connection."))
        return
    
    # Obtener lista de compañías disponibles
    companies = sorted(calls_df['company_id'].unique())
    
    # Selector de compañía
    company_id = st.sidebar.selectbox(
        _("Select Company:"),
        options=companies,
        index=0,
        help=_("Select the company to analyze its inflection points")
    )
    
    # Información de la compañía seleccionada
    company_data = calls_df[calls_df['company_id'] == company_id]
    total_calls_company = company_data['calls'].sum()
    years_range = f"{company_data['year'].min()} - {company_data['year'].max()}"
    states = company_data['state'].unique()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### {_('Company Information')}")
    st.sidebar.write(f"**{_('ID:')}** {company_id}")
    st.sidebar.write(f"**{_('Total Calls:')}** {total_calls_company:,}")
    st.sidebar.write(f"**{_('Years:')}** {years_range}")
    st.sidebar.write(f"**{_('States:')}** {', '.join(states)}")
    
    # Botón para generar análisis
    if st.sidebar.button(_("Generate Analysis"), type="primary"):
        # Realizar análisis
        months, calls, peaks, valleys, total_calls, monthly_calls = analyze_inflection_points_streamlit(calls_df, company_id)
        
        if months is not None:
            # Crear gráfico
            fig = create_inflection_chart(months, calls, peaks, valleys, company_id)
            
            # Mostrar gráfico
            st.pyplot(fig)
            
            # Mostrar estadísticas
            st.markdown("---")
            st.markdown(f"### {_('Analysis Statistics')}")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(_("Peaks Identified"), len(peaks))
            
            with col2:
                st.metric(_("Valleys Identified"), len(valleys))
            
            with col3:
                st.metric(_("Monthly Average"), f"{np.mean(calls):.1f}%")
            
            with col4:
                st.metric(_("Maximum Variation"), f"{np.max(calls) - np.min(calls):.1f}%")
            
            # Detalles de picos y valles
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"#### 🔺 {_('Identified Peaks')}")
                if len(peaks) > 0:
                    month_names = [_("January"), _("February"), _("March"), _("April"), _("May"), _("June"), 
                                 _("July"), _("August"), _("September"), _("October"), _("November"), _("December")]
                    for i, peak in enumerate(peaks, 1):
                        month_name = month_names[months[peak]-1]
                        st.write(f"**{i}.** {_('Month')} {months[peak]} ({month_name}): {calls[peak]:.1f}% {_('of total')}")
                else:
                    st.write(_("No peaks identified"))
            
            with col2:
                st.markdown(f"#### 🔻 {_('Identified Valleys')}")
                if len(valleys) > 0:
                    month_names = [_("January"), _("February"), _("March"), _("April"), _("May"), _("June"), 
                                 _("July"), _("August"), _("September"), _("October"), _("November"), _("December")]
                    for i, valley in enumerate(valleys, 1):
                        month_name = month_names[months[valley]-1]
                        st.write(f"**{i}.** {_('Month')} {months[valley]} ({month_name}): {calls[valley]:.1f}% {_('of total')}")
                else:
                    st.write(_("No valleys identified"))
            
            # Tabla de datos mensuales
            st.markdown("---")
            st.markdown(f"### 📋 {_('Detailed Monthly Data')}")
            
            monthly_data = pd.DataFrame({
                _('Month'): [_("January"), _("February"), _("March"), _("April"), _("May"), _("June"),
                            _("July"), _("August"), _("September"), _("October"), _("November"), _("December")],
                _('Calls'): monthly_calls.astype(int),
                _('Percentage (%)'): calls.round(2),
                _('Is Peak'): ['✅' if i in peaks else '' for i in range(12)],
                _('Is Valley'): ['✅' if i in valleys else '' for i in range(12)]
            })
            
            st.dataframe(monthly_data, use_container_width=True)
            
        else:
            st.error(f"❌ {_('No data found for company')} {company_id}")
    
    # Información adicional
    st.markdown("---")
    st.markdown(f"### ℹ️ {_('Analysis Information')}")
    st.info(f"""
    **📊 {_('Methodology:')}**
    - {_('Data is grouped by month summing all calls from all years')}
    - {_('Monthly percentages of the total annual are calculated')}
    - {_('Peaks and valleys are identified using SciPy find_peaks function')}
    - {_('Parameters: minimum height = monthly average, minimum distance = 2 months')}
    
    **🎯 {_('Interpretation:')}**
    - **{_('Peaks (🔺): Months with higher call concentration')}**
    - **{_('Valleys (🔻): Months with lower call concentration')}**
    - **{_('Percentages: Represent the proportion of calls for each month relative to the annual total')}**
    """)

if __name__ == "__main__":
    main()
