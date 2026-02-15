#!/bin/bash

# Quick Fix Script for Cloud Run Deployment Error
# This script updates your Cloud Run service with the required environment variables

set -e

echo "🔧 Quick Fix for Cloud Run Deployment"
echo "======================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please create a .env file with your API keys"
    exit 1
fi

# Read API keys from .env
echo "📖 Reading API keys from .env..."
VISION_KEY=$(grep VISION_GEMINI_API_KEY .env | cut -d '=' -f2 | tr -d '"' | tr -d ' ')
NLP_KEY=$(grep NLP_GEMINI_API_KEY .env | cut -d '=' -f2 | tr -d '"' | tr -d ' ')

# Validate keys
if [ -z "$VISION_KEY" ]; then
    echo "❌ Error: VISION_GEMINI_API_KEY not found in .env"
    exit 1
fi

if [ -z "$NLP_KEY" ]; then
    echo "❌ Error: NLP_GEMINI_API_KEY not found in .env"
    exit 1
fi

echo "✓ API keys loaded successfully"
echo ""

# Get project and region
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION="us-central1"
SERVICE_NAME="octus-backend"

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No GCP project configured"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📋 Configuration:"
echo "   Project: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Service: $SERVICE_NAME"
echo ""

# Check if service exists
echo "🔍 Checking if service exists..."
if ! gcloud run services describe $SERVICE_NAME --region $REGION &>/dev/null; then
    echo "❌ Error: Service '$SERVICE_NAME' not found in region '$REGION'"
    echo "Please deploy the service first or check the service name"
    exit 1
fi

echo "✓ Service found"
echo ""

# Update service with environment variables
echo "🚀 Updating Cloud Run service with environment variables..."
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --set-env-vars VISION_GEMINI_API_KEY=$VISION_KEY,NLP_GEMINI_API_KEY=$NLP_KEY \
  --quiet

echo ""
echo "✅ Service updated successfully!"
echo ""

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')

echo "🌐 Service URL: $SERVICE_URL"
echo ""

# Test health endpoint
echo "🧪 Testing health endpoint..."
sleep 5  # Wait for service to be ready

if curl -s -f $SERVICE_URL/health > /dev/null 2>&1; then
    echo "✅ Health check passed!"
    echo ""
    echo "Response:"
    curl -s $SERVICE_URL/health | jq . || curl -s $SERVICE_URL/health
else
    echo "⚠️  Health check failed. The service might still be starting up."
    echo "Wait a minute and try: curl $SERVICE_URL/health"
fi

echo ""
echo "🎉 All done! Your service should now be working."
echo ""
echo "Next steps:"
echo "1. Test the endpoints: curl $SERVICE_URL/health"
echo "2. Check logs if issues persist: gcloud logging read \"resource.type=cloud_run_revision\" --limit 50"
echo "3. View service details: gcloud run services describe $SERVICE_NAME --region $REGION"
