# Lago Billing Integration — Autonomyx LLM Gateway

## Architecture

```
LiteLLM Proxy
  ├── Postgres (litellm-db)     ← operational spend logs, virtual key budgets
  └── Lago (via callback)       ← metered billing, invoicing, customer plans
```

Dual-track: LiteLLM continues using its own Postgres for real-time budget enforcement and
spend logs. Every completed LLM call also fires a usage event to Lago for metered billing,
invoice generation, and customer-facing cost reports.

---

## Step 1 — Deploy Lago on Coolify

Add to your Coolify stack. Lago requires: API server, worker, clock, Redis, Postgres (separate DB).

### docker-compose addition (append to existing Coolify compose)

```yaml
  # ── Lago API ──────────────────────────────
  lago-api:
    image: getlago/api:latest
    container_name: autonomyx-lago-api
    restart: always
    networks:
      - coolify
    depends_on:
      - lago-db
      - lago-redis
    environment:
      - LAGO_API_URL=https://billing.openautonomyx.com
      - DATABASE_URL=postgresql://lago:lago_pass@lago-db:5432/lago
      - REDIS_URL=redis://lago-redis:6379
      - SECRET_KEY_BASE=${LAGO_SECRET_KEY_BASE}
      - ENCRYPTION_PRIMARY_KEY=${LAGO_ENCRYPTION_PRIMARY_KEY}
      - ENCRYPTION_DETERMINISTIC_KEY=${LAGO_ENCRYPTION_DETERMINISTIC_KEY}
      - ENCRYPTION_KEY_DERIVATION_SALT=${LAGO_ENCRYPTION_KEY_DERIVATION_SALT}
      - LAGO_FRONT_URL=https://billing.openautonomyx.com
      - RAILS_ENV=production
      - LAGO_DISABLE_SIGNUP=false
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.lago.rule=Host(`billing.openautonomyx.com`)"
      - "traefik.http.routers.lago.entrypoints=https"
      - "traefik.http.routers.lago.tls.certresolver=letsencrypt"
      - "traefik.http.services.lago.loadbalancer.server.port=3000"

  lago-worker:
    image: getlago/api:latest
    container_name: autonomyx-lago-worker
    restart: always
    networks:
      - coolify
    depends_on:
      - lago-api
    environment:
      - DATABASE_URL=postgresql://lago:lago_pass@lago-db:5432/lago
      - REDIS_URL=redis://lago-redis:6379
      - SECRET_KEY_BASE=${LAGO_SECRET_KEY_BASE}
      - RAILS_ENV=production
    command: ["bundle", "exec", "sidekiq"]

  lago-clock:
    image: getlago/api:latest
    container_name: autonomyx-lago-clock
    restart: always
    networks:
      - coolify
    depends_on:
      - lago-api
    environment:
      - DATABASE_URL=postgresql://lago:lago_pass@lago-db:5432/lago
      - REDIS_URL=redis://lago-redis:6379
      - SECRET_KEY_BASE=${LAGO_SECRET_KEY_BASE}
      - RAILS_ENV=production
    command: ["bundle", "exec", "clockwork", "clock.rb"]

  lago-front:
    image: getlago/front:latest
    container_name: autonomyx-lago-front
    restart: always
    networks:
      - coolify
    environment:
      - API_URL=https://billing.openautonomyx.com
      - APP_ENV=production
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.lago-ui.rule=Host(`billing-ui.openautonomyx.com`)"
      - "traefik.http.routers.lago-ui.entrypoints=https"
      - "traefik.http.routers.lago-ui.tls.certresolver=letsencrypt"
      - "traefik.http.services.lago-ui.loadbalancer.server.port=80"

  lago-db:
    image: postgres:15-alpine
    container_name: autonomyx-lago-db
    restart: always
    networks:
      - coolify
    environment:
      - POSTGRES_USER=lago
      - POSTGRES_PASSWORD=${LAGO_DB_PASSWORD:-lago_pass}
      - POSTGRES_DB=lago
    volumes:
      - lago-db-data:/var/lib/postgresql/data

  lago-redis:
    image: redis:7-alpine
    container_name: autonomyx-lago-redis
    restart: always
    networks:
      - coolify
    volumes:
      - lago-redis-data:/data
```

Add to the `volumes:` block:
```yaml
  lago-db-data:
  lago-redis-data:
```

---

## Step 2 — Lago env vars (add to .env.example)

```
# Lago Billing
LAGO_API_URL=https://billing.openautonomyx.com
LAGO_API_KEY=YOUR_LAGO_API_KEY_HERE         # from Lago UI → Developers → API Keys
LAGO_SECRET_KEY_BASE=YOUR_64_CHAR_SECRET
LAGO_ENCRYPTION_PRIMARY_KEY=YOUR_32_CHAR_KEY
LAGO_ENCRYPTION_DETERMINISTIC_KEY=YOUR_32_CHAR_KEY
LAGO_ENCRYPTION_KEY_DERIVATION_SALT=YOUR_32_CHAR_SALT
LAGO_DB_PASSWORD=lago_pass
```

Generate secrets:
```bash
openssl rand -hex 32  # run 4 times for each key above
```

---

## Step 3 — Wire LiteLLM → Lago via Custom Callback

LiteLLM supports custom success callbacks. Add a callback file to the LiteLLM container.

### `lago_callback.py`

```python
import os
import httpx
from datetime import datetime, timezone
from litellm.integrations.custom_logger import CustomLogger

LAGO_API_URL = os.environ.get("LAGO_API_URL", "https://billing.openautonomyx.com")
LAGO_API_KEY = os.environ.get("LAGO_API_KEY", "")

BILLABLE_METRIC_CODES = {
    "input_tokens":  "llm_input_tokens",   # create these in Lago UI
    "output_tokens": "llm_output_tokens",
    "requests":      "llm_requests",
}

class LagoCallback(CustomLogger):
    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            usage = response_obj.get("usage", {})
            input_tokens  = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            model         = response_obj.get("model", "unknown")
            # Use virtual key alias as Lago external_customer_id
            key_alias = kwargs.get("metadata", {}).get("user_api_key_alias", "default")

            timestamp = datetime.now(timezone.utc).isoformat()
            events = [
                {
                    "transaction_id": f"{response_obj.get('id','')}-input",
                    "external_customer_id": key_alias,
                    "code": BILLABLE_METRIC_CODES["input_tokens"],
                    "timestamp": timestamp,
                    "properties": {"model": model, "tokens": input_tokens},
                },
                {
                    "transaction_id": f"{response_obj.get('id','')}-output",
                    "external_customer_id": key_alias,
                    "code": BILLABLE_METRIC_CODES["output_tokens"],
                    "timestamp": timestamp,
                    "properties": {"model": model, "tokens": output_tokens},
                },
                {
                    "transaction_id": f"{response_obj.get('id','')}-req",
                    "external_customer_id": key_alias,
                    "code": BILLABLE_METRIC_CODES["requests"],
                    "timestamp": timestamp,
                    "properties": {"model": model},
                },
            ]
            for event in events:
                httpx.post(
                    f"{LAGO_API_URL}/api/v1/events",
                    json={"event": event},
                    headers={"Authorization": f"Bearer {LAGO_API_KEY}"},
                    timeout=5,
                )
        except Exception as e:
            print(f"[LagoCallback] Failed to send event: {e}")

lago_logger = LagoCallback()
```

### Mount in docker-compose

```yaml
  litellm:
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./lago_callback.py:/app/lago_callback.py:ro   # ADD THIS
```

### Register in config.yaml

```yaml
litellm_settings:
  success_callback: ["lago_callback.LagoCallback"]
  custom_logger_compatible_callbacks: ["lago_callback.LagoCallback"]
```

---

## Step 4 — Lago Setup (UI)

After deploying, open `https://billing-ui.openautonomyx.com`:

1. **Create Billable Metrics** (Metering → Billable Metrics → New):
   - `llm_input_tokens` — Aggregation: SUM, Field: `tokens`
   - `llm_output_tokens` — Aggregation: SUM, Field: `tokens`
   - `llm_requests` — Aggregation: COUNT

2. **Create Plans** (Plans → New):
   - E.g. "Pay-as-you-go": $0.002 per 1K input tokens, $0.006 per 1K output tokens

3. **Create Customers** — one per LiteLLM virtual key alias
   - External Customer ID = LiteLLM `key_alias` (e.g. `langflow-prod`, `autonomyx-mcp-prod`)

4. **Assign Plans** to customers → Lago handles invoicing automatically

---

## Step 5 — Verify dual-track billing

```bash
# LiteLLM Postgres spend (operational)
curl http://localhost:4000/spend/logs?limit=5 \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" | jq '.[] | {model, spend, total_tokens}'

# Lago usage events (billing)
curl https://billing.openautonomyx.com/api/v1/events?external_customer_id=langflow-prod \
  -H "Authorization: Bearer $LAGO_API_KEY" | jq '.events[] | {code, timestamp, properties}'

# Lago current period usage
curl https://billing.openautonomyx.com/api/v1/customers/langflow-prod/current_usage \
  -H "Authorization: Bearer $LAGO_API_KEY" | jq '.customer_usage.charges_usage[]'
```

---

## Dual-Track Summary

| Concern | LiteLLM Postgres | Lago |
|---|---|---|
| Real-time budget enforcement | ✅ | ❌ |
| Per-key spend logs | ✅ | ✅ |
| Invoice generation | ❌ | ✅ |
| Customer billing plans | ❌ | ✅ |
| Metered pricing tiers | ❌ | ✅ |
| Grafana dashboards | ✅ (via Prometheus) | ❌ |
| Source of truth for ops | ✅ | ❌ |
| Source of truth for finance | ❌ | ✅ |
