#!/bin/bash

# =============================================================================
# SCRIPT DE BUILD & DEPLOY PARA CALLS ANALYSIS DASHBOARD
# =============================================================================

set -e  # Salir si hay algún error

# Configuración
PROJECT_ID="platform-partners-qua"
SERVICE_NAME="calls-analysis-dashboard"
REGION="us-east1"
SERVICE_ACCOUNT="streamlit-bigquery-sa@platform-partners-qua.iam.gserviceaccount.com"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Iniciando Build & Deploy para Calls Analysis Dashboard"
echo "=================================================="
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
echo "🔨 PASO 1: BUILD (Creando imagen Docker)"
echo "=========================================="
gcloud builds submit --tag ${IMAGE_TAG}

if [ $? -eq 0 ]; then
    echo "✅ Build exitoso!"
else
    echo "❌ Error en el build"
    exit 1
fi

echo ""
echo "🚀 PASO 2: DEPLOY (Desplegando a Cloud Run)"
echo "============================================="
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_TAG} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --port 8080 \
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
echo "📊 Para ver tu dashboard:"
echo "   1. Ve a: https://console.cloud.google.com/run"
echo "   2. Selecciona el servicio: ${SERVICE_NAME}"
echo "   3. Haz clic en la URL del servicio"
echo ""
echo "🔧 Para ver logs en tiempo real:"
echo "   gcloud logs tail --service=${SERVICE_NAME} --region=${REGION}"
echo ""
echo "🛑 Para detener el servicio:"
echo "   gcloud run services delete ${SERVICE_NAME} --region=${REGION}"
