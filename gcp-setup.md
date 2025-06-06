# Google Cloud Platform Deployment Guide

This guide covers deploying your Opus Agent FastAPI application to Google Cloud Platform. You have several deployment options depending on your needs.

## Prerequisites

1. **Google Cloud Account**: Set up a GCP account with billing enabled
2. **gcloud CLI**: Install and authenticate the Google Cloud CLI
3. **Docker**: Install Docker for building container images
4. **OpenAI API Key**: Have your OpenAI API key ready

## Quick Setup

```bash
# Install gcloud CLI (if not already installed)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authenticate with Google Cloud
gcloud auth login
gcloud auth configure-docker

# Create a new project (optional)
gcloud projects create your-project-id --name="Opus Agent"
gcloud config set project your-project-id
```

## Deployment Options

### Option 1: Google Cloud Run (Recommended) 🚀

**Best for**: Production use, automatic scaling, cost-effective
**Pros**: Serverless, scales to zero, HTTPS out of the box, integrated logging
**Cons**: Cold starts (minimal for this use case), regional limitations

#### Quick Deploy with Script

1. Update the `PROJECT_ID` in `deploy-gcp.sh`
2. Make the script executable and run:

```bash
chmod +x deploy-gcp.sh
./deploy-gcp.sh
```

#### Manual Deploy

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export SERVICE_NAME="opus-agent"
export REGION="us-central1"

# Enable APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com

# Build and deploy
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --port 8000 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --concurrency 1000 \
    --max-instances 10
```

### Option 2: Google Compute Engine VM

**Best for**: Full control, persistent connections, custom configurations
**Pros**: Full VM control, persistent state, no cold starts
**Cons**: Always-on billing, manual scaling, more management overhead

```bash
# Create a VM instance
gcloud compute instances create opus-agent-vm \
    --zone=us-central1-a \
    --machine-type=e2-standard-2 \
    --image-family=ubuntu-2004-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB \
    --tags=http-server,https-server

# SSH into the instance
gcloud compute ssh opus-agent-vm --zone=us-central1-a

# On the VM, install dependencies
sudo apt update
sudo apt install -y docker.io git python3-pip
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Clone and run your application
git clone <your-repo-url>
cd fastagent
sudo docker build -t opus-agent .
sudo docker run -d -p 8000:8000 -e OPENAI_API_KEY="your-key" opus-agent

# Create firewall rule
gcloud compute firewall-rules create allow-opus-agent \
    --allow tcp:8000 \
    --source-ranges 0.0.0.0/0 \
    --target-tags http-server
```

### Option 3: Google Kubernetes Engine (GKE)

**Best for**: Multiple services, complex orchestration, high availability
**Pros**: Full Kubernetes features, horizontal scaling, service mesh
**Cons**: More complex, higher cost, overkill for single service

```bash
# Create GKE cluster
gcloud container clusters create opus-agent-cluster \
    --zone=us-central1-a \
    --num-nodes=2 \
    --machine-type=e2-standard-2

# Get cluster credentials
gcloud container clusters get-credentials opus-agent-cluster --zone=us-central1-a

# Build and push image
gcloud builds submit --tag gcr.io/$PROJECT_ID/opus-agent

# Deploy to GKE (create deployment.yaml first)
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

## Configuration

### Environment Variables

Set these environment variables in your chosen deployment:

```bash
# Required
OPENAI_API_KEY="sk-..."

# Optional (with defaults)
ENV="production"
PORT="8000"
HOST="0.0.0.0"
LOG_LEVEL="INFO"
```

### For Cloud Run
```bash
gcloud run services update opus-agent \
    --region us-central1 \
    --set-env-vars="OPENAI_API_KEY=sk-..." \
    --set-env-vars="ENV=production"
```

### For Compute Engine
```bash
# Create a .env file or set environment variables
echo "OPENAI_API_KEY=sk-..." | sudo tee /etc/environment
```

## Monitoring and Logging

### Cloud Run Logs
```bash
# View logs
gcloud run services logs read opus-agent --region us-central1 --follow

# View metrics in Cloud Console
# https://console.cloud.google.com/run
```

### VM Logs
```bash
# SSH to VM and check Docker logs
gcloud compute ssh opus-agent-vm --zone=us-central1-a
sudo docker logs <container-id> -f
```

## Twilio Integration

Once deployed, update your Twilio configuration:

1. **Get your service URL**:
   ```bash
   gcloud run services describe opus-agent --region us-central1 --format "value(status.url)"
   ```

2. **Add Twilio WebSocket endpoint** to your FastAPI app (if not already done):
   ```python
   @app.websocket("/twilio-ws")
   async def handle_twilio_call(websocket: WebSocket):
       # Use TwilioRealtimeBridge instead of TelephonyRealtimeBridge
       # ... implementation
   ```

3. **Configure Twilio Webhook URL**:
   - Go to Twilio Console → Phone Numbers → Manage → Active numbers
   - Select your phone number
   - Set Webhook URL to: `https://your-service-url.run.app/twilio-ws`

## Security Best Practices

1. **Use Secret Manager** for sensitive data:
   ```bash
   # Store OpenAI API key in Secret Manager
   echo "sk-..." | gcloud secrets create openai-api-key --data-file=-
   
   # Grant Cloud Run access to the secret
   gcloud secrets add-iam-policy-binding openai-api-key \
       --member="serviceAccount:your-service-account@your-project.iam.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor"
   ```

2. **Enable IAM authentication** if needed:
   ```bash
   gcloud run services update opus-agent --region us-central1 --no-allow-unauthenticated
   ```

3. **Set up custom domain** with SSL:
   ```bash
   gcloud run domain-mappings create \
       --service opus-agent \
       --domain your-domain.com \
       --region us-central1
   ```

## Cost Optimization

### Cloud Run
- **Auto-scaling**: Scales to zero when not in use
- **Resource allocation**: Start with 1 CPU, 1Gi memory, adjust based on usage
- **Request-based billing**: Only pay for actual requests

### Compute Engine
- **Preemptible instances**: 60-91% cheaper, good for development
- **Right-sizing**: Use `e2-micro` for testing, `e2-standard-2` for production
- **Sustained use discounts**: Automatic discounts for long-running instances

## Troubleshooting

### Common Issues

1. **WebSocket Connection Fails**:
   ```bash
   # Check if service is running
   gcloud run services describe opus-agent --region us-central1
   
   # Check logs for errors
   gcloud run services logs read opus-agent --region us-central1 --limit 50
   ```

2. **OpenAI API Key Issues**:
   ```bash
   # Verify environment variable is set
   gcloud run services describe opus-agent --region us-central1 --format="value(spec.template.spec.template.spec.containers[0].env[].value)"
   ```

3. **Performance Issues**:
   - Increase CPU/memory allocation
   - Check for cold start latency
   - Monitor request metrics in Cloud Console

### Health Check Endpoint

Add to your FastAPI app:
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}
```

## Next Steps

1. **Set up CI/CD**: Use the included `cloudbuild.yaml` for automated deployments
2. **Monitor performance**: Set up Cloud Monitoring alerts
3. **Scale as needed**: Adjust instance limits and resource allocation
4. **Backup strategy**: Consider database backups if using persistent storage

## Support

- **Google Cloud Support**: Available with paid support plans
- **Community**: Stack Overflow, Google Cloud Community
- **Documentation**: https://cloud.google.com/run/docs 