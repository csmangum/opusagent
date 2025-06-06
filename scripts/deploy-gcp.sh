#!/bin/bash

# Google Cloud Run Deployment Script for Opus Agent
# This script deploys your FastAPI WebSocket application to Cloud Run

set -e

# Configuration
PROJECT_ID="your-project-id"  # Replace with your GCP project ID
SERVICE_NAME="opus-agent"
REGION="us-central1"  # Choose your preferred region
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying Opus Agent to Google Cloud Run${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install it first.${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Pre-deployment checklist:${NC}"
echo "1. Make sure you have set your OPENAI_API_KEY in the environment"
echo "2. Update PROJECT_ID in this script"
echo "3. Ensure you're authenticated with gcloud"

read -p "Continue with deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Set the project
echo -e "${YELLOW}🔧 Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build and push the Docker image
echo -e "${YELLOW}🏗️ Building Docker image...${NC}"
docker build -t $IMAGE_NAME .

echo -e "${YELLOW}📤 Pushing image to Container Registry...${NC}"
docker push $IMAGE_NAME

# Deploy to Cloud Run
echo -e "${YELLOW}🚀 Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --port 8000 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --concurrency 1000 \
    --max-instances 10 \
    --set-env-vars "ENV=production,PORT=8000,HOST=0.0.0.0" \
    --set-secrets "OPENAI_API_KEY=openai-api-key:latest"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)")

echo -e "${GREEN}✅ Deployment completed!${NC}"
echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"
echo -e "${GREEN}🔗 WebSocket endpoint: ${SERVICE_URL}/ws${NC}"

echo -e "${YELLOW}⚠️ Don't forget to:${NC}"
echo "1. Set your OPENAI_API_KEY as a secret (see instructions below)"
echo "2. Update your Twilio webhook URL to: ${SERVICE_URL}/ws"
echo "3. Configure your domain/SSL if needed"

echo -e "${YELLOW}📝 To set environment variables securely:${NC}"
echo "gcloud run services update $SERVICE_NAME --region $REGION --set-env-vars=\"OPENAI_API_KEY=your-api-key\""

echo -e "${YELLOW}📊 Monitor your service:${NC}"
echo "gcloud run services logs read $SERVICE_NAME --region $REGION --follow" 