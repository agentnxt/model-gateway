# Autonomyx Playwright Scraper — Dockerfile
# Chromium only (650MB vs 2.1GB for all browsers)
# Non-root user for security
# shm_size must be set in docker-compose (256m minimum)

FROM python:3.12-slim AS deps

WORKDIR /app

# System deps for Chromium only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    libxshmfence1 libx11-6 libxext6 libxfixes3 libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium only (not Firefox + WebKit)
RUN playwright install chromium --with-deps

FROM deps AS app

WORKDIR /app

COPY scraper.py .

# Non-root user — prevents container escape attacks
RUN useradd -m scraper && chown -R scraper:scraper /app
USER scraper

EXPOSE 8400

CMD ["python", "scraper.py"]
