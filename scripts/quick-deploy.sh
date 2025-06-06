#!/bin/bash

# Quick GCP Cloud Run Deployment for Opus Agent
# Usage: ./quick-deploy.sh your-project-id [your-openai-api-key]

set -e

# Check arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 <project-id> [openai-api-key]"
    echo "Example: $0 my-gcp-project sk-..."
    exit 1
fi

PROJECT_ID=$1
OPENAI_API_KEY=${2:-$OPENAI_API_KEY}

if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OpenAI API key not provided"
    echo "Either pass it as second argument or set OPENAI_API_KEY environment variable"
    exit 1
fi

SERVICE_NAME="opus-agent"
REGION="us-central1"

echo "🚀 Quick deploying Opus Agent to Google Cloud Run..."
echo "📋 Project: $PROJECT_ID"
echo "🌍 Region: $REGION"
echo "🔑 OpenAI API Key: ${OPENAI_API_KEY:0:10}..."

# Set project
gcloud config set project $PROJECT_ID

# Enable APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com run.googleapis.com --quiet

# Build and deploy in one command
echo "🏗️ Building and deploying..."
gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --port 8000 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --concurrency 1000 \
    --max-instances 10 \
    --set-env-vars "ENV=production,PORT=8000,HOST=0.0.0.0,OPENAI_API_KEY=$OPENAI_API_KEY" \
    --quiet

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)")

echo ""
echo "✅ Deployment completed!"
echo "🌐 Service URL: $SERVICE_URL"
echo "🔗 AudioCodes endpoint: $SERVICE_URL/voice-bot"
echo "🔗 Twilio endpoint: $SERVICE_URL/twilio-ws"
echo "💚 Health check: $SERVICE_URL/health"
echo ""
echo "📝 Next steps:"
echo "1. Test the health endpoint: curl $SERVICE_URL/health"
echo "2. Update your Twilio webhook URL to: $SERVICE_URL/twilio-ws"
echo "3. Configure your AudioCodes to point to: $SERVICE_URL/voice-bot"
echo ""
echo "📊 View logs: gcloud run services logs read $SERVICE_NAME --region $REGION --follow" 