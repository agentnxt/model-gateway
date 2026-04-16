# docker-compose Template

Two variants — Coolify and Generic Docker. Generate the correct one based on deploy target.

---

## VARIANT A: Coolify (vps.agnxxt.com)

```yaml
version: "3.9"

networks:
  coolify:
    external: true

volumes:
  litellm-db-data:
  prometheus-data:
  grafana-data:

services:

  litellm:
    image: ghcr.io/berriai/litellm:main-stable
    container_name: autonomyx-litellm
    restart: always
    networks:
      - coolify
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - STORE_MODEL_IN_DB=True
      - LITELLM_UI_USERNAME=${LITELLM_UI_USERNAME}
      - LITELLM_UI_PASSWORD=${LITELLM_UI_PASSWORD}
      # Provider keys (only set the ones you use)
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - AZURE_API_KEY=${AZURE_API_KEY}
      - AZURE_API_BASE=${AZURE_API_BASE}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=${AWS_REGION}
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - FIREWORKS_API_KEY=${FIREWORKS_API_KEY}
      - TOGETHER_API_KEY=${TOGETHER_API_KEY}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - HF_TOKEN=${HF_TOKEN}
    volumes:
      - ./config.yaml:/app/config.yaml:ro
    command: ["--config", "/app/config.yaml", "--port", "4000", "--num_workers", "8"]
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.litellm.rule=Host(`llm.openautonomyx.com`)"
      - "traefik.http.routers.litellm.entrypoints=https"
      - "traefik.http.routers.litellm.tls.certresolver=letsencrypt"
      - "traefik.http.services.litellm.loadbalancer.server.port=4000"
    depends_on:
      - litellm-db
    extra_hosts:
      - "host.docker.internal:host-gateway"

  litellm-db:
    image: postgres:15-alpine
    container_name: autonomyx-litellm-db
    restart: always
    networks:
      - coolify
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-litellm}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-litellm_pass}
      - POSTGRES_DB=${POSTGRES_DB:-litellm}
    volumes:
      - litellm-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U litellm"]
      interval: 10s
      timeout: 5s
      retries: 5

  prometheus:
    image: prom/prometheus:latest
    container_name: autonomyx-prometheus
    restart: always
    networks:
      - coolify
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=30d"

  grafana:
    image: grafana/grafana:latest
    container_name: autonomyx-grafana
    restart: always
    networks:
      - coolify
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-autonomyx}
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.grafana.rule=Host(`metrics.openautonomyx.com`)"
      - "traefik.http.routers.grafana.entrypoints=https"
      - "traefik.http.routers.grafana.tls.certresolver=letsencrypt"
      - "traefik.http.services.grafana.loadbalancer.server.port=3000"
    depends_on:
      - prometheus
```

---

## VARIANT B: Generic Docker

```yaml
version: "3.9"

volumes:
  litellm-db-data:
  prometheus-data:
  grafana-data:

services:

  litellm:
    image: ghcr.io/berriai/litellm:main-stable
    container_name: autonomyx-litellm
    restart: always
    ports:
      - "4000:4000"
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - STORE_MODEL_IN_DB=True
      - LITELLM_UI_USERNAME=${LITELLM_UI_USERNAME}
      - LITELLM_UI_PASSWORD=${LITELLM_UI_PASSWORD}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - AZURE_API_KEY=${AZURE_API_KEY}
      - AZURE_API_BASE=${AZURE_API_BASE}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=${AWS_REGION}
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - FIREWORKS_API_KEY=${FIREWORKS_API_KEY}
      - TOGETHER_API_KEY=${TOGETHER_API_KEY}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - HF_TOKEN=${HF_TOKEN}
    volumes:
      - ./config.yaml:/app/config.yaml:ro
    command: ["--config", "/app/config.yaml", "--port", "4000", "--num_workers", "8"]
    depends_on:
      litellm-db:
        condition: service_healthy
    extra_hosts:
      - "host.docker.internal:host-gateway"

  litellm-db:
    image: postgres:15-alpine
    container_name: autonomyx-litellm-db
    restart: always
    ports:
      - "5433:5432"
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-litellm}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-litellm_pass}
      - POSTGRES_DB=${POSTGRES_DB:-litellm}
    volumes:
      - litellm-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U litellm"]
      interval: 10s
      timeout: 5s
      retries: 5

  prometheus:
    image: prom/prometheus:latest
    container_name: autonomyx-prometheus
    restart: always
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus

  grafana:
    image: grafana/grafana:latest
    container_name: autonomyx-grafana
    restart: always
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-autonomyx}
    volumes:
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
```
