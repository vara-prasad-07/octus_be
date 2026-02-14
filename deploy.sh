#!/bin/bash

# Deployment script for Google Cloud Run
# Usage: ./deploy.sh [PROJECT_ID] [REGION]

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}
SERVICE_NAME="octus-backend"

echo "Deploying to Google Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"

# Build and deploy
gcloud run deploy $SERVICE_NAME \
  --source . \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=1Gi \
  --cpu=1 \
  --max-instances=10 \
  --timeout=300 \
  --set-env-vars="ENVIRONMENT=production"

echo "Deployment complete!"
echo "Service URL:"
gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)'
