# Quick Deploy Guide: Opus Server on GCP Cloud Run (2024)

**Deploy your Opus server to accept Twilio connections in under 5 minutes! 🚀**

## Prerequisites (1 minute)

1. **Google Cloud SDK** installed and authenticated
2. **GCP Project** with billing enabled
3. **OpenAI API Key** ready

```bash
# Quick setup
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

## Option 1: Ultra-Fast Deploy ⚡ (2-3 minutes)

```bash
# Make script executable
chmod +x scripts/quick-deploy-updated.sh

# Deploy (replace with your values)
./scripts/quick-deploy-updated.sh YOUR_PROJECT_ID YOUR_OPENAI_API_KEY
```

**That's it!** Your server will be deployed with optimal WebSocket settings for Twilio.

## Option 2: Manual Deploy (3-4 minutes)

```bash
# Set variables
export PROJECT_ID="your-project-id"
export OPENAI_API_KEY="sk-your-key"

# Enable APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com

# Deploy with optimized settings
gcloud run deploy opus-agent \
    --source . \
    --region us-central1 \
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
    --set-env-vars "ENV=production,PORT=8000,HOST=0.0.0.0,OPENAI_API_KEY=$OPENAI_API_KEY"
```

## Twilio Configuration 📞

After deployment, you'll get a service URL like: `https://opus-agent-xyz-uc.a.run.app`

### Configure Twilio Webhook:

1. **Go to Twilio Console** → Phone Numbers → Manage → Active numbers
2. **Select your phone number**
3. **Set Webhook URL to:** `https://your-service-url.run.app/twilio-agent`
4. **Set HTTP method to:** POST
5. **Enable Media Streams** in your Twilio configuration

### Test WebSocket Connection:

```bash
# Get your service URL
SERVICE_URL=$(gcloud run services describe opus-agent --region us-central1 --format "value(status.url)")

# Test health endpoint
curl $SERVICE_URL/health

# Test WebSocket endpoint (should return upgrade response)
curl -H "Connection: Upgrade" -H "Upgrade: websocket" $SERVICE_URL/twilio-agent
```

## Optimized Configuration Explained

Your deployment uses these **2024 best practices** for WebSocket/Twilio:

- **Memory: 4Gi** - Handles audio processing efficiently
- **CPU: 2 cores + boost** - Fast real-time processing
- **Timeout: 3600s** - Supports long conversations
- **Concurrency: 100** - Optimal for WebSocket connections
- **Min instances: 1** - Reduces cold starts
- **Gen2 execution** - Better performance and networking

## Monitoring & Troubleshooting 📊

```bash
# View logs
gcloud run services logs read opus-agent --region us-central1 --follow

# View metrics
gcloud run services describe opus-agent --region us-central1

# Scale if needed
gcloud run services update opus-agent --max-instances 50 --region us-central1
```

## Cost Optimization 💰

**Expected costs for moderate usage:**
- **Idle:** ~$5-10/month (min instances)
- **Active:** ~$0.10-0.20 per 1000 requests
- **Data transfer:** ~$0.12/GB

**Tips to reduce costs:**
- Set `--min-instances 0` for development
- Use `--max-instances 10` for cost limits
- Monitor usage in Cloud Console

## Production Checklist ✅

Before going live:

- [ ] Test health endpoint
- [ ] Test Twilio WebSocket connection
- [ ] Configure custom domain (optional)
- [ ] Set up monitoring alerts
- [ ] Enable Cloud Armor for DDoS protection
- [ ] Use Secret Manager for API keys (production)

## Advanced: Custom Domain Setup

```bash
# Map custom domain
gcloud run domain-mappings create \
    --service opus-agent \
    --domain your-domain.com \
    --region us-central1
```

## Troubleshooting Common Issues

### WebSocket Connection Fails
```bash
# Check service status
gcloud run services describe opus-agent --region us-central1

# Check recent logs
gcloud run services logs read opus-agent --region us-central1 --limit 50
```

### High Latency
- Increase CPU: `--cpu 4`
- Enable CPU boost: `--cpu-boost`
- Reduce concurrency: `--concurrency 50`

### Scaling Issues
- Increase max instances: `--max-instances 50`
- Set min instances: `--min-instances 2`

## Quick Commands Reference

```bash
# View service URL
gcloud run services describe opus-agent --region us-central1 --format "value(status.url)"

# Update environment variables
gcloud run services update opus-agent --set-env-vars "NEW_VAR=value" --region us-central1

# Scale service
gcloud run services update opus-agent --concurrency 200 --max-instances 30 --region us-central1

# Delete service
gcloud run services delete opus-agent --region us-central1
```

---

**🎉 Congratulations!** Your Opus server is now live and ready to handle Twilio connections with optimal WebSocket performance.

**Questions?** Check the detailed `gcp-setup.md` for comprehensive documentation.