# 🚀 Instrucciones de Deploy - Calls Analysis Dashboard

## 📋 Scripts Disponibles

### Linux/macOS (Bash)
```bash
./build_deploy.sh
```

### Windows (PowerShell)
```powershell
.\build_deploy.ps1
```

## 🔧 Configuración

El script está configurado con:
- **Proyecto**: `pph-central`
- **Servicio**: `calls-analysis-dashboard`
- **Región**: `us-east1`
- **Service Account**: `streamlit-bigquery-sa@platform-partners-qua.iam.gserviceaccount.com`

## 📝 Comandos Manuales (si prefieres ejecutarlos uno por uno)

### 1. Build
```bash
gcloud builds submit --tag gcr.io/pph-central/calls-analysis-dashboard
```

### 2. Deploy
```bash
gcloud run deploy calls-analysis-dashboard \
  --image gcr.io/pph-central/calls-analysis-dashboard \
  --platform managed \
  --region us-east1 \
  --allow-unauthenticated \
  --port 8080 \
  --service-account streamlit-bigquery-sa@platform-partners-qua.iam.gserviceaccount.com
```

## 🔍 Verificación

### Ver logs en tiempo real:
```bash
gcloud logs tail --service=calls-analysis-dashboard --region=us-east1
```

### Ver información del servicio:
```bash
gcloud run services describe calls-analysis-dashboard --region=us-east1
```

### Detener el servicio:
```bash
gcloud run services delete calls-analysis-dashboard --region=us-east1
```

## ⚠️ Notas Importantes

1. **Ejecuta desde el directorio correcto**: Asegúrate de estar en `calls_analysis_dashboard/`
2. **Autenticación**: Asegúrate de estar autenticado con `gcloud auth login`
3. **Proyecto**: El script verifica y configura automáticamente el proyecto correcto
4. **Service Account**: Necesario para acceso a BigQuery

## 🆘 Solución de Problemas

### Error de permisos:
```bash
gcloud auth login
gcloud config set project pph-central
```

### Error de región:
Verifica que la región `us-east1` esté disponible:
```bash
gcloud run regions list
```

### Error de service account:
Verifica que el service account tenga permisos de BigQuery:
```bash
gcloud projects get-iam-policy pph-central
```



