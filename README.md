# Calls Analysis Dashboard
## Análisis de Puntos de Inflexión en Llamadas de ServiceTitan

---

## 📋 **Resumen del Proyecto**

Este proyecto desarrolló un **dashboard interactivo** para analizar **puntos de inflexión** (picos y valles) en el volumen de llamadas mensuales de ServiceTitan. El sistema permite identificar patrones estacionales y tendencias en la distribución de llamadas a lo largo del año.

### **🎯 Objetivo Principal**
Identificar automáticamente los **meses con mayor y menor concentración de llamadas** para cada compañía, permitiendo:
1. **Detección de patrones estacionales** (picos en verano, valles en invierno, etc.)
2. **Análisis de transiciones** entre períodos altos y bajos
3. **Visualización interactiva** de tendencias históricas
4. **Soporte multiidioma** (Inglés/Español)

---

## 🧠 **Concepto Técnico**

### **Puntos de Inflexión**
El análisis identifica dos tipos de puntos críticos en la serie temporal:

#### **Picos (Peaks)**
Meses con concentración de llamadas **por encima del promedio**:
```
Peak: Valor[mes] > Media(valores) AND es_máximo_local
```

#### **Valles (Valleys)**
Meses con concentración de llamadas **por debajo del promedio**:
```
Valley: Valor[mes] < Media(valores) AND es_mínimo_local
```

### **Métodos de Detección Implementados**

#### 1. **Original (find_peaks)**
- Usa SciPy para detectar máximos/mínimos locales
- Parámetros: `height=mean`, `distance=2`
- **Sensibilidad**: Alta (detecta más puntos)

#### 2. **Mathematical Strict**
- Basado en cuartiles estadísticos
- Siempre retorna exactamente 2 picos y 2 valles
- **Sensibilidad**: Baja (solo los extremos)

#### 3. **Hybrid (3-4 months)** ⭐ *Recomendado*
- Combina detección de picos con distancia mínima
- Parámetros: `height=mean`, `distance=3-4`
- **Sensibilidad**: Media (patrones estacionales claros)

---

## 📊 **Funcionalidades del Dashboard**

### **✅ Análisis Principal**
1. **Gráfico de Puntos de Inflexión**
   - Curva suavizada con splines
   - Marcadores de picos (▲ verde) y valles (▼ rojo)
   - Anotaciones con valores exactos (porcentaje o cantidad)
   - Líneas de transición (verde: crecimiento, rojo: descenso)

2. **Análisis del Patrón**
   - Clasificación: Normal, Clustered Points, Non-Alternating, etc.
   - Validación de alternancia entre picos y valles
   - Detección de puntos muy cercanos
   - Recomendaciones automáticas

3. **Estadísticas Detalladas**
   - Cantidad de picos y valles identificados
   - Promedio mensual con 2 decimales
   - Variación máxima
   - Detalles por mes identificado

4. **Tabla de Datos Mensuales**
   - Vista completa de 12 meses (sin scrollbar)
   - Llamadas totales por mes (enteros)
   - Porcentajes con 2 decimales
   - Indicadores de picos y valles

5. **Tabla de Datos Anuales**
   - Comparación año por año
   - Altura dinámica (sin scrollbar)
   - Colores: Verde (máximo), Rosa (mínimo), Gris (sin datos), Lavanda (histórico)
   - Fila histórica para validación

### **🎨 Modos de Análisis**

#### **Modo Porcentajes** (Default)
- Muestra la distribución porcentual de llamadas por mes
- Formato: `8.33%` (2 decimales)
- Ideal para comparar patrones entre compañías de diferente tamaño

#### **Modo Absoluto**
- Muestra la cantidad total de llamadas por mes
- Formato: `1,234` (enteros)
- Ideal para análisis de volumen real

---

## 🌐 **Internacionalización**

### **Detección Automática de Idioma**
El dashboard detecta automáticamente el idioma desde:
1. Parámetro URL: `?lang=es` o `?lang=en`
2. Idioma del navegador (si no hay parámetro)
3. Fallback a inglés

### **Traducciones Implementadas**
- **Inglés**: Interfaz, métricas, meses, mensajes
- **Español**: Interfaz completa, métricas, meses, mensajes

### **Archivos de Traducción**
```
locales/
├── en/
│   └── LC_MESSAGES/
│       ├── messages.po    # Traducción inglés
│       └── messages.mo    # Compilado
└── es/
    └── LC_MESSAGES/
        ├── messages.po    # Traducción español
        └── messages.mo    # Compilado
```

---

## 🔢 **Redondeos y Formato**

### **Estándares Implementados**
- **Porcentajes**: 2 decimales (ej: 8.33%)
- **Cantidad de llamadas**: Enteros (ej: 1,234)
- **Promedios**: 2 decimales (ej: 8.33) - incluso para cantidades
- **Valores en gráficos**: 2 decimales para %, enteros para cantidades

### **Formato en Tablas**
- **Tabla mensual**: Altura fija 490px (12 meses completos)
- **Tabla anual**: Altura dinámica `(años + 1) * 35 + 3`
- **Colores consistentes**: Verde/Rosa/Gris/Lavanda

---

## 🛠️ **Implementación Técnica**

### **Arquitectura**
```
dashboard.py
├── get_calls_info()                      # Consulta BigQuery
├── calculate_monthly_percentages()       # Calcula % por mes
├── analyze_inflection_points_streamlit() # Detecta picos/valles
├── classify_graph_pattern()              # Clasifica patrón
├── calculate_midpoint_lines()            # Calcula transiciones
├── create_inflection_chart()             # Genera gráfico principal
├── calculate_annual_data()               # Tabla año por año
└── main()                                # Interfaz Streamlit
```

### **Consulta BigQuery**
```sql
SELECT c.company_id, c.company_name, cl.location_state,
       EXTRACT(YEAR FROM DATE(cl.lead_call_created_on)) AS year,
       EXTRACT(MONTH FROM DATE(cl.lead_call_created_on)) AS month,
       COUNT(cl.lead_call_id) AS calls,
       COUNT(DISTINCT(cl.campaign_id)) AS campaigns,
       COUNT(cl.lead_call_customer_id) AS customers
FROM `pph-central.analytical.vw_consolidated_call_inbound_location` cl
JOIN `pph-central.settings.companies` c ON cl.company_id = c.company_id
WHERE DATE(cl.lead_call_created_on) < DATE("2025-10-01")
  AND EXTRACT(YEAR FROM DATE(cl.lead_call_created_on)) >= 2015
GROUP BY company_id, company_name, location_state, year, month
ORDER BY company_id, location_state, year, month
```

### **Librerías Principales**
```python
import streamlit as st           # Dashboard interactivo
import matplotlib.pyplot as plt  # Gráficos
import numpy as np               # Cálculos numéricos
import pandas as pd              # Manejo de datos
from scipy.signal import find_peaks        # Detección de picos
from scipy.interpolate import make_interp_spline  # Curvas suaves
from google.cloud import bigquery          # Consultas a BigQuery
import gettext                   # Traducciones
```

---

## 📈 **Análisis de Patrones**

### **Tipos de Patrones Detectados**

#### 1. **Normal** ✅
- Picos y valles alternados
- Bien separados (distancia > 2-3 meses)
- 2 picos + 2 valles
- **Recomendación**: Patrón óptimo

#### 2. **Clustered Points** ⚠️
- Puntos muy cercanos (< 2 meses)
- Dificulta interpretación
- **Recomendación**: Usar "Mathematical Strict"

#### 3. **Non-Alternating** ⚠️
- Picos consecutivos o valles consecutivos
- Patrón irregular
- **Recomendación**: Usar "Hybrid (3-4 months)"

#### 4. **Insufficient Points** ⚠️
- Menos de 4 puntos detectados
- **Recomendación**: Aumentar sensibilidad

#### 5. **Too Many Points** ⚠️
- Más de 4 puntos detectados
- **Recomendación**: Reducir sensibilidad

---

## 🎯 **Líneas de Transición**

### **Puntos Medios (Midpoints)**
Marcas calculadas entre picos y valles consecutivos:

#### **Líneas Verdes** (Crecimiento)
- Transición: Valle → Pico
- Indica períodos de aumento en llamadas
- Cálculo: `midpoint = (valley_month + peak_month) / 2`

#### **Líneas Rojas** (Descenso)
- Transición: Pico → Valle
- Indica períodos de disminución en llamadas
- Cálculo: `midpoint = (peak_month + valley_month) / 2`

#### **Líneas Circulares** (Year-End)
- Transición: Diciembre ↔ Enero
- Considera la circularidad del calendario
- Aparece en ambos extremos del gráfico

---

## 🔧 **Dependencias**

### **Librerías Requeridas**
```
streamlit>=1.28.0
matplotlib>=3.7.0
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.10.0
google-cloud-bigquery>=3.11.0
```

Ver `requirements.txt` para lista completa.

---

## 🚀 **Uso del Dashboard**

### **Ejecución Local (Desarrollo)**
```bash
# Instalar dependencias
pip install -r requirements.txt

# Compilar traducciones
python3 compile_translations.py

# Ejecutar dashboard
streamlit run dashboard.py
```

### **Ejecución con Docker**
```bash
# Construir imagen
docker build -t calls-analysis-dashboard .

# Ejecutar contenedor
docker run -p 8501:8501 calls-analysis-dashboard
```

---

## 🌍 **Deploy a Google Cloud Run (Multi-Ambiente)**

### **Deploy Automático (Recomendado)**
El script detecta automáticamente el ambiente según tu proyecto activo:

```bash
# Deploy automático (usa proyecto activo de gcloud)
./build_deploy.sh
```

### **Deploy Manual por Ambiente**
```bash
# Deploy en DEV (desarrollo y testing - solo tú)
./build_deploy.sh dev

# Deploy en QUA (validación y QA - equipo interno)
./build_deploy.sh qua

# Deploy en PRO (producción - usuarios finales)
./build_deploy.sh pro
```

### **Ambientes Configurados**

| Ambiente | Proyecto | Servicio | Uso |
|----------|----------|----------|-----|
| **DEV** | `platform-partners-des` | `calls-analysis-dashboard-dev` | Desarrollo y testing |
| **QUA** | `platform-partners-qua` | `calls-analysis-dashboard-qua` | Validación y QA |
| **PRO** | `platform-partners-pro` | `calls-analysis-dashboard` | Usuarios finales |

### **Características del Script**
- ✅ Detección automática de ambiente
- ✅ Verificación de archivos necesarios
- ✅ Compilación automática de traducciones
- ✅ Build y deploy integrados
- ✅ Mensajes informativos
- ✅ Manejo de errores
- ✅ Mantiene contexto del proyecto activo

### **Flujo de Trabajo Recomendado**
```bash
# 1. Desarrollo en DEV
gcloud config set project platform-partners-des
./build_deploy.sh
# [Testing personal]

# 2. Validación en QUA
gcloud config set project platform-partners-qua
./build_deploy.sh
# [Validación del equipo]

# 3. Producción en PRO
gcloud config set project platform-partners-pro
./build_deploy.sh
# [Usuarios finales]
```

---

## 📊 **Comandos Útiles**

### **Ver Logs en Tiempo Real**
```bash
# DEV
gcloud logs tail --service=calls-analysis-dashboard-dev --region=us-east1 --project=platform-partners-des

# QUA
gcloud logs tail --service=calls-analysis-dashboard-qua --region=us-east1 --project=platform-partners-qua

# PRO
gcloud logs tail --service=calls-analysis-dashboard --region=us-east1 --project=platform-partners-pro
```

### **Ver Información del Servicio**
```bash
# QUA (ejemplo)
gcloud run services describe calls-analysis-dashboard-qua --region=us-east1 --project=platform-partners-qua
```

### **Detener el Servicio**
```bash
# QUA (ejemplo)
gcloud run services delete calls-analysis-dashboard-qua --region=us-east1 --project=platform-partners-qua
```

### **Obtener URL del Servicio**
```bash
# QUA (ejemplo)
gcloud run services describe calls-analysis-dashboard-qua \
  --region=us-east1 \
  --project=platform-partners-qua \
  --format='value(status.url)'
```

---

## 🔐 **Configuración Inicial de Permisos (Solo Primera Vez)**

Si es la primera vez que despliegas en un ambiente, necesitas configurar permisos:

```bash
# 1. Crear cuenta de servicio (si no existe)
gcloud iam service-accounts create streamlit-bigquery-sa \
    --display-name="Streamlit BigQuery Service Account" \
    --project=platform-partners-qua

# 2. Permisos en proyecto propio
gcloud projects add-iam-policy-binding platform-partners-qua \
    --member="serviceAccount:streamlit-bigquery-sa@platform-partners-qua.iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser"

# 3. Permisos para acceder a pph-central
gcloud projects add-iam-policy-binding pph-central \
    --member="serviceAccount:streamlit-bigquery-sa@platform-partners-qua.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding pph-central \
    --member="serviceAccount:streamlit-bigquery-sa@platform-partners-qua.iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser"

# 4. Permisos para tu usuario
gcloud iam service-accounts add-iam-policy-binding \
    streamlit-bigquery-sa@platform-partners-qua.iam.gserviceaccount.com \
    --member="user:tu-email@peachcfo.com" \
    --role="roles/iam.serviceAccountUser" \
    --project=platform-partners-qua
```

**Nota:** Repite estos comandos para DEV y PRO cambiando el proyecto correspondiente.

---

## 💡 **Insights Generados**

### **Patrones Identificados**
- **Estacionalidad**: Picos en meses específicos (ej: verano)
- **Valles recurrentes**: Meses de baja demanda consistentes
- **Transiciones**: Períodos críticos de cambio
- **Variabilidad histórica**: Consistencia año tras año

### **Valor de Negocio**
- **Planificación**: Anticipar períodos de alta/baja demanda
- **Recursos**: Optimizar asignación de personal y campañas
- **Marketing**: Ajustar inversión según estacionalidad
- **Predicción**: Base para modelos de forecasting

---

## 🆘 **Solución de Problemas**

### **Error: "dashboard.py no encontrado"**
```bash
# Asegúrate de estar en el directorio correcto
cd ~/platform_partners/analysis_predictive/calls_analysis_dashboard/
./build_deploy.sh
```

### **Error de permisos al ejecutar script**
```bash
# Hacer el script ejecutable
chmod +x build_deploy.sh
```

### **Error de autenticación BigQuery**
```bash
# Verificar cuenta de servicio y permisos
gcloud projects get-iam-policy pph-central
```

### **Dashboard no muestra datos**
- Verificar que la vista de BigQuery existe: `pph-central.analytical.vw_consolidated_call_inbound_location`
- Verificar permisos de la cuenta de servicio
- Revisar logs de Cloud Run

### **Traducciones no funcionan**
```bash
# Recompilar traducciones
python3 compile_translations.py

# Verificar archivos .mo existen
ls -la locales/*/LC_MESSAGES/
```

---

## 📁 **Estructura del Proyecto**

```
calls_analysis_dashboard/
├── dashboard.py                 # Dashboard principal
├── build_deploy.sh             # Script de deploy multi-ambiente
├── requirements.txt            # Dependencias Python
├── Dockerfile                  # Configuración Docker
├── .dockerignore              # Archivos a ignorar en Docker
├── compile_translations.py     # Compilador de traducciones
├── README.md                   # Este archivo
└── locales/                    # Traducciones
    ├── en/
    │   └── LC_MESSAGES/
    │       ├── messages.po     # Traducción inglés
    │       └── messages.mo     # Compilado
    └── es/
        └── LC_MESSAGES/
            ├── messages.po     # Traducción español
            └── messages.mo     # Compilado
```

---

## 📞 **Contexto del Proyecto**

### **Plataforma**: ServiceTitan
### **Datos**: Llamadas inbound de marketing y servicio
### **Período**: 2015 - Septiembre 2025
### **Granularidad**: Mensual por compañía
### **Fuente de Datos**: 
- **Vista**: `pph-central.analytical.vw_consolidated_call_inbound_location`
- **Compañías**: `pph-central.settings.companies`

---

## 📝 **Historial de Desarrollo**

### **Fase 1: Concepto y Desarrollo**
- ✅ Análisis de puntos de inflexión básico
- ✅ Implementación de múltiples métodos de detección
- ✅ Gráficos interactivos con Matplotlib
- ✅ Integración con BigQuery

### **Fase 2: Mejoras y Correcciones**
- ✅ Corrección de redondeos (2 decimales para %, enteros para cantidades)
- ✅ Valores en gráficos (mostrar valores reales, no meses)
- ✅ Eliminación de scrollbar en tablas
- ✅ Anotaciones dentro del gráfico (picos abajo, valles arriba)
- ✅ Formato consistente en todas las métricas

### **Fase 3: Internacionalización**
- ✅ Sistema de traducciones con gettext
- ✅ Detección automática de idioma
- ✅ Soporte inglés y español completo

### **Fase 4: Deploy Multi-Ambiente**
- ✅ Script inteligente de deploy
- ✅ Detección automática de ambiente
- ✅ Soporte DEV/QUA/PRO
- ✅ Configuración por ambiente
- ✅ Documentación completa

---

## ✅ **Estado del Desarrollo**

- ✅ **Dashboard principal**: Completamente funcional
- ✅ **Detección de patrones**: 3 métodos implementados
- ✅ **Gráficos**: Interactivos con valores correctos
- ✅ **Tablas**: Sin scrollbar, formato correcto
- ✅ **Redondeos**: Estándares aplicados (2 decimales/enteros)
- ✅ **Traducciones**: Inglés y español
- ✅ **Deploy multi-ambiente**: DEV/QUA/PRO configurado
- ✅ **Documentación**: Completa y unificada
- 🔄 **Exportación**: Por implementar (CSV, PDF, Google Sheets)
- 🔄 **Comparación multi-compañía**: Por implementar

---

## 🔗 **Enlaces Útiles**

- **Cloud Console**: https://console.cloud.google.com/
- **Cloud Run Services**: https://console.cloud.google.com/run
- **BigQuery**: https://console.cloud.google.com/bigquery
- **Service Accounts**: https://console.cloud.google.com/iam-admin/serviceaccounts

---

**Desarrollado por**: Platform Partners Team  
**Fecha**: Octubre 2025  
**Versión**: 2.0  
**Estado**: Producción (Multi-Ambiente)

