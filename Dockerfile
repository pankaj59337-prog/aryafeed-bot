FROM python:3.11-slim

# Install system dependencies (FFmpeg, fonts, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
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
RUN mkdir -p data/input data/output data/temp data/audio assets/fonts assets/music/bollywood assets/images/candid assets/images/used assets/images/categories/sexy assets/images/categories/baddie assets/images/categories/bestie assets/images/categories/romantic assets/images/categories/cinematic assets/images/categories/traditional assets/images/categories/broken assets/images/categories/aesthetic database

# Run bot
CMD ["python", "main.py"]
