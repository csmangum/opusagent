#!/bin/bash

# Updated Quick GCP Cloud Run Deployment for Opus Agent (2024)
# Usage: ./quick-deploy-updated.sh <project-id> [openai-api-key]

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}Usage: $0 <project-id> [openai-api-key]${NC}"
    echo "Example: $0 my-gcp-project sk-..."
    exit 1
fi

PROJECT_ID=$1
OPENAI_API_KEY=${2:-$OPENAI_API_KEY}

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}Error: OpenAI API key not provided${NC}"
    echo "Either pass it as second argument or set OPENAI_API_KEY environment variable"
    exit 1
fi

SERVICE_NAME="opus-agent"
REGION="us-central1"  # Update to your preferred region

echo -e "${GREEN}🚀 Quick deploying Opus Agent to Google Cloud Run...${NC}"
echo -e "${YELLOW}📋 Project: $PROJECT_ID${NC}"
echo -e "${YELLOW}🌍 Region: $REGION${NC}"
echo -e "${YELLOW}🔑 OpenAI API Key: ${OPENAI_API_KEY:0:10}...${NC}"

# Set project
gcloud config set project $PROJECT_ID

# Enable APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com --quiet

# Build and deploy with optimized settings for WebSockets
echo -e "${YELLOW}🏗️ Building and deploying with WebSocket optimization...${NC}"
gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --port 8000 \
    --memory 4Gi \
    --cpu 2 \
    --timeout 3600 \
    --concurrency 100 \
    --max-instances 20 \
    --min-instances 1 \
    --cpu-boost \
    --execution-environment gen2 \
    --set-env-vars "ENV=production,PORT=8000,HOST=0.0.0.0,OPENAI_API_KEY=$OPENAI_API_KEY" \
    --quiet

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)")

echo ""
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Service URL: $SERVICE_URL${NC}"
echo -e "${GREEN}🔗 Twilio WebSocket endpoint: $SERVICE_URL/twilio-agent${NC}"
echo -e "${GREEN}🔗 AudioCodes endpoint: $SERVICE_URL/voice-bot${NC}"
echo -e "${GREEN}💚 Health check: $SERVICE_URL/health${NC}"
echo ""
echo -e "${YELLOW}📝 Next steps for Twilio integration:${NC}"
echo "1. Test the health endpoint: curl $SERVICE_URL/health"
echo "2. Update your Twilio webhook URL to: $SERVICE_URL/twilio-agent"
echo "3. Configure Twilio Media Streams to use WebSocket URL: $SERVICE_URL/twilio-agent"
echo ""
echo -e "${YELLOW}📊 Monitoring:${NC}"
echo "View logs: gcloud run services logs read $SERVICE_NAME --region $REGION --follow"
echo "View metrics: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME"
echo ""
echo -e "${YELLOW}💡 Twilio Configuration Tips:${NC}"
echo "- Ensure your Twilio phone number webhook points to: $SERVICE_URL/twilio-agent"
echo "- Use WSS (secure WebSocket) for production: wss://$(echo $SERVICE_URL | sed 's|https://||')/twilio-agent"
echo "- Set timeout to maximum (3600s) for long conversations"