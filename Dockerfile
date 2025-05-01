# Use official Python image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DISPLAY=host.docker.internal:0
ENV CHROME_BIN=/usr/bin/google-chrome

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    xauth \
    libxi6 \
    libgconf-2-4 \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libnspr4 \
    libnss3 \
    libxss1 \
    libxtst6 \
    libxkbcommon-x11-0 \
    libgbm-dev \
    libdrm2 \
    x11-utils \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Chromium and create Chrome symlink
RUN apt-get update && \
    apt-get install -y chromium chromium-driver && \
    ln -s /usr/bin/chromium /usr/bin/google-chrome && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/logs

# Copy project files
COPY . .

# Add Xvfb init script
RUN echo '#!/bin/bash\n\
Xvfb :99 -screen 0 1024x768x24 &\n\
export DISPLAY=:99\n\
exec "$@"' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "scraper.py"]