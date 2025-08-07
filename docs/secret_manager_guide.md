# Google Secret Manager Integration Guide

This guide explains how to use Google Secret Manager with your Opus Agent application for secure credential management.

## Overview

Google Secret Manager provides a secure way to store and manage sensitive information like API keys, database passwords, and other credentials. Instead of hardcoding these values in your application or environment variables, Secret Manager encrypts them and provides secure access.

## Benefits

- 🔐 **Security**: Secrets are encrypted at rest and in transit
- 🔄 **Versioning**: Track changes to secrets over time
- 👥 **Access Control**: Fine-grained IAM permissions
- 🔍 **Audit Logging**: Track who accessed what and when
- 🚀 **Integration**: Native integration with Cloud Run

## Setup Instructions

### 1. Prerequisites

Ensure you have:
- Google Cloud SDK installed and authenticated
- A Google Cloud project with billing enabled
- Appropriate IAM permissions (Secret Manager Admin)

### 2. Run the Setup Script

```bash
# Navigate to your project directory
cd /path/to/opusagent

# Run the setup script
python scripts/setup_secret_manager.py --project-id YOUR_PROJECT_ID
```

The script will:
- Enable required APIs
- Create secrets for your application
- Grant necessary permissions
- Guide you through entering your API keys

### 3. Manual Setup (Alternative)

If you prefer to set up manually:

```bash
# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com --project=YOUR_PROJECT_ID

# Create secrets
gcloud secrets create openai-api-key --project=YOUR_PROJECT_ID
gcloud secrets create anthropic-api-key --project=YOUR_PROJECT_ID
gcloud secrets create redis-url --project=YOUR_PROJECT_ID

# Add secret versions (replace with your actual values)
echo "sk-your-openai-key" | gcloud secrets versions add openai-api-key --data-file=- --project=YOUR_PROJECT_ID
echo "sk-ant-your-anthropic-key" | gcloud secrets versions add anthropic-api-key --data-file=- --project=YOUR_PROJECT_ID
echo "redis://your-redis-url" | gcloud secrets versions add redis-url --data-file=- --project=YOUR_PROJECT_ID

# Grant permissions to Cloud Run service account
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:YOUR_PROJECT_ID@appspot.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## Configuration

### Cloud Build Configuration

Your `cloudbuild.yaml` is already configured to use Secret Manager:

```yaml
- '--set-secrets=OPENAI_API_KEY=openai-api-key:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,REDIS_URL=redis-url:latest'
```

This maps environment variables to Secret Manager secrets:
- `OPENAI_API_KEY` → `openai-api-key:latest`
- `ANTHROPIC_API_KEY` → `anthropic-api-key:latest`
- `REDIS_URL` → `redis-url:latest`

### Application Code

Your application code doesn't need to change! The secrets are automatically available as environment variables:

```python
import os

# These will be automatically populated from Secret Manager
openai_api_key = os.getenv('OPENAI_API_KEY')
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
redis_url = os.getenv('REDIS_URL')
```

## Managing Secrets

### View All Secrets

```bash
gcloud secrets list --project=YOUR_PROJECT_ID
```

### View Secret Metadata

```bash
gcloud secrets describe SECRET_NAME --project=YOUR_PROJECT_ID
```

### Update a Secret

```bash
# Method 1: From file
echo "new-secret-value" > secret.txt
gcloud secrets versions add SECRET_NAME --data-file=secret.txt --project=YOUR_PROJECT_ID

# Method 2: From stdin
echo "new-secret-value" | gcloud secrets versions add SECRET_NAME --data-file=- --project=YOUR_PROJECT_ID
```

### Access Secret Value

```bash
gcloud secrets versions access latest --secret=SECRET_NAME --project=YOUR_PROJECT_ID
```

## Security Best Practices

### 1. Principle of Least Privilege

Only grant the minimum necessary permissions:
- **Secret Manager Secret Accessor**: For applications to read secrets
- **Secret Manager Admin**: For managing secrets (admin only)

### 2. Secret Rotation

Regularly rotate your secrets:

```bash
# Create a new version
echo "new-api-key" | gcloud secrets versions add openai-api-key --data-file=- --project=YOUR_PROJECT_ID

# Your application will automatically use the latest version
```

### 3. Audit Logging

Monitor secret access:

```bash
# View recent access logs
gcloud logging read "resource.type=secretmanager.googleapis.com/Secret" --project=YOUR_PROJECT_ID
```

### 4. Environment Separation

Use different secrets for different environments:

```bash
# Development secrets
gcloud secrets create openai-api-key-dev --project=YOUR_PROJECT_ID

# Production secrets  
gcloud secrets create openai-api-key-prod --project=YOUR_PROJECT_ID
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```
   Error: Permission denied on secret
   ```
   **Solution**: Grant Secret Manager Secret Accessor role to your Cloud Run service account

2. **Secret Not Found**
   ```
   Error: Secret not found
   ```
   **Solution**: Verify the secret name and project ID

3. **API Not Enabled**
   ```
   Error: API not enabled
   ```
   **Solution**: Enable Secret Manager API

### Debugging Commands

```bash
# Check if APIs are enabled
gcloud services list --enabled --project=YOUR_PROJECT_ID | grep secretmanager

# Check service account permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID --flatten="bindings[].members" --filter="bindings.members:YOUR_PROJECT_ID@appspot.gserviceaccount.com"

# Test secret access
gcloud secrets versions access latest --secret=openai-api-key --project=YOUR_PROJECT_ID
```

## Cost Considerations

Secret Manager pricing:
- **Storage**: $0.06 per 10,000 secret versions per month
- **Access**: $0.03 per 10,000 secret accesses per month
- **Replication**: Free for automatic replication

For typical usage, costs are minimal (usually < $1/month).

## Migration from Environment Variables

If you're migrating from environment variables:

1. **Create secrets** for your existing environment variables
2. **Update cloudbuild.yaml** to use `--set-secrets` instead of `--set-env-vars`
3. **Deploy** your application
4. **Remove** environment variables from your configuration

## Additional Resources

- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Cloud Run Secret Integration](https://cloud.google.com/run/docs/configuring/secrets)
- [IAM Best Practices](https://cloud.google.com/iam/docs/best-practices)
- [Secret Manager Pricing](https://cloud.google.com/secret-manager/pricing)
