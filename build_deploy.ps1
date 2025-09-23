# =============================================================================
# SCRIPT DE BUILD & DEPLOY PARA CALLS ANALYSIS DASHBOARD (Windows PowerShell)
# =============================================================================

# Configuración
$PROJECT_ID = "pph-central"
$SERVICE_NAME = "calls-analysis-dashboard"
$REGION = "us-east1"
$SERVICE_ACCOUNT = "streamlit-bigquery-sa@platform-partners-qua.iam.gserviceaccount.com"
$IMAGE_TAG = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

Write-Host "🚀 Iniciando Build & Deploy para Calls Analysis Dashboard" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host "📋 Configuración:" -ForegroundColor Yellow
Write-Host "   Proyecto: $PROJECT_ID" -ForegroundColor White
Write-Host "   Servicio: $SERVICE_NAME" -ForegroundColor White
Write-Host "   Región: $REGION" -ForegroundColor White
Write-Host "   Imagen: $IMAGE_TAG" -ForegroundColor White
Write-Host "   Service Account: $SERVICE_ACCOUNT" -ForegroundColor White
Write-Host ""

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "dashboard.py")) {
    Write-Host "❌ Error: dashboard.py no encontrado. Ejecuta este script desde el directorio calls_analysis_dashboard/" -ForegroundColor Red
    exit 1
}

# Verificar que gcloud está disponible
try {
    gcloud version | Out-Null
} catch {
    Write-Host "❌ Error: gcloud CLI no está instalado o no está en el PATH" -ForegroundColor Red
    exit 1
}

# Verificar proyecto activo
$CURRENT_PROJECT = gcloud config get-value project
if ($CURRENT_PROJECT -ne $PROJECT_ID) {
    Write-Host "⚠️  Proyecto actual: $CURRENT_PROJECT" -ForegroundColor Yellow
    Write-Host "🔧 Configurando proyecto a: $PROJECT_ID" -ForegroundColor Yellow
    gcloud config set project $PROJECT_ID
}

Write-Host ""
Write-Host "🔨 PASO 1: BUILD (Creando imagen Docker)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
gcloud builds submit --tag $IMAGE_TAG

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build exitoso!" -ForegroundColor Green
} else {
    Write-Host "❌ Error en el build" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🚀 PASO 2: DEPLOY (Desplegando a Cloud Run)" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_TAG `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --port 8080 `
    --service-account $SERVICE_ACCOUNT

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Deploy exitoso!" -ForegroundColor Green
} else {
    Write-Host "❌ Error en el deploy" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎉 ¡DEPLOY COMPLETADO EXITOSAMENTE!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Para ver tu dashboard:" -ForegroundColor Yellow
Write-Host "   1. Ve a: https://console.cloud.google.com/run" -ForegroundColor White
Write-Host "   2. Selecciona el servicio: $SERVICE_NAME" -ForegroundColor White
Write-Host "   3. Haz clic en la URL del servicio" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Para ver logs en tiempo real:" -ForegroundColor Yellow
Write-Host "   gcloud logs tail --service=$SERVICE_NAME --region=$REGION" -ForegroundColor White
Write-Host ""
Write-Host "🛑 Para detener el servicio:" -ForegroundColor Yellow
Write-Host "   gcloud run services delete $SERVICE_NAME --region=$REGION" -ForegroundColor White
