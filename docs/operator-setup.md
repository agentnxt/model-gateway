# Operator Setup

This guide deploys the full Autonomyx Model Gateway platform — two nodes, all services.
Time to complete: 2–3 hours (mostly waiting for model downloads).

## Prerequisites

- Two VPS instances: 96GB RAM + 48GB RAM (or one 96GB for testing)
- Ubuntu 22.04 or 24.04
- Docker + Docker Compose installed on both
- Coolify installed and running at `http://vps.agnxxt.com:8000`
- Domain with DNS access (for Traefik TLS)
- GitHub account with access to this repo

---

## Step 1 — DNS records

Point these subdomains to your 96GB node IP before starting:

```
llm.openautonomyx.com       → 96GB node
flows.openautonomyx.com     → 96GB node
metrics.openautonomyx.com   → 96GB node
mcp.openautonomyx.com       → 96GB node
```

Point these to your 48GB node:

```
traces.openautonomyx.com    → 48GB node
billing.openautonomyx.com   → 48GB node
billing-ui.openautonomyx.com → 48GB node
auth.openautonomyx.com      → 48GB node
```

---

## Step 2 — Clone repo on both nodes

```bash
git clone https://github.com/openautonomyx/autonomyx-model-gateway.git
cd autonomyx-model-gateway
```

---

## Step 3 — Configure environment

Copy and fill in the env file:

```bash
cp .env.example .env
```

Minimum required values:

```bash
# Generate a secure master key
LITELLM_MASTER_KEY=sk-autonomyx-$(openssl rand -hex 16)

# Postgres
POSTGRES_PASSWORD=$(openssl rand -hex 16)

# Langfuse
LANGFUSE_NEXTAUTH_SECRET=$(openssl rand -hex 32)
LANGFUSE_DB_PASSWORD=$(openssl rand -hex 16)

# Lago
LAGO_SECRET_KEY_BASE=$(openssl rand -hex 32)
LAGO_DB_PASSWORD=$(openssl rand -hex 16)

# Keycloak
KEYCLOAK_ADMIN_PASSWORD=$(openssl rand -hex 16)

# Langflow
LANGFLOW_SECRET_KEY=$(openssl rand -hex 32)
LANGFLOW_DB_PASSWORD=$(openssl rand -hex 16)
LANGFLOW_ADMIN_PASSWORD=$(openssl rand -hex 16)
LANGFLOW_VIRTUAL_KEY=sk-autonomyx-langflow-$(openssl rand -hex 8)

# SurrealDB Cloud (for RAG/Playwright)
SURREAL_URL=https://schemadb-06ehsj292ppah8kbsk9pmnjjbc.aws-aps1.surreal.cloud
SURREAL_USER=root
SURREAL_PASS=YOUR_SURREAL_PASSWORD

# Cloud provider keys (add only those you use)
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
# GROQ_API_KEY=
```

---

## Step 4 — Deploy 96GB node (inference)

```bash
# Start all inference services
docker compose -f docker-compose.yml up -d

# Verify all services are up
docker compose ps
```

Expected services running:
- `autonomyx-litellm` on port 4000
- `autonomyx-ollama` on port 11434
- `autonomyx-langflow` on port 7860
- `autonomyx-prometheus` on port 9090
- `autonomyx-grafana` on port 3000
- `autonomyx-playwright` on port 8400
- `autonomyx-classifier` on port 8100
- `autonomyx-translator` on port 8200

---

## Step 5 — Pull local models

```bash
docker exec autonomyx-ollama sh /ollama-pull.sh
```

This pulls the full Option C stack (~58GB). Takes 30–90 minutes depending on connection.

Monitor progress:
```bash
docker exec autonomyx-ollama ollama ps
```

---

## Step 6 — Deploy 48GB node (business logic)

On the 48GB node:

```bash
# Uses same .env file — copy it over
scp .env user@48gb-node:~/autonomyx-model-gateway/

# Start business logic services only
docker compose -f docker-compose.business.yml up -d
```

Expected services:
- `autonomyx-langfuse` on traces.openautonomyx.com
- `autonomyx-lago-api` on billing.openautonomyx.com
- `autonomyx-keycloak` on auth.openautonomyx.com
- `autonomyx-mailserver` on port 25/465/587

---

## Step 7 — Keycloak setup

```bash
# Create autonomyx realm
curl -X POST https://auth.openautonomyx.com/admin/realms \
  -H "Authorization: Bearer $(get_kc_token)" \
  -H "Content-Type: application/json" \
  -d '{"realm": "autonomyx", "enabled": true}'

# Create OIDC client for the gateway
curl -X POST https://auth.openautonomyx.com/admin/realms/autonomyx/clients \
  -H "Authorization: Bearer $(get_kc_token)" \
  -d '{"clientId": "autonomyx-gateway", "protocol": "openid-connect", "publicClient": false}'
```

See `references/keycloak-integration.md` for full setup commands.

---

## Step 8 — Lago billing setup

1. Open `https://billing-ui.openautonomyx.com`
2. Create three billable metrics:
   - `llm_input_tokens` — SUM aggregation on `input_tokens`
   - `llm_output_tokens` — SUM aggregation on `output_tokens`
   - `llm_requests` — COUNT aggregation
3. Create plans matching your pricing tiers (see `references/profitability.md`)

---

## Step 9 — Grafana setup

1. Open `https://metrics.openautonomyx.com`
2. Login: admin / `$GRAFANA_ADMIN_PASSWORD`
3. Add Prometheus datasource: `http://prometheus:9090`
4. Import dashboard ID `17587` (LiteLLM community dashboard)

---

## Step 10 — Import Langflow flows

```bash
# Import all pre-built flows
for flow in flows/*.json; do
  curl -X POST https://flows.openautonomyx.com/api/v1/flows/ \
    -H "Authorization: Bearer $LANGFLOW_API_KEY" \
    -H "Content-Type: application/json" \
    -d @$flow
  echo "Imported: $flow"
done
```

---

## Step 11 — Health check

```bash
# Gateway
curl https://llm.openautonomyx.com/health \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"

# Test a model call
curl https://llm.openautonomyx.com/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/qwen3:30b-a3b",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Playwright sidecar
curl http://localhost:8400/health

# Classifier sidecar
curl http://localhost:8100/health

# Translator sidecar
curl http://localhost:8200/health
```

---

## Onboard your first tenant

See [Tenant Onboarding](./tenant-onboarding.md).
