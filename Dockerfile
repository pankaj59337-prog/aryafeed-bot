FROM python:3.11-slim

# Install system dependencies (FFmpeg, fonts, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tzdata \
    fonts-roboto \
    fonts-dejavu-core \
    libfreetype6-dev \
    libjpeg-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Ensure data directories exist
RUN mkdir -p data/input data/output data/temp data/audio data/sessions assets/fonts database assets/music/news assets/music/aura assets/music/national assets/images/categories/news

# Expose healthcheck and keepalive port
EXPOSE 10000

# Run AryaFeed 24/7 daemon
CMD ["python", "-u", "aryafeed_daemon.py"]
