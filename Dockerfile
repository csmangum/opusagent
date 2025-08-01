FROM python:3.11-slim

# Install system dependencies for audio processing and WebSocket support
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libasound2-dev \
    portaudio19-dev \
    libffi-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port
EXPOSE 8000

# Use the correct entry point for your server
CMD ["python", "run_opus_server.py", "--host", "0.0.0.0", "--port", "8000"] 