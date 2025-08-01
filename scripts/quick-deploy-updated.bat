@echo off
REM Updated Quick GCP Cloud Run Deployment for Opus Agent (2024) - Windows Version
REM Usage: quick-deploy-updated.bat <project-id> [openai-api-key]

setlocal enabledelayedexpansion

REM Check arguments
if "%~1"=="" (
    echo Usage: %0 ^<project-id^> [openai-api-key]
    echo Example: %0 my-gcp-project sk-...
    exit /b 1
)

set PROJECT_ID=%~1
set OPENAI_API_KEY=%~2

if "%OPENAI_API_KEY%"=="" (
    if "%OPENAI_API_KEY%"=="" (
        echo Error: OpenAI API key not provided
        echo Either pass it as second argument or set OPENAI_API_KEY environment variable
        exit /b 1
    )
)

set SERVICE_NAME=opus-agent
set REGION=us-central1

echo 🚀 Quick deploying Opus Agent to Google Cloud Run...
echo 📋 Project: %PROJECT_ID%
echo 🌍 Region: %REGION%
echo 🔑 OpenAI API Key: %OPENAI_API_KEY:~0,10%...

REM Set project
gcloud config set project %PROJECT_ID%

REM Enable APIs
echo 🔧 Enabling required APIs...
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com --quiet

REM Build and deploy with optimized settings for WebSockets
echo 🏗️ Building and deploying with WebSocket optimization...
gcloud run deploy %SERVICE_NAME% ^
    --source . ^
    --region %REGION% ^
    --platform managed ^
    --allow-unauthenticated ^
    --port 8000 ^
    --memory 4Gi ^
    --cpu 2 ^
    --timeout 3600 ^
    --concurrency 100 ^
    --max-instances 20 ^
    --min-instances 1 ^
    --cpu-boost ^
    --execution-environment gen2 ^
    --set-env-vars "ENV=production,PORT=8000,HOST=0.0.0.0,OPENAI_API_KEY=%OPENAI_API_KEY%" ^
    --quiet

REM Get service URL
for /f "tokens=*" %%i in ('gcloud run services describe %SERVICE_NAME% --region %REGION% --format "value(status.url)"') do set SERVICE_URL=%%i

echo.
echo ✅ Deployment completed successfully!
echo 🌐 Service URL: %SERVICE_URL%
echo 🔗 Twilio WebSocket endpoint: %SERVICE_URL%/twilio-agent
echo 🔗 AudioCodes endpoint: %SERVICE_URL%/voice-bot
echo 💚 Health check: %SERVICE_URL%/health
echo.
echo 📝 Next steps for Twilio integration:
echo 1. Test the health endpoint: curl %SERVICE_URL%/health
echo 2. Update your Twilio webhook URL to: %SERVICE_URL%/twilio-agent
echo 3. Configure Twilio Media Streams to use WebSocket URL: %SERVICE_URL%/twilio-agent
echo.
echo 📊 Monitoring:
echo View logs: gcloud run services logs read %SERVICE_NAME% --region %REGION% --follow
echo View metrics: https://console.cloud.google.com/run/detail/%REGION%/%SERVICE_NAME%
echo.
echo 💡 Twilio Configuration Tips:
echo - Ensure your Twilio phone number webhook points to: %SERVICE_URL%/twilio-agent
echo - Use WSS (secure WebSocket) for production: wss://%SERVICE_URL:https://=%/twilio-agent
echo - Set timeout to maximum (3600s) for long conversations 