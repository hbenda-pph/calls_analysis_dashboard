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
import sys
import warnings
warnings.filterwarnings('ignore')

# Importar estilos compartidos
try:
    # Intentar desde directorio padre (desarrollo local)
    sys.path.append(os.path.join(os.path.dirname(__file__), '../analysis_predictive_shared'))
    from streamlit_config import apply_standard_styles
except ImportError:
    try:
        # Intentar desde directorio actual (producción/Docker)
        sys.path.append(os.path.join(os.path.dirname(__file__), 'analysis_predictive_shared'))
        from streamlit_config import apply_standard_styles
    except ImportError:
        # Si no se encuentra, definir función vacía
        def apply_standard_styles():
            pass

# Configuración de la página
st.set_page_config(
    page_title="ServiceTitan - Inflection Points Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aplicar estilos compartidos INMEDIATAMENTE después de set_page_config
apply_standard_styles()

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
             FROM `pph-central.analytical.vw_consolidated_call_inbound_location` cl
             JOIN `pph-central.settings.companies` c ON cl.company_id = c.company_id
            WHERE DATE(cl.lead_call_created_on) < DATE("2025-10-01")
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
    # Método original - más sensible
    if method == "Original (find_peaks)":
        peaks, _ = find_peaks(calls, height=np.mean(calls), distance=2)
        valleys, _ = find_peaks(-calls, height=-np.mean(calls), distance=2)

    # Método matemático estricto - quartiles        
    elif method == "Mathematical Strict":
        peaks, valleys = detect_peaks_valleys_quartiles(calls)

    # Método híbrido - distancia mínima de 3-4 meses
    elif method == "Hybrid (3-4 months)":
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

def classify_graph_pattern(peaks, valleys, months):
    """
    Clasifica el patrón del gráfico en diferentes categorías
    Retorna: pattern_type, issues, recommendations
    """
    all_points = []
    
    # Combinar todos los puntos con su tipo y mes
    for peak in peaks:
        all_points.append({'month': months[peak], 'type': 'peak', 'index': peak})
    for valley in valleys:
        all_points.append({'month': months[valley], 'type': 'valley', 'index': valley})
    
    # Ordenar por mes
    all_points.sort(key=lambda x: x['month'])
    
    # Análisis de patrones
    issues = []
    recommendations = []
    
    # 1. Verificar alternancia (Normal vs Anormal)
    is_alternating = True
    for i in range(len(all_points) - 1):
        if all_points[i]['type'] == all_points[i+1]['type']:
            is_alternating = False
            issues.append(f"Consecutive {all_points[i]['type']}s in months {all_points[i]['month']} and {all_points[i+1]['month']}")
    
    # 2. Verificar distancia mínima entre puntos
    min_distance = 2  # meses
    too_close = []
    for i in range(len(all_points) - 1):
        distance = all_points[i+1]['month'] - all_points[i]['month']
        if distance < min_distance:
            too_close.append(f"{all_points[i]['type']} (month {all_points[i]['month']}) and {all_points[i+1]['type']} (month {all_points[i+1]['month']}) are too close ({distance} month{'s' if distance != 1 else ''})")
    
    # 3. Verificar puntos en extremos (diciembre-enero)
    circular_issues = []
    for point in all_points:
        if point['month'] == 12:
            # Buscar si hay otro punto en enero
            january_point = next((p for p in all_points if p['month'] == 1), None)
            if january_point:
                circular_issues.append(f"Year-end transition: {point['type']} in December and {january_point['type']} in January")
    
    # 4. Determinar tipo de patrón
    if is_alternating and len(too_close) == 0 and len(all_points) == 4:
        pattern_type = "Normal"
        recommendations.append("Optimal pattern: Well-separated alternating peaks and valleys")
    elif len(too_close) > 0:
        pattern_type = "Clustered Points"
        recommendations.append("Consider merging nearby points or using different detection parameters")
    elif not is_alternating:
        pattern_type = "Non-Alternating"
        recommendations.append("Consider adjusting detection method or using mathematical strict approach")
    elif len(all_points) < 4:
        pattern_type = "Insufficient Points"
        recommendations.append("Increase sensitivity or check data quality")
    elif len(all_points) > 4:
        pattern_type = "Too Many Points"
        recommendations.append("Reduce sensitivity or use mathematical strict method")
    else:
        pattern_type = "Complex"
        recommendations.append("Pattern requires manual review")
    
    # 5. Generar recomendaciones específicas
    if len(too_close) > 0:
        recommendations.append("Consider using 'Mathematical Strict' method for better separation")
    if not is_alternating:
        recommendations.append("Try 'Hybrid (3-4 months)' method for better seasonal patterns")
    
    return {
        'pattern_type': pattern_type,
        'is_alternating': is_alternating,
        'total_points': len(all_points),
        'issues': issues + too_close + circular_issues,
        'recommendations': recommendations,
        'all_points': all_points
    }

def optimize_midpoint_marks(pattern_analysis, months, calls, peaks, valleys):
    """
    Optimiza las marcas de punto medio basado en el análisis del patrón
    """
    all_points = pattern_analysis['all_points']
    
    if pattern_analysis['pattern_type'] == "Normal":
        # Para patrones normales, usar el método estándar
        return calculate_midpoint_lines(months, calls, peaks, valleys)
    
    elif pattern_analysis['pattern_type'] == "Clustered Points":
        # Para puntos agrupados, intentar separarlos
        optimized_lines = []
        
        # Agrupar puntos cercanos
        clusters = []
        current_cluster = [all_points[0]]
        
        for i in range(1, len(all_points)):
            distance = all_points[i]['month'] - all_points[i-1]['month']
            if distance <= 2:  # Puntos muy cercanos
                current_cluster.append(all_points[i])
            else:
                clusters.append(current_cluster)
                current_cluster = [all_points[i]]
        clusters.append(current_cluster)
        
        # Para cada cluster, crear una marca representativa
        for cluster in clusters:
            if len(cluster) > 1:
                # Calcular punto medio del cluster
                avg_month = np.mean([p['month'] for p in cluster])
                avg_value = np.mean([calls[p['index']] for p in cluster])
                
                # Determinar tipo dominante en el cluster
                peak_count = sum(1 for p in cluster if p['type'] == 'peak')
                valley_count = sum(1 for p in cluster if p['type'] == 'valley')
                
                cluster_type = 'peak' if peak_count > valley_count else 'valley'
                
                optimized_lines.append({
                    'month': avg_month,
                    'value': avg_value,
                    'type': f'cluster_{cluster_type}',
                    'original_points': len(cluster),
                    'is_optimized': True
                })
        
        return optimized_lines
    
    elif pattern_analysis['pattern_type'] in ["Non-Alternating", "Too Many Points"]:
        # Usar método matemático estricto
        strict_peaks, strict_valleys = detect_peaks_valleys_quartiles(calls)
        return calculate_midpoint_lines(months, calls, strict_peaks, strict_valleys)
    
    else:
        # Método estándar para otros casos
        return calculate_midpoint_lines(months, calls, peaks, valleys)

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
        # Crear fila histórica y formatear según el modo
        if mode == "percentages":
            historical_row = pd.Series(historical_data.round(2), index=month_names)
        else:  # absolute
            historical_row = pd.Series(historical_data.round(0).astype(int), index=month_names)
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
    """Calcular líneas de punto medio entre picos y valles con secuencia lógica"""
    midpoint_lines = []
    
    # Combinar todos los puntos con su posición y tipo
    all_points = []
    for peak in peaks:
        all_points.append({
            'month': months[peak], 
            'value': calls[peak], 
            'type': 'peak',
            'index': peak
        })
    for valley in valleys:
        all_points.append({
            'month': months[valley], 
            'value': calls[valley], 
            'type': 'valley',
            'index': valley
        })
    
    # Ordenar por mes
    all_points.sort(key=lambda x: x['month'])
    
    # Asignar posiciones lógicas (v1, p1, v2, p2, etc.)
    valley_count = 0
    peak_count = 0
    
    for point in all_points:
        if point['type'] == 'valley':
            valley_count += 1
            point['position'] = f'v{valley_count}'
        else:  # peak
            peak_count += 1
            point['position'] = f'p{peak_count}'
    
    # Calcular marcas solo entre secuencias válidas
    for i in range(len(all_points) - 1):
        current = all_points[i]
        next_point = all_points[i + 1]
        
        # Solo marcar entre valley→peak (verde) o peak→valley (rojo)
        if (current['type'] == 'valley' and next_point['type'] == 'peak') or \
           (current['type'] == 'peak' and next_point['type'] == 'valley'):
            
            # Calcular punto medio
            midpoint_month = (current['month'] + next_point['month']) / 2
            midpoint_value = (current['value'] + next_point['value']) / 2
            
            # Determinar color basado en la secuencia
            if current['type'] == 'valley' and next_point['type'] == 'peak':
                color = 'green'  # Subiendo: valley→peak
                transition_type = f"{current['position']}→{next_point['position']}"
            else:
                color = 'red'    # Bajando: peak→valley
                transition_type = f"{current['position']}→{next_point['position']}"
            
            midpoint_lines.append({
                'month': midpoint_month,
                'value': midpoint_value,
                'color': color,
                'from_position': current['position'],
                'to_position': next_point['position'],
                'transition_type': transition_type,
                'is_circular': False
            })
    
    # Verificar secuencia circular (diciembre→enero) solo si es válida
    if len(all_points) > 1:
        first_point = all_points[0]
        last_point = all_points[-1]
        
        # Solo si hay una secuencia válida (valley→peak o peak→valley)
        if (last_point['type'] == 'valley' and first_point['type'] == 'peak') or \
           (last_point['type'] == 'peak' and first_point['type'] == 'valley'):
            
            circular_midpoint = 0.5
            circular_value = (last_point['value'] + first_point['value']) / 2
            
            if last_point['type'] == 'valley' and first_point['type'] == 'peak':
                color = 'green'  # Subiendo: valley→peak
            else:
                color = 'red'    # Bajando: peak→valley
            
            midpoint_lines.append({
                'month': circular_midpoint,
                'value': circular_value,
                'color': color,
                'from_position': last_point['position'],
                'to_position': first_point['position'],
                'transition_type': f"{last_point['position']}→{first_point['position']}",
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
        
        # Líneas verdes (después de valles) - Estilo difuminado
        if green_lines:
            for line in green_lines:
                ax.axvline(x=line['month'], color='green', linestyle='--', alpha=0.4, linewidth=1.5)
        
        # Líneas rojas (después de picos) - Estilo difuminado
        if red_lines:
            for line in red_lines:
                ax.axvline(x=line['month'], color='red', linestyle='--', alpha=0.4, linewidth=1.5)
        
        # Líneas circulares (diciembre-enero) - Estilo difuminado
        if circular_lines:
            for line in circular_lines:
                # Dibujar línea en enero (1) para transición diciembre->enero
                ax.axvline(x=1, color=line['color'], linestyle='--', alpha=0.5, linewidth=2)
                # Dibujar línea en diciembre (12) para transición diciembre->enero
                ax.axvline(x=12, color=line['color'], linestyle='--', alpha=0.5, linewidth=2)
        
        # Agregar a la leyenda solo si hay líneas (simplificada)
        if green_lines:
            ax.axvline(x=green_lines[0]['month'], color='green', linestyle='--', alpha=0.4, 
                      linewidth=1.5, label=f'Growth Periods ({len(green_lines)})')
        if red_lines:
            ax.axvline(x=red_lines[0]['month'], color='red', linestyle='--', alpha=0.4, 
                      linewidth=1.5, label=f'Decline Periods ({len(red_lines)})')
        if circular_lines:
            ax.axvline(x=1, color=circular_lines[0]['color'], linestyle='--', alpha=0.5, 
                      linewidth=2, label=f'Year-End Transition ({len(circular_lines)})')
    
    # Marcar picos y valles CON anotaciones
    if len(peaks) > 0:
        ax.plot(months[peaks], calls[peaks], '^', color='green', markersize=8, 
                label=f'Peaks ({len(peaks)})', markeredgecolor='darkgreen', markeredgewidth=1)
        # Anotaciones para picos (debajo de la curva)
        for peak in peaks:
            # Determinar formato según el modo de análisis
            if analysis_mode == "Absolute Numbers":
                value_text = f'{calls[peak]:.0f}'  # Enteros para cantidades
            else:
                value_text = f'{calls[peak]:.2f}%'  # 2 decimales para porcentajes
            
            ax.annotate(value_text, xy=(months[peak], calls[peak]), 
                       xytext=(0, -15), textcoords='offset points',
                       ha='center', va='top', fontsize=10, fontweight='bold', color='darkgreen',
                       bbox=dict(boxstyle='round,pad=0.4', facecolor='lightgreen', alpha=0.8, edgecolor='darkgreen', linewidth=1.5))
    
    if len(valleys) > 0:
        ax.plot(months[valleys], calls[valleys], 'v', color='red', markersize=8,
                label=f'Valleys ({len(valleys)})', markeredgecolor='darkred', markeredgewidth=1)
        # Anotaciones para valles (encima de la curva)
        for valley in valleys:
            # Determinar formato según el modo de análisis
            if analysis_mode == "Absolute Numbers":
                value_text = f'{calls[valley]:.0f}'  # Enteros para cantidades
            else:
                value_text = f'{calls[valley]:.2f}%'  # 2 decimales para porcentajes
            
            ax.annotate(value_text, xy=(months[valley], calls[valley]), 
                       xytext=(0, 15), textcoords='offset points',
                       ha='center', va='bottom', fontsize=10, fontweight='bold', color='darkred',
                       bbox=dict(boxstyle='round,pad=0.4', facecolor='lightcoral', alpha=0.8, edgecolor='darkred', linewidth=1.5))
    
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
            
            # Análisis del patrón del gráfico
            pattern_analysis = classify_graph_pattern(peaks, valleys, months)
            
            # Mostrar diagnóstico del patrón
            st.markdown("---")
            st.markdown(f"### 🔍 {_('Graph Pattern Analysis')}")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Tipo de patrón con color
                if pattern_analysis['pattern_type'] == "Normal":
                    st.success(f"**Pattern Type:** {pattern_analysis['pattern_type']} ✅")
                elif pattern_analysis['pattern_type'] == "Clustered Points":
                    st.warning(f"**Pattern Type:** {pattern_analysis['pattern_type']} ⚠️")
                else:
                    st.error(f"**Pattern Type:** {pattern_analysis['pattern_type']} ❌")
            
            with col2:
                st.metric(_("Total Points"), pattern_analysis['total_points'])
            
            with col3:
                st.metric(_("Is Alternating"), "Yes" if pattern_analysis['is_alternating'] else "No")
            
            # Mostrar issues si los hay
            if pattern_analysis['issues']:
                st.markdown(f"#### ⚠️ {_('Issues Detected:')}")
                for issue in pattern_analysis['issues']:
                    st.warning(f"• {issue}")
            
            # Mostrar recomendaciones
            if pattern_analysis['recommendations']:
                st.markdown(f"#### 💡 {_('Recommendations:')}")
                for rec in pattern_analysis['recommendations']:
                    st.info(f"• {rec}")
            
            # Mostrar marcas optimizadas
            st.markdown(f"#### 🎯 {_('Optimized Midpoint Marks:')}")
            optimized_marks = optimize_midpoint_marks(pattern_analysis, months, calls_absolute, peaks, valleys)
            
            if optimized_marks:
                marks_info = []
                for mark in optimized_marks:
                    if 'is_optimized' in mark and mark['is_optimized']:
                        marks_info.append(f"• **Month {mark['month']:.1f}**: {mark['type']} (optimized from {mark['original_points']} nearby points)")
                    else:
                        color_desc = "Green (Valley→Peak)" if mark['color'] == 'green' else "Red (Peak→Valley)"
                        marks_info.append(f"• **Month {mark['month']:.1f}**: {color_desc}")
                
                if marks_info:
                    st.info("\n".join(marks_info))
            else:
                st.warning("No midpoint marks could be calculated for this pattern")
            
            # Mostrar estadísticas
            st.markdown("---")
            st.markdown(f"### {_('Analysis Statistics')}")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(_("Peaks Identified"), len(peaks))
            
            with col2:
                st.metric(_("Valleys Identified"), len(valleys))
            
            with col3:
                st.metric(_("Monthly Average"), f"{np.mean(calls):.2f}%")
            
            with col4:
                st.metric(_("Maximum Variation"), f"{np.max(calls) - np.min(calls):.2f}%")
            
            # Detalles de picos y valles
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"#### 🔺 {_('Identified Peaks')}")
                if len(peaks) > 0:
                    month_names = [_("January"), _("February"), _("March"), _("April"), _("May"), _("June"), 
                                 _("July"), _("August"), _("September"), _("October"), _("November"), _("December")]
                    for i, peak in enumerate(peaks, 1):
                        month_name = month_names[months[peak]-1]
                        if analysis_mode == "Absolute Numbers":
                            st.write(f"**{i}.** {_('Month')} {months[peak]} ({month_name}): {calls_absolute[peak]:.0f} {_('calls')}")
                        else:
                            st.write(f"**{i}.** {_('Month')} {months[peak]} ({month_name}): {calls[peak]:.2f}% {_('of total')}")
                else:
                    st.write(_("No peaks identified"))
            
            with col2:
                st.markdown(f"#### 🔻 {_('Identified Valleys')}")
                if len(valleys) > 0:
                    month_names = [_("January"), _("February"), _("March"), _("April"), _("May"), _("June"), 
                                 _("July"), _("August"), _("September"), _("October"), _("November"), _("December")]
                    for i, valley in enumerate(valleys, 1):
                        month_name = month_names[months[valley]-1]
                        if analysis_mode == "Absolute Numbers":
                            st.write(f"**{i}.** {_('Month')} {months[valley]} ({month_name}): {calls_absolute[valley]:.0f} {_('calls')}")
                        else:
                            st.write(f"**{i}.** {_('Month')} {months[valley]} ({month_name}): {calls[valley]:.2f}% {_('of total')}")
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
                    _('Calls Count'): monthly_calls.astype(int),
                    _('Is Peak'): ['✅' if i in peaks else '' for i in range(12)],
                    _('Is Valley'): ['✅' if i in valleys else '' for i in range(12)]
                })
            
            st.dataframe(monthly_data, use_container_width=True, height=490)
            
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
                if mode_key == "percentages":
                    styled_table = (formatted_annual_table
                                  .style
                                  .format("{:.2f}")  # 2 decimales para porcentajes
                                  .apply(highlight_max_min, axis=1)
                                  .apply(highlight_historical_row, axis=1)
                                  .set_table_styles([
                                      {'selector': 'th', 'props': [('text-align', 'center')]},
                                      {'selector': 'td', 'props': [('text-align', 'center')]}
                                  ]))
                else:  # absolute
                    styled_table = (formatted_annual_table
                                  .style
                                  .format("{:.0f}")  # Enteros para cantidades
                                  .apply(highlight_max_min, axis=1)
                                  .apply(highlight_historical_row, axis=1)
                                  .set_table_styles([
                                      {'selector': 'th', 'props': [('text-align', 'center')]},
                                      {'selector': 'td', 'props': [('text-align', 'center')]}
                                  ]))
                # Calcular altura dinámica: ~35px por fila + 35px header
                table_height = (len(formatted_annual_table) + 1) * 35 + 3
                st.dataframe(styled_table, use_container_width=True, height=table_height)
                
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
                        st.metric(_("Avg Annual Variation"), f"{avg_annual_variation:.2f} calls")
                
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
