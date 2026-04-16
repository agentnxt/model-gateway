FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

COPY scraper_server.py .

RUN pip install --no-cache-dir \
        fastapi==0.111.0 \
        uvicorn==0.30.0 \
        httpx==0.27.0 \
        pydantic==2.7.0 \
    && useradd -m scraper \
    && chown -R scraper /app

USER scraper

EXPOSE 8400
CMD ["python", "scraper_server.py"]
