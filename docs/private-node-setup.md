# Private Node Setup

Deploy your own dedicated Autonomyx Model Gateway on a single VPS.
Your data never leaves your infrastructure.

## What you get

- All local models running on your hardware
- Zero shared compute with other customers
- DPDP 2023 Data Processing Agreement signable
- Auth, billing, and tracing via Autonomyx operator infra (isolated per your tenant)

## What you need

- A VPS with minimum 16GB RAM (32GB recommended, 96GB for full stack)
- Ubuntu 22.04 or 24.04
- Docker + Docker Compose
- Your onboarding credentials from Autonomyx (provided after sign-up)

---

## Step 1 — Get your credentials

Autonomyx provides during onboarding:

```
LITELLM_MASTER_KEY    → your gateway master key
LANGFLOW_VIRTUAL_KEY  → for spend tracking on Langflow flows
LANGFUSE_PUBLIC_KEY   → traces go to your org on Autonomyx Langfuse
LANGFUSE_SECRET_KEY   → paired with public key
```

---

## Step 2 — Deploy

```bash
# Download the deployment files
curl -O https://raw.githubusercontent.com/openautonomyx/autonomyx-model-gateway/main/docker-compose.private-node.yml
curl -O https://raw.githubusercontent.com/openautonomyx/autonomyx-model-gateway/main/.env.private-node

# Fill in your credentials
nano .env.private-node
```

Set these values in `.env.private-node`:

```bash
# From Autonomyx onboarding
LITELLM_MASTER_KEY=sk-autonomyx-YOUR_KEY
LANGFLOW_VIRTUAL_KEY=sk-autonomyx-YOUR_VIRTUAL_KEY
LANGFUSE_PUBLIC_KEY=pk-lf-YOUR_KEY
LANGFUSE_SECRET_KEY=sk-lf-YOUR_KEY

# Generate yourself
POSTGRES_PASSWORD=$(openssl rand -hex 16)
GRAFANA_ADMIN_PASSWORD=$(openssl rand -hex 16)
LANGFLOW_SECRET_KEY=$(openssl rand -hex 32)
LANGFLOW_DB_PASSWORD=$(openssl rand -hex 16)
LANGFLOW_ADMIN_PASSWORD=$(openssl rand -hex 16)

# Set based on your VPS RAM (see table below)
OLLAMA_MEM_LIMIT=20g
OLLAMA_MAX_LOADED_MODELS=2
```

**RAM tier guide:**

| Your VPS RAM | `OLLAMA_MEM_LIMIT` | `MAX_LOADED_MODELS` | Models available |
|---|---|---|---|
| 16GB | `10g` | `1` | 7B/8B only |
| 32GB | `20g` | `2` | 14B always-on |
| 64GB | `45g` | `3` | 32B always-on |
| 96GB | `70g` | `4` | Full stack |

---

## Step 3 — Start services

```bash
docker compose -f docker-compose.private-node.yml --env-file .env.private-node up -d
```

Services starting:
- `private-litellm` on port 4000
- `private-ollama` on port 11434 (auto-pulls models based on RAM)
- `private-prometheus` on port 9090
- `private-grafana` on port 3001
- `private-langflow` on port 7860
- `private-playwright` on port 8400

---

## Step 4 — Wait for models

Ollama auto-detects your RAM and pulls appropriate models. Monitor:

```bash
# Watch model downloads
docker logs private-ollama -f

# Check loaded models
docker exec private-ollama ollama ps
```

Time estimates:
- 16GB tier (~14GB models): 20–30 min
- 32GB tier (~30GB models): 40–60 min
- 64GB tier (~45GB models): 60–90 min
- 96GB tier (~58GB models): 90–120 min

---

## Step 5 — Test

```bash
# Health check
curl http://localhost:4000/health \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"

# First model call
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/qwen2.5:14b",
    "messages": [{"role": "user", "content": "Hello from my private node"}]
  }'
```

---

## Step 6 — Import flows

```bash
# Import Autonomyx pre-built flows
for flow in code-review policy-creator policy-review web-scraper; do
  curl -O "https://raw.githubusercontent.com/openautonomyx/autonomyx-model-gateway/main/flows/${flow}.json"
  curl -X POST http://localhost:7860/api/v1/flows/ \
    -H "Content-Type: application/json" \
    -d @${flow}.json
  echo "Imported: $flow"
done
```

---

## Using your private node

Your node exposes the same OpenAI-compatible API:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://your-vps-ip:4000/v1",
    api_key="sk-autonomyx-your-master-key",
)

response = client.chat.completions.create(
    model="ollama/qwen2.5:14b",
    messages=[{"role": "user", "content": "Review this contract"}],
)
```

---

## Monitoring

- Grafana: `http://your-vps-ip:3001` (admin / your GRAFANA_ADMIN_PASSWORD)
- Import dashboard ID `17587` for LiteLLM metrics

---

## Updates

Pull latest images:
```bash
docker compose -f docker-compose.private-node.yml pull
docker compose -f docker-compose.private-node.yml up -d
```

---

## Support

- Email: chinmay@openautonomyx.com
- Book a call: cal.com/thefractionalpm
