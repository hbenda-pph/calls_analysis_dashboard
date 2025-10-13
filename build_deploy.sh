#!/bin/bash

# =============================================================================
# SCRIPT DE BUILD & DEPLOY PARA CALLS ANALYSIS DASHBOARD
# Multi-Environment: DEV, QUA, PRO
# =============================================================================

set -e  # Salir si hay algún error

# =============================================================================
# CONFIGURACIÓN DE AMBIENTES
# =============================================================================

# Detectar proyecto activo de gcloud
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)

# Si se proporciona parámetro, usarlo; si no, detectar automáticamente
if [ -n "$1" ]; then
    # Parámetro proporcionado explícitamente
    ENVIRONMENT="$1"
    ENVIRONMENT=$(echo "$ENVIRONMENT" | tr '[:upper:]' '[:lower:]')  # Convertir a minúsculas
    
    # Validar ambiente
    if [[ ! "$ENVIRONMENT" =~ ^(dev|qua|pro)$ ]]; then
        echo "❌ Error: Ambiente inválido '$ENVIRONMENT'"
        echo "Uso: ./build_deploy.sh [dev|qua|pro]"
        echo ""
        echo "Ejemplos:"
        echo "  ./build_deploy.sh dev    # Deploy en DEV (platform-partners-des)"
        echo "  ./build_deploy.sh qua    # Deploy en QUA (platform-partners-qua)"
        echo "  ./build_deploy.sh pro    # Deploy en PRO (platform-partners-pro)"
        echo ""
        echo "O ejecuta sin parámetros para usar el proyecto activo de gcloud"
        exit 1
    fi
else
    # Detectar automáticamente según el proyecto activo
    echo "🔍 Detectando ambiente desde proyecto activo de gcloud..."
    
    case "$CURRENT_PROJECT" in
        platform-partners-des)
            ENVIRONMENT="dev"
            echo "✅ Detectado: DEV (platform-partners-des)"
            ;;
        platform-partners-qua)
            ENVIRONMENT="qua"
            echo "✅ Detectado: QUA (platform-partners-qua)"
            ;;
        platform-partners-pro)
            ENVIRONMENT="pro"
            echo "✅ Detectado: PRO (platform-partners-pro)"
            ;;
        *)
            echo "⚠️  Proyecto activo: ${CURRENT_PROJECT}"
            echo "⚠️  No se reconoce el proyecto. Usando DEV por defecto."
            ENVIRONMENT="dev"
            ;;
    esac
fi

# Configuración según ambiente
case "$ENVIRONMENT" in
    dev)
        PROJECT_ID="platform-partners-des"
        SERVICE_NAME="calls-analysis-dashboard-dev"
        SERVICE_ACCOUNT="streamlit-bigquery-sa@platform-partners-des.iam.gserviceaccount.com"
        ;;
    qua)
        PROJECT_ID="platform-partners-qua"
        SERVICE_NAME="calls-analysis-dashboard-qua"
        SERVICE_ACCOUNT="streamlit-bigquery-sa@platform-partners-qua.iam.gserviceaccount.com"
        ;;
    pro)
        PROJECT_ID="platform-partners-pro"
        SERVICE_NAME="calls-analysis-dashboard"
        SERVICE_ACCOUNT="streamlit-bigquery-sa@platform-partners-pro.iam.gserviceaccount.com"
        ;;
esac

REGION="us-east1"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Iniciando Build & Deploy para Calls Analysis Dashboard"
echo "================================================================"
echo "🌍 AMBIENTE: ${ENVIRONMENT^^}"
echo "📋 Configuración:"
echo "   Proyecto: ${PROJECT_ID}"
echo "   Servicio: ${SERVICE_NAME}"
echo "   Región: ${REGION}"
echo "   Imagen: ${IMAGE_TAG}"
echo "   Service Account: ${SERVICE_ACCOUNT}"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "dashboard.py" ]; then
    echo "❌ Error: dashboard.py no encontrado. Ejecuta este script desde el directorio calls_analysis_dashboard/"
    exit 1
fi

# Verificar que gcloud está configurado
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI no está instalado o no está en el PATH"
    exit 1
fi

# Verificar proyecto activo
CURRENT_PROJECT=$(gcloud config get-value project)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    echo "⚠️  Proyecto actual: ${CURRENT_PROJECT}"
    echo "🔧 Configurando proyecto a: ${PROJECT_ID}"
    gcloud config set project ${PROJECT_ID}
fi

echo ""
echo "📦 PASO 1: PREPARACIÓN (Verificando archivos)"
echo "=============================================="

# Verificar archivos necesarios
if [ -f "dashboard.py" ]; then
    echo "✅ dashboard.py encontrado"
else
    echo "❌ dashboard.py no encontrado"
    exit 1
fi

if [ -f "requirements.txt" ]; then
    echo "✅ requirements.txt encontrado"
else
    echo "❌ requirements.txt no encontrado"
    exit 1
fi

if [ -f "Dockerfile" ]; then
    echo "✅ Dockerfile encontrado"
else
    echo "❌ Dockerfile no encontrado"
    exit 1
fi

# Verificar traducciones compiladas
if [ -d "locales" ]; then
    echo "✅ Directorio locales encontrado"
    
    # Compilar traducciones si es necesario
    if [ -f "compile_translations.py" ]; then
        echo "🔄 Compilando traducciones..."
        python3 compile_translations.py
        echo "✅ Traducciones compiladas"
    fi
else
    echo "⚠️  Advertencia: No se encontró directorio locales"
fi

echo ""
echo "🔨 PASO 2: BUILD (Creando imagen Docker)"
echo "=========================================="
gcloud builds submit --tag ${IMAGE_TAG}

if [ $? -eq 0 ]; then
    echo "✅ Build exitoso!"
else
    echo "❌ Error en el build"
    exit 1
fi

echo ""
echo "🚀 PASO 3: DEPLOY (Desplegando a Cloud Run)"
echo "============================================="
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_TAG} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --port 8501 \
    --service-account ${SERVICE_ACCOUNT}

if [ $? -eq 0 ]; then
    echo "✅ Deploy exitoso!"
else
    echo "❌ Error en el deploy"
    exit 1
fi

echo ""
echo "🎉 ¡DEPLOY COMPLETADO EXITOSAMENTE!"
echo "=================================="
echo ""
echo "🌍 AMBIENTE: ${ENVIRONMENT^^}"
echo "📊 Para ver tu dashboard:"
echo "   1. Ve a: https://console.cloud.google.com/run?project=${PROJECT_ID}"
echo "   2. Selecciona el servicio: ${SERVICE_NAME}"
echo "   3. Haz clic en la URL del servicio"
echo ""
echo "🔧 Para ver logs en tiempo real:"
echo "   gcloud logs tail --service=${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID}"
echo ""
echo "🔄 Para deploy en otros ambientes:"
echo "   ./build_deploy.sh dev    # Deploy en DEV (solo para testing)"
echo "   ./build_deploy.sh qua    # Deploy en QUA (para validación)"
echo "   ./build_deploy.sh pro    # Deploy en PRO (usuarios finales)"
echo ""
echo "🛑 Para detener el servicio:"
echo "   gcloud run services delete ${SERVICE_NAME} --region=${REGION} --project=${PROJECT_ID}"
echo ""
echo "📝 Notas:"
echo "   - DEV: Para desarrollo y testing (solo tú)"
echo "   - QUA: Para validación y QA (equipo interno)"
echo "   - PRO: Para usuarios finales (producción)"
