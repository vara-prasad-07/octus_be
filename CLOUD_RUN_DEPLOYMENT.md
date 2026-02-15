# Google Cloud Run Deployment Guide

## The Error You're Seeing

```
The user-provided container failed to start and listen on the port defined provided by
the PORT=8080 environment variable within the allocated timeout.
```

This happens because the application crashes on startup when the required environment variables (`VISION_GEMINI_API_KEY` and `NLP_GEMINI_API_KEY`) are not set.

## Solution: Add Environment Variables to Cloud Run

### Option 1: Using Google Cloud Console (Easiest)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **Cloud Run**
3. Click on your service **octus-backend**
4. Click **EDIT & DEPLOY NEW REVISION**
5. Scroll down to **Variables & Secrets**
6. Click **ADD VARIABLE** and add:
   - Name: `VISION_GEMINI_API_KEY`
   - Value: Your vision API key
7. Click **ADD VARIABLE** again and add:
   - Name: `NLP_GEMINI_API_KEY`
   - Value: Your NLP API key
8. Click **DEPLOY**

### Option 2: Using gcloud CLI

```bash
gcloud run services update octus-backend \
  --region us-central1 \
  --set-env-vars VISION_GEMINI_API_KEY=your-vision-key,NLP_GEMINI_API_KEY=your-nlp-key
```

### Option 3: Using Cloud Build with Secrets (Recommended for Production)

#### Step 1: Store API Keys in Secret Manager

```bash
# Create secrets
echo -n "your-vision-api-key" | gcloud secrets create vision-gemini-api-key --data-file=-
echo -n "your-nlp-api-key" | gcloud secrets create nlp-gemini-api-key --data-file=-

# Grant Cloud Build access to secrets
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")

gcloud secrets add-iam-policy-binding vision-gemini-api-key \
  --member=serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor

gcloud secrets add-iam-policy-binding nlp-gemini-api-key \
  --member=serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

#### Step 2: Update cloudbuild.yaml

The `cloudbuild.yaml` has been updated to use these secrets. Now you need to configure the build trigger:

```yaml
# cloudbuild.yaml (already updated)
steps:
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'octus-backend'
      - '--set-env-vars'
      - 'VISION_GEMINI_API_KEY=$$VISION_GEMINI_API_KEY,NLP_GEMINI_API_KEY=$$NLP_GEMINI_API_KEY'
    secretEnv: ['VISION_GEMINI_API_KEY', 'NLP_GEMINI_API_KEY']

availableSecrets:
  secretManager:
  - versionName: projects/$PROJECT_ID/secrets/vision-gemini-api-key/versions/latest
    env: 'VISION_GEMINI_API_KEY'
  - versionName: projects/$PROJECT_ID/secrets/nlp-gemini-api-key/versions/latest
    env: 'NLP_GEMINI_API_KEY'
```

#### Step 3: Trigger a New Build

```bash
gcloud builds submit --config cloudbuild.yaml
```

## Quick Fix (Immediate Solution)

If you need to fix this immediately:

```bash
# Get your current API key from .env
VISION_KEY=$(grep VISION_GEMINI_API_KEY .env | cut -d '=' -f2 | tr -d '"')
NLP_KEY=$(grep NLP_GEMINI_API_KEY .env | cut -d '=' -f2 | tr -d '"')

# Update Cloud Run service
gcloud run services update octus-backend \
  --region us-central1 \
  --set-env-vars VISION_GEMINI_API_KEY=$VISION_KEY,NLP_GEMINI_API_KEY=$NLP_KEY
```

## Verify the Deployment

After setting the environment variables:

```bash
# Check service status
gcloud run services describe octus-backend --region us-central1

# Get the service URL
SERVICE_URL=$(gcloud run services describe octus-backend --region us-central1 --format='value(status.url)')

# Test the health endpoint
curl $SERVICE_URL/health

# Should return: {"status":"healthy"}
```

## Troubleshooting

### Error: "Container failed to start"

**Check logs:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=octus-backend" --limit 50 --format json
```

**Common causes:**
1. Environment variables not set
2. Invalid API keys
3. Port misconfiguration
4. Memory/CPU limits too low

### Error: "Service timeout"

**Increase timeout:**
```bash
gcloud run services update octus-backend \
  --region us-central1 \
  --timeout 300
```

### Error: "Out of memory"

**Increase memory:**
```bash
gcloud run services update octus-backend \
  --region us-central1 \
  --memory 2Gi
```

## Complete Deployment Script

Save this as `deploy.sh`:

```bash
#!/bin/bash

set -e

echo "🚀 Deploying Octus Backend to Cloud Run"

# Configuration
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
SERVICE_NAME="octus-backend"

# Read API keys from .env
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    exit 1
fi

VISION_KEY=$(grep VISION_GEMINI_API_KEY .env | cut -d '=' -f2 | tr -d '"')
NLP_KEY=$(grep NLP_GEMINI_API_KEY .env | cut -d '=' -f2 | tr -d '"')

if [ -z "$VISION_KEY" ] || [ -z "$NLP_KEY" ]; then
    echo "❌ Error: API keys not found in .env"
    exit 1
fi

echo "✓ API keys loaded from .env"

# Build and push image
echo "📦 Building container image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
echo "🚢 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10 \
  --timeout 300 \
  --set-env-vars VISION_GEMINI_API_KEY=$VISION_KEY,NLP_GEMINI_API_KEY=$NLP_KEY

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "Testing health endpoint..."
curl -s $SERVICE_URL/health | jq .

echo ""
echo "🎉 All done! Your service is live at: $SERVICE_URL"
```

Make it executable and run:
```bash
chmod +x deploy.sh
./deploy.sh
```

## Environment Variables Checklist

Before deploying, ensure:

- [ ] `VISION_GEMINI_API_KEY` is set in Cloud Run
- [ ] `NLP_GEMINI_API_KEY` is set in Cloud Run
- [ ] Both keys are valid and active
- [ ] Keys have proper permissions in Google AI Studio
- [ ] Service has enough memory (1Gi minimum)
- [ ] Timeout is set to 300 seconds
- [ ] Port 8080 is exposed in Dockerfile

## Next Steps

1. Set the environment variables using one of the methods above
2. Redeploy the service
3. Test the endpoints
4. Monitor the logs for any issues

## Support

If you continue to have issues:

1. Check Cloud Run logs: `gcloud logging read "resource.type=cloud_run_revision" --limit 50`
2. Verify environment variables: `gcloud run services describe octus-backend --region us-central1`
3. Test locally first: `docker build -t octus-backend . && docker run -p 8080:8080 -e VISION_GEMINI_API_KEY=xxx -e NLP_GEMINI_API_KEY=xxx octus-backend`
