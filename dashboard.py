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

def get_translation_function():
    """Obtener función de traducción según idioma"""
    
    # Detectar idioma del navegador o parámetro URL
    lang = st.query_params.get("lang", None)
    
    # Si no hay parámetro URL, detectar idioma del sistema
    if lang is None:
        try:
            system_lang = locale.getdefaultlocale()[0][:2]
            if system_lang in ["es", "en"]:
                lang = system_lang
            else:
                lang = "en"  # Fallback a inglés
        except:
            lang = "en"  # Fallback a inglés
    
    # Configurar GETTEXT
    try:
        translation = gettext.translation(
            'messages', 
            'locales', 
            languages=[lang],
            fallback=True
        )
        return translation.gettext
    except Exception as e:
        st.warning(f"Translation error: {e}. Using English.")
        return lambda x: x

# Función de traducción (se llama en cada uso)
def _(text):
    return get_translation_function()(text)

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
           SELECT c.company_id AS `company_id`
                , c.company_name AS `company_name`
                , COUNT(DISTINCT(cl.campaign_id)) AS `campaigns`
                , COUNT(cl.lead_call_customer_id) AS `customers`
                , cl.location_state AS `state`
                , EXTRACT(YEAR FROM DATE(cl.lead_call_created_on)) AS `year`
                , EXTRACT(MONTH FROM DATE(cl.lead_call_created_on)) AS `month`
                , COUNT(cl.lead_call_id) AS `calls`
             FROM `pph-central.silver.vw_consolidated_call_inbound_location` cl
             JOIN `pph-central.settings.companies` c ON cl.company_id = c.company_id
            WHERE DATE(cl.lead_call_created_on) < DATE("2025-09-01")
              AND EXTRACT(YEAR FROM DATE(cl.lead_call_created_on)) >= 2015
            GROUP BY c.company_id, c.company_name, cl.location_state, EXTRACT(YEAR FROM DATE(cl.lead_call_created_on)), EXTRACT(MONTH FROM DATE(cl.lead_call_created_on))
            ORDER BY c.company_id, cl.location_state, EXTRACT(YEAR FROM DATE(cl.lead_call_created_on)), EXTRACT(MONTH FROM DATE(cl.lead_call_created_on))
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

def analyze_inflection_points_streamlit(calls_df, company_id, method="Original (find_peaks)"):
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
    
    # Aplicar método de detección seleccionado
    if method == "Original (find_peaks)":
        # Método original - más sensible
        peaks, _ = find_peaks(calls, height=np.mean(calls), distance=2)
        valleys, _ = find_peaks(-calls, height=-np.mean(calls), distance=2)
        
    elif method == "Mathematical Strict":
        # Método matemático estricto - quartiles
        peaks, valleys = detect_peaks_valleys_quartiles(calls)
        
    elif method == "Hybrid (3-4 months)":
        # Método híbrido - distancia mínima de 3-4 meses
        peaks, _ = find_peaks(calls, height=np.mean(calls), distance=3)
        valleys, _ = find_peaks(-calls, height=-np.mean(calls), distance=3)
    
    return months, calls, peaks, valleys, total_calls, monthly_calls

def detect_peaks_valleys_quartiles(calls):
    """
    Detecta picos y valles usando el método matemático estricto (quartiles)
    Siempre retorna exactamente 2 picos y 2 valles
    """
    # Calcular quartiles
    q1 = np.percentile(calls, 25)
    q2 = np.percentile(calls, 50)  # mediana
    q3 = np.percentile(calls, 75)
    
    # Encontrar los 2 valores más altos (picos) y los 2 más bajos (valles)
    sorted_indices = np.argsort(calls)
    
    # 2 valles (valores más bajos)
    valleys = sorted_indices[:2]
    
    # 2 picos (valores más altos)
    peaks = sorted_indices[-2:]
    
    return peaks, valleys

def calculate_annual_data(calls_df, company_id, mode="percentages"):
    """
    Calcula datos mensuales por año para una compañía específica.
    Modo: "percentages" o "absolute"
    Retorna una tabla con años en filas y meses en columnas.
    """
    # Filtrar datos de la compañía
    company_data = calls_df[calls_df['company_id'] == company_id].copy()
    
    if company_data.empty:
        return None
    
    # Agrupar por año y mes, sumar llamadas
    yearly_monthly = company_data.groupby(['year', 'month'])['calls'].sum().reset_index()
    
    # Crear tabla anual
    years = sorted(yearly_monthly['year'].unique())
    months = range(1, 13)
    
    # Crear DataFrame para la tabla
    annual_table = pd.DataFrame(index=years, columns=months)
    annual_table.columns.name = 'Month'
    annual_table.index.name = 'Year'
    
    # Calcular datos para cada año
    for year in years:
        year_data = yearly_monthly[yearly_monthly['year'] == year]
        year_total = year_data['calls'].sum()
        
        for month in months:
            month_data = year_data[year_data['month'] == month]
            if not month_data.empty:
                month_calls = month_data['calls'].iloc[0]
                if mode == "percentages":
                    value = (month_calls / year_total) * 100
                else:  # absolute
                    value = month_calls
                annual_table.loc[year, month] = value
            else:
                annual_table.loc[year, month] = 0.0
    
    return annual_table

def create_annual_table(annual_table, historical_data=None, mode="percentages"):
    """
    Crea una tabla formateada para mostrar datos anuales.
    Modo: "percentages" o "absolute"
    Incluye una fila histórica para validación.
    """
    if annual_table is None:
        return None
    
    # Crear tabla con nombres de meses
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Crear DataFrame formateado
    formatted_table = annual_table.copy()
    formatted_table.columns = month_names
    
    # Formatear valores según el modo
    if mode == "percentages":
        formatted_table = formatted_table.round(2)
    else:  # absolute
        # Para números absolutos, redondear a enteros
        formatted_table = formatted_table.round(0).astype(int)
    
    # Agregar fila histórica si se proporciona
    if historical_data is not None:
        # Crear fila histórica
        historical_row = pd.Series(historical_data, index=month_names)
        historical_row.name = 'Historical Total'
        
        # Agregar al DataFrame
        formatted_table = pd.concat([formatted_table, historical_row.to_frame().T])
    
    return formatted_table

def create_scatter_with_midpoints(annual_table, midpoint_lines, company_id, company_name):
    """
    Crea un gráfico de dispersión con líneas de punto medio superpuestas.
    Muestra todos los datos anuales con las marcas históricas.
    """
    if annual_table is None or annual_table.empty:
        return None
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Preparar datos para dispersión
    scatter_data = []
    colors = []
    labels = []
    
    # Recopilar todos los puntos de datos anuales
    for year in annual_table.index:
        for month in annual_table.columns:
            value = annual_table.loc[year, month]
            if value > 0:  # Solo datos no cero
                scatter_data.append([month, value])
                colors.append(f'C{year % 10}')  # Color diferente por año
                labels.append(f'{year}')
    
    # Convertir a arrays
    scatter_data = np.array(scatter_data)
    if len(scatter_data) == 0:
        return None
    
    months_scatter = scatter_data[:, 0]
    values_scatter = scatter_data[:, 1]
    
    # Crear gráfico de dispersión
    scatter = ax.scatter(months_scatter, values_scatter, c=colors, alpha=0.6, s=60, edgecolors='black', linewidth=0.5)
    
    # Dibujar líneas de punto medio del gráfico histórico
    if midpoint_lines:
        for line in midpoint_lines:
            if line['is_circular']:
                # Líneas circulares: dibujar en enero y diciembre
                ax.axvline(x=1, color=line['color'], linestyle='--', alpha=0.8, linewidth=3)
                ax.axvline(x=12, color=line['color'], linestyle='--', alpha=0.8, linewidth=3)
            else:
                # Líneas normales
                ax.axvline(x=line['month'], color=line['color'], linestyle='--', alpha=0.8, linewidth=2)
    
    # Configurar gráfico
    ax.set_title(f'Annual Data vs Historical Midpoints - {company_name}\nScatter Plot with Historical Transition Lines', 
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('Month', fontsize=12)
    ax.set_ylabel('Percentage of Total Calls (%)', fontsize=12)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    
    # Crear leyenda personalizada
    legend_elements = []
    
    # Agregar elementos de líneas históricas
    if midpoint_lines:
        green_lines = [line for line in midpoint_lines if line['color'] == 'green']
        red_lines = [line for line in midpoint_lines if line['color'] == 'red']
        circular_lines = [line for line in midpoint_lines if line['is_circular']]
        
        if green_lines:
            legend_elements.append(plt.Line2D([0], [0], color='green', linestyle='--', linewidth=2, 
                                            label=f'Valley-to-Peak Transitions ({len(green_lines)})'))
        if red_lines:
            legend_elements.append(plt.Line2D([0], [0], color='red', linestyle='--', linewidth=2, 
                                            label=f'Peak-to-Valley Transitions ({len(red_lines)})'))
        if circular_lines:
            legend_elements.append(plt.Line2D([0], [0], color=circular_lines[0]['color'], linestyle='--', linewidth=3, 
                                            label=f'Year-End Transitions ({len(circular_lines)})'))
    
    # Agregar elementos de años únicos
    unique_years = sorted(set(labels))
    for i, year in enumerate(unique_years[:5]):  # Máximo 5 años en leyenda
        legend_elements.append(plt.Line2D([0], [0], marker='o', color=f'C{i}', linestyle='None', markersize=8, 
                                        label=f'Year {year}'))
    
    if len(unique_years) > 5:
        legend_elements.append(plt.Line2D([0], [0], marker='o', color='gray', linestyle='None', markersize=8, 
                                        label=f'Other years ({len(unique_years)-5} more)'))
    
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def calculate_midpoint_lines(months, calls, peaks, valleys):
    """Calcular líneas de punto medio entre picos y valles consecutivos"""
    midpoint_lines = []
    
    # Combinar todos los puntos (picos y valles) y ordenarlos por mes
    all_points = []
    for peak in peaks:
        all_points.append((months[peak], calls[peak], 'peak'))
    for valley in valleys:
        all_points.append((months[valley], calls[valley], 'valley'))
    
    # Ordenar por mes
    all_points.sort(key=lambda x: x[0])
    
    # Calcular puntos medios entre puntos consecutivos
    for i in range(len(all_points) - 1):
        current_month, current_value, current_type = all_points[i]
        next_month, next_value, next_type = all_points[i + 1]
        
        # Calcular punto medio
        midpoint_month = (current_month + next_month) / 2
        midpoint_value = (current_value + next_value) / 2
        
        # Determinar color: Verde si viene después de un valle, Rojo si viene después de un pico
        color = 'green' if current_type == 'valley' else 'red'
        
        midpoint_lines.append({
            'month': midpoint_month,
            'value': midpoint_value,
            'color': color,
            'from_type': current_type,
            'to_type': next_type,
            'is_circular': False
        })
    
    # Verificar secuencias que cruzan diciembre-enero (análisis circular)
    if len(all_points) > 1:
        first_point = all_points[0]
        last_point = all_points[-1]
        
        # Si el primer punto está en enero (1) y el último en diciembre (12)
        if first_point[0] == 1 and last_point[0] == 12:
            # Calcular punto medio circular (diciembre -> enero)
            # El punto medio está en 0.5 (entre diciembre y enero)
            circular_midpoint = 0.5
            circular_value = (first_point[1] + last_point[1]) / 2
            
            # Determinar color basado en el último punto (diciembre)
            circular_color = 'green' if last_point[2] == 'valley' else 'red'
            
            midpoint_lines.append({
                'month': circular_midpoint,
                'value': circular_value,
                'color': circular_color,
                'from_type': last_point[2],  # diciembre
                'to_type': first_point[2],   # enero
                'is_circular': True
            })
    
    return midpoint_lines

def create_inflection_chart(months, calls, peaks, valleys, company_id, company_name, ylabel_text="Percentage of Total Calls (%)", title_suffix="Peaks and Valleys Analysis", analysis_mode="Percentages"):
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
    
    # Calcular líneas de punto medio
    midpoint_lines = calculate_midpoint_lines(months, calls, peaks, valleys)
    
    # Dibujar líneas de punto medio
    if midpoint_lines:
        green_lines = [line for line in midpoint_lines if line['color'] == 'green' and not line['is_circular']]
        red_lines = [line for line in midpoint_lines if line['color'] == 'red' and not line['is_circular']]
        circular_lines = [line for line in midpoint_lines if line['is_circular']]
        
        # Líneas verdes (después de valles)
        if green_lines:
            for line in green_lines:
                ax.axvline(x=line['month'], color='green', linestyle='--', alpha=0.6, linewidth=2)
        
        # Líneas rojas (después de picos)
        if red_lines:
            for line in red_lines:
                ax.axvline(x=line['month'], color='red', linestyle='--', alpha=0.6, linewidth=2)
        
        # Líneas circulares (diciembre-enero)
        if circular_lines:
            for line in circular_lines:
                # Dibujar línea en enero (1) para transición diciembre->enero
                ax.axvline(x=1, color=line['color'], linestyle='--', alpha=0.8, linewidth=3)
                # Dibujar línea en diciembre (12) para transición diciembre->enero
                ax.axvline(x=12, color=line['color'], linestyle='--', alpha=0.8, linewidth=3)
        
        # Agregar a la leyenda solo si hay líneas
        if green_lines:
            ax.axvline(x=green_lines[0]['month'], color='green', linestyle='--', alpha=0.6, 
                      linewidth=2, label=f'Valley-to-Peak Midpoints ({len(green_lines)})')
        if red_lines:
            ax.axvline(x=red_lines[0]['month'], color='red', linestyle='--', alpha=0.6, 
                      linewidth=2, label=f'Peak-to-Valley Midpoints ({len(red_lines)})')
        if circular_lines:
            ax.axvline(x=1, color=circular_lines[0]['color'], linestyle='--', alpha=0.8, 
                      linewidth=3, label=f'Year-End Transition ({len(circular_lines)})')
    
    # Marcar picos (Verde - consistente con box plot)
    if len(peaks) > 0:
        ax.plot(months[peaks], calls[peaks], '^', color='green', markersize=12, 
                label=f'Peaks ({len(peaks)})', markeredgecolor='darkgreen', markeredgewidth=2)
        
        # Anotar picos (DEBAJO de la curva)
        for peak in peaks:
            if analysis_mode == "Absolute Numbers":
                annotation_text = f'Peak\nMonth {months[peak]}\n{int(calls[peak])} calls'
            else:
                annotation_text = f'Peak\nMonth {months[peak]}\n{calls[peak]:.2f}%'
            
            ax.annotate(annotation_text, 
                        xy=(months[peak], calls[peak]), 
                        xytext=(months[peak], calls[peak] - np.max(calls)*0.1),
                        ha='center', va='top',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="green", alpha=0.7),
                        arrowprops=dict(arrowstyle='->', color='green'))
    
    # Marcar valles (Rojo - consistente con box plot)
    if len(valleys) > 0:
        ax.plot(months[valleys], calls[valleys], 'v', color='red', markersize=12,
                label=f'Valleys ({len(valleys)})', markeredgecolor='darkred', markeredgewidth=2)
        
        # Anotar valles (ENCIMA de la curva)
        for valley in valleys:
            if analysis_mode == "Absolute Numbers":
                annotation_text = f'Valley\nMonth {months[valley]}\n{int(calls[valley])} calls'
            else:
                annotation_text = f'Valley\nMonth {months[valley]}\n{calls[valley]:.2f}%'
            
            ax.annotate(annotation_text, 
                        xy=(months[valley], calls[valley]), 
                        xytext=(months[valley], calls[valley] + np.max(calls)*0.1),
                        ha='center', va='bottom',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="red", alpha=0.7),
                        arrowprops=dict(arrowstyle='->', color='red'))
    
    # Configurar gráfico
    ax.set_title(f'Inflection Points - {company_name} (ID: {company_id})\n{title_suffix} in Calls', 
                 fontsize=14, fontweight='bold')
    ax.set_xlabel('Month', fontsize=12)
    ax.set_ylabel(ylabel_text, fontsize=12)
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
    
    # Obtener lista de compañías disponibles con nombres
    companies_info = calls_df[['company_id', 'company_name']].drop_duplicates().sort_values('company_id')
    companies_dict = dict(zip(companies_info['company_id'], companies_info['company_name']))
    
    # Selector de compañía
    selected_company_name = st.sidebar.selectbox(
        _("Select Company:"),
        options=list(companies_dict.values()),
        index=0,
        help=_("Select the company to analyze its inflection points")
    )
    
    # Obtener el ID de la compañía seleccionada
    company_id = [k for k, v in companies_dict.items() if v == selected_company_name][0]
    
    # Selector de modo de análisis
    analysis_mode = st.sidebar.selectbox(
        _("Analysis Mode:"),
        options=["Percentages", "Absolute Numbers"],
        index=0,
        help=_("Choose between percentage analysis or absolute call numbers")
    )
    
    # Selector de método de detección (OCULTADO TEMPORALMENTE)
    # detection_method = st.sidebar.selectbox(
    #     _("Peak/Valley Detection Method:"),
    #     options=["Original (find_peaks)", "Mathematical Strict", "Hybrid (3-4 months)"],
    #     index=2,  # Híbrido como predeterminado
    #     help=_("Choose the method for detecting peaks and valleys")
    # )
    
    # Método híbrido como predeterminado
    detection_method = "Hybrid (3-4 months)"
    
    # Información de la compañía seleccionada
    company_data = calls_df[calls_df['company_id'] == company_id]
    total_calls_company = company_data['calls'].sum()
    years_range = f"{company_data['year'].min()} - {company_data['year'].max()}"
    states = company_data['state'].unique()
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### {_('Company Information')}")
    st.sidebar.write(f"**{_('Name:')}** {selected_company_name}")
    st.sidebar.write(f"**{_('ID:')}** {company_id}")
    st.sidebar.write(f"**{_('Total Calls:')}** {total_calls_company:,}")
    st.sidebar.write(f"**{_('Years:')}** {years_range}")
    st.sidebar.write(f"**{_('States:')}** {', '.join(states)}")
    
    # Botón para generar análisis
    if st.sidebar.button(_("Generate Analysis"), type="primary"):
        # Realizar análisis
        months, calls, peaks, valleys, total_calls, monthly_calls = analyze_inflection_points_streamlit(calls_df, company_id, detection_method)
        
        if months is not None:
            # Ajustar datos según el modo seleccionado
            if analysis_mode == "Absolute Numbers":
                # Convertir porcentajes a números absolutos para el gráfico
                calls_absolute = (calls / 100) * total_calls
                ylabel_text = 'Number of Calls'
                title_suffix = 'Calls Analysis'
            else:
                calls_absolute = calls
                ylabel_text = 'Percentage of Total Calls (%)'
                title_suffix = 'Percentage Analysis'
            
            # Crear gráfico
            fig = create_inflection_chart(months, calls_absolute, peaks, valleys, company_id, selected_company_name, ylabel_text, title_suffix, analysis_mode)
            
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
            if analysis_mode == "Percentages":
            st.markdown(f"### 📋 {_('Detailed Monthly Data')}")
                monthly_data = pd.DataFrame({
                    _('Month'): [_("January"), _("February"), _("March"), _("April"), _("May"), _("June"),
                                _("July"), _("August"), _("September"), _("October"), _("November"), _("December")],
                    _('Calls'): monthly_calls.astype(int),
                    _('Percentage (%)'): calls.round(2),
                    _('Is Peak'): ['✅' if i in peaks else '' for i in range(12)],
                    _('Is Valley'): ['✅' if i in valleys else '' for i in range(12)]
                })
            else:
                st.markdown(f"### 📋 {_('Detailed Monthly Data - Absolute Numbers')}")
            monthly_data = pd.DataFrame({
                _('Month'): [_("January"), _("February"), _("March"), _("April"), _("May"), _("June"),
                            _("July"), _("August"), _("September"), _("October"), _("November"), _("December")],
                _('Calls'): monthly_calls.astype(int),
                _('Percentage (%)'): calls.round(2),
                _('Is Peak'): ['✅' if i in peaks else '' for i in range(12)],
                _('Is Valley'): ['✅' if i in valleys else '' for i in range(12)]
            })
            
            st.dataframe(monthly_data, use_container_width=True)
            
            # Tabla de datos anuales
            st.markdown("---")
            if analysis_mode == "Percentages":
                st.markdown(f"### 📊 {_('Annual Percentage Breakdown')}")
                st.markdown(f"*{_('Each month shows the percentage of total calls for that specific year')}*")
            else:
                st.markdown(f"### 📊 {_('Annual Absolute Numbers Breakdown')}")
                st.markdown(f"*{_('Each month shows the absolute number of calls for that specific year')}*")
            
            # Explicación de colores
            st.markdown(f"**🎨 {_('Color Legend:')}**")
            st.markdown("- **🟢 Verde**: Month with highest calls in that year")
            st.markdown("- **🟡 Rosa**: Month with lowest calls in that year (excluding zeros)")
            st.markdown("- **⚪ Gris**: Months with no data (0 calls)")
            st.markdown("- **🟣 Lavanda**: Historical validation row")
            
            if analysis_mode == "Percentages":
                note_text = _("The 'Historical Total' row shows percentages from the main chart for validation")
            else:
                note_text = _("The 'Historical Total' row shows absolute numbers from the main chart for validation")
            st.markdown(f"**💡 {_('Note:')}** {note_text}")
            
            # Calcular tabla de datos anuales
            mode_key = "percentages" if analysis_mode == "Percentages" else "absolute"
            annual_table = calculate_annual_data(calls_df, company_id, mode_key)
            
            # Preparar datos históricos según el modo
            if analysis_mode == "Percentages":
                historical_data = calls  # Porcentajes históricos
            else:
                # Calcular números absolutos históricos
                historical_data = (calls / 100) * total_calls  # Convertir % a números absolutos
            
            formatted_annual_table = create_annual_table(annual_table, historical_data, mode_key)
            
            if formatted_annual_table is not None:
                # Aplicar estilo a la tabla
                def highlight_max_min(row):
                    """Resaltar valores máximos y mínimos en cada fila (excluyendo ceros)"""
                    styles = []
                    # Filtrar valores no nulos y mayores a 0
                    non_zero_values = row[row > 0]
                    
                    for i, val in enumerate(row):
                        if val == 0:
                            styles.append('background-color: #D3D3D3')  # Gris para ceros
                        elif len(non_zero_values) > 0 and val == non_zero_values.max():
                            styles.append('background-color: #90EE90')  # Verde claro para máximo (no cero)
                        elif len(non_zero_values) > 0 and val == non_zero_values.min():
                            styles.append('background-color: #FFB6C1')  # Rosa claro para mínimo (no cero)
                        else:
                            styles.append('')
                    return styles
                
                def highlight_historical_row(row):
                    """Resaltar la fila histórica con color diferente"""
                    if row.name == 'Historical Total':
                        return ['background-color: #E6E6FA' for _ in row]  # Lavanda para fila histórica
                    return ['' for _ in row]
                
                # Aplicar estilos y mostrar tabla
                styled_table = (formatted_annual_table
                              .style
                              .apply(highlight_max_min, axis=1)
                              .apply(highlight_historical_row, axis=1)
                              .set_table_styles([
                                  {'selector': 'th', 'props': [('text-align', 'center')]},
                                  {'selector': 'td', 'props': [('text-align', 'center')]}
                              ]))
                st.dataframe(styled_table, use_container_width=True)
                
                # Estadísticas adicionales
                st.markdown(f"#### 📈 {_('Annual Statistics')}")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(_("Years Analyzed"), len(formatted_annual_table))
                
                with col2:
                    # Calcular variación por año y luego promediar
                    annual_variations = []
                    for year in formatted_annual_table.index:
                        year_data = formatted_annual_table.loc[year]
                        non_zero_data = year_data[year_data > 0]  # Excluir ceros
                        if len(non_zero_data) > 0:
                            year_variation = non_zero_data.max() - non_zero_data.min()
                            annual_variations.append(year_variation)
                    
                    avg_annual_variation = np.mean(annual_variations) if annual_variations else 0
                    
                    if analysis_mode == "Percentages":
                        st.metric(_("Avg Annual Variation"), f"{avg_annual_variation:.2f}%")
                    else:
                        st.metric(_("Avg Annual Variation"), f"{int(avg_annual_variation)} calls")
                
                with col3:
                    most_active_month = formatted_annual_table.mean().idxmax()
                    st.metric(_("Most Active Month"), most_active_month)
                
                # Gráfico de dispersión con líneas de punto medio (COMENTADO TEMPORALMENTE)
                # st.markdown("---")
                # st.markdown(f"### 🎯 {_('Annual Data vs Historical Transitions')}")
                # st.markdown(f"*{_('Scatter plot showing yearly data points with historical transition lines from main chart')}*")
                
                # # Calcular líneas de punto medio para el gráfico de dispersión
                # scatter_midpoint_lines = calculate_midpoint_lines(months, calls, peaks, valleys)
                
                # # Crear gráfico de dispersión
                # scatter_fig = create_scatter_with_midpoints(annual_table, scatter_midpoint_lines, company_id, selected_company_name)
                # if scatter_fig is not None:
                #     st.pyplot(scatter_fig)
                    
                #     # Análisis de patrones
                #     st.markdown("#### 🔍 {_('Pattern Analysis')}")
                #     if scatter_midpoint_lines:
                #         st.markdown("**{_('Historical Transition Lines:')}**")
                #         for line in scatter_midpoint_lines:
                #             if line['is_circular']:
                #                 st.write(f"• **Year-End Transition**: December → January ({line['color'].title()})")
                #             else:
                #                 month_name = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                #                             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][int(line['month'])-1]
                #                 transition_type = "Valley→Peak" if line['color'] == 'green' else "Peak→Valley"
                #                 st.write(f"• **Month {int(line['month'])} ({month_name})**: {transition_type} transition ({line['color'].title()})")
                # else:
                #     st.warning(_("No scatter plot data available"))
            else:
                st.warning(_("No annual data available for this company"))
            
        else:
            st.error(f"❌ {_('No data found for company')} {company_id}")
    
    # Información adicional
    st.markdown("---")
    st.markdown(f"### ℹ️ {_('Analysis Information')}")
    st.info(f"""
    **📊 {_('Methodology:')}**
    - {_('Data is grouped by month summing all calls from all years')}
    - {_('Monthly percentages of the total annual are calculated')}
    - {_('Peaks and valleys are identified using the selected detection method')}
    
    **🔍 {_('Detection Method:')}**
    - **{_('Hybrid (3-4 months): Uses SciPy with height=mean, distance=3 months for optimal seasonal patterns')}**
    - **{_('This method provides better separation between seasonal peaks and valleys')}**
    
    **🎯 {_('Interpretation:')}**
    - **{_('Peaks (🔺): Months with higher call concentration')}**
    - **{_('Valleys (🔻): Months with lower call concentration')}**
    - **{_('Percentages: Represent the proportion of calls for each month relative to the annual total')}**
    """)

if __name__ == "__main__":
    main()
