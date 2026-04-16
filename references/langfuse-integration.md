# Langfuse Integration & Multi-tenancy Audit — Autonomyx LLM Gateway

## Why Langfuse is day-one infrastructure, not optional

Without Langfuse you cannot:
- See which prompts fail and why → can't improve models
- Track latency per model per tenant → can't make SLA claims
- Collect human feedback → can't do RLHF or fine-tuning later
- Detect prompt injection, jailbreaks, cost anomalies → can't secure the platform
- Build evaluation datasets → can't run A/B tests between models

Langfuse is not observability. It is the **feedback loop that makes local models competitive.**
Without it, you are flying blind. With it, you can systematically close the gap vs cloud models
on your specific workloads.

---

## Complete multi-tenancy audit — with Langfuse added

| Layer | Isolated? | Mechanism | Notes |
|---|---|---|---|
| Auth (Keycloak) | ✅ Full | Group per tenant, OIDC scoped | Done |
| Billing (Lago) | ✅ Full | external_customer_id per tenant | Done |
| LiteLLM virtual keys | ✅ Full | Budget, rate limits, model access per key | Done |
| **Trace + prompt data (Langfuse)** | **✅ Full** | **Organisation per tenant, DB-level isolation** | **Add today** |
| LiteLLM spend logs (Postgres) | 🟡 Row-level | Separated by key_alias, shared DB | Add RLS |
| Prometheus metrics | 🟡 Label-level | Per model+key, shared instance | Add Grafana orgs |
| LiteLLM proxy process | ❌ Shared | Single process, all tenants | Acceptable |
| Ollama model inference | ❌ Shared | Single instance, all tenants | Acceptable |
| Prompt content at inference | ✅ Not stored | LiteLLM default — no logging | Langfuse captures it |

**Net verdict:** With Langfuse added, you have **full isolation on everything that matters** —
identity, billing, spend, and now prompt/trace data. The shared compute layer is the only gap,
and that is standard for any SaaS LLM provider including OpenAI.

**You can claim multi-tenancy today.** Be precise about what it means:
"Billing, access, and trace data are fully isolated per tenant. Compute is shared."

---

## docker-compose addition — Langfuse v3

```yaml
  langfuse-server:
    image: langfuse/langfuse:3
    container_name: autonomyx-langfuse
    restart: always
    networks:
      - coolify
    depends_on:
      langfuse-db:
        condition: service_healthy
      langfuse-redis:
        condition: service_started
    environment:
      - DATABASE_URL=postgresql://langfuse:${LANGFUSE_DB_PASSWORD}@langfuse-db:5432/langfuse
      - REDIS_HOST=langfuse-redis
      - REDIS_PORT=6379
      - NEXTAUTH_URL=https://traces.openautonomyx.com
      - NEXTAUTH_SECRET=${LANGFUSE_NEXTAUTH_SECRET}
      - SALT=${LANGFUSE_SALT}
      - ENCRYPTION_KEY=${LANGFUSE_ENCRYPTION_KEY}
      - LANGFUSE_ENABLE_EXPERIMENTAL_FEATURES=true
      # Keycloak OIDC SSO
      - AUTH_KEYCLOAK_CLIENT_ID=${LANGFUSE_KC_CLIENT_ID}
      - AUTH_KEYCLOAK_CLIENT_SECRET=${LANGFUSE_KC_CLIENT_SECRET}
      - AUTH_KEYCLOAK_ISSUER=https://auth.openautonomyx.com/realms/autonomyx
      # Disable public signup — admin creates orgs manually or via API
      - AUTH_DISABLE_SIGNUP=false
      - LANGFUSE_INIT_ORG_ID=${LANGFUSE_INIT_ORG_ID}
      - LANGFUSE_INIT_ORG_NAME=Autonomyx
      - LANGFUSE_INIT_PROJECT_ID=${LANGFUSE_INIT_PROJECT_ID}
      - LANGFUSE_INIT_PROJECT_NAME=platform-default
      - LANGFUSE_INIT_PROJECT_PUBLIC_KEY=${LANGFUSE_DEFAULT_PUBLIC_KEY}
      - LANGFUSE_INIT_PROJECT_SECRET_KEY=${LANGFUSE_DEFAULT_SECRET_KEY}
      - LANGFUSE_INIT_USER_EMAIL=${LANGFUSE_ADMIN_EMAIL}
      - LANGFUSE_INIT_USER_NAME=admin
      - LANGFUSE_INIT_USER_PASSWORD=${LANGFUSE_ADMIN_PASSWORD}
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.langfuse.rule=Host(`traces.openautonomyx.com`)"
      - "traefik.http.routers.langfuse.entrypoints=https"
      - "traefik.http.routers.langfuse.tls.certresolver=letsencrypt"
      - "traefik.http.services.langfuse.loadbalancer.server.port=3000"

  langfuse-db:
    image: postgres:15-alpine
    container_name: autonomyx-langfuse-db
    restart: always
    networks:
      - coolify
    environment:
      - POSTGRES_USER=langfuse
      - POSTGRES_PASSWORD=${LANGFUSE_DB_PASSWORD}
      - POSTGRES_DB=langfuse
    volumes:
      - langfuse-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U langfuse"]
      interval: 10s
      timeout: 5s
      retries: 5

  langfuse-redis:
    image: redis:7-alpine
    container_name: autonomyx-langfuse-redis
    restart: always
    networks:
      - coolify
    volumes:
      - langfuse-redis-data:/data
```

Add to `volumes:` block:
```yaml
  langfuse-db-data:
  langfuse-redis-data:
```

---

## Tenant isolation architecture — Langfuse

```
Langfuse hierarchy:
  Organisation (= Keycloak tenant group = Lago customer)
    └── Project: production
    └── Project: development
    └── Project: evaluation

One Organisation per tenant.
One set of API keys per Project.
DB-level isolation enforced by Langfuse — no cross-org data access possible.
```

### Provisioning a new tenant (Langfuse side)

When `kc_lago_sync.py` detects GROUP_CREATE in Keycloak, extend it to also
create a Langfuse organisation and project:

```python
import httpx

LANGFUSE_URL      = os.environ["LANGFUSE_URL"]          # https://traces.openautonomyx.com
LANGFUSE_ADMIN_KEY = os.environ["LANGFUSE_ADMIN_KEY"]   # admin API key

async def create_langfuse_org(group_id: str, group_name: str) -> dict:
    """
    Create Langfuse organisation + default project for a new tenant.
    Returns project API keys to store in Keycloak group attributes.
    """
    # 1. Create organisation
    r = await httpx.AsyncClient().post(
        f"{LANGFUSE_URL}/api/admin/organizations",
        headers={"x-langfuse-admin-api-key": LANGFUSE_ADMIN_KEY},
        json={"name": group_name, "id": group_id},
    )
    r.raise_for_status()

    # 2. Create default project in that org
    r2 = await httpx.AsyncClient().post(
        f"{LANGFUSE_URL}/api/admin/projects",
        headers={"x-langfuse-admin-api-key": LANGFUSE_ADMIN_KEY},
        json={
            "name": "production",
            "organizationId": group_id,
        },
    )
    r2.raise_for_status()
    project = r2.json()

    return {
        "public_key": project["publicKey"],
        "secret_key": project["secretKey"],
        "project_id": project["id"],
    }
```

Add this call to `kc_lago_sync.py` GROUP_CREATE handler alongside the Lago + LiteLLM calls.
Store the returned keys in Keycloak group attributes so they are available to the tenant's apps.

---

## Wiring LiteLLM → Langfuse (per-tenant routing)

### The challenge
LiteLLM's built-in Langfuse callback sends all traces to ONE Langfuse project.
For multi-tenancy, you need traces routed to each tenant's own project.

### Solution: custom success callback with per-key routing

Extend `lago_callback.py` to also route traces to Langfuse:

```python
# Add to lago_callback.py

import langfuse
from langfuse import Langfuse

# Cache of Langfuse clients per tenant key alias
_langfuse_clients: dict[str, Langfuse] = {}

def _get_langfuse_client(key_alias: str) -> Langfuse | None:
    """
    Returns a Langfuse client scoped to the tenant's project.
    Looks up project keys from an env var map or a DB table.
    LANGFUSE_KEYS env var format: "alias1:pubkey1:seckey1,alias2:pubkey2:seckey2"
    """
    if key_alias in _langfuse_clients:
        return _langfuse_clients[key_alias]

    # Load from env (for small deployments)
    # For larger: query Keycloak group attributes or a config table
    key_map_raw = os.environ.get("LANGFUSE_TENANT_KEYS", "")
    key_map = {}
    for entry in key_map_raw.split(","):
        parts = entry.strip().split(":")
        if len(parts) == 3:
            alias, pub, sec = parts
            key_map[alias] = (pub, sec)

    if key_alias not in key_map:
        # Fall back to default project if no tenant-specific key
        pub = os.environ.get("LANGFUSE_DEFAULT_PUBLIC_KEY")
        sec = os.environ.get("LANGFUSE_DEFAULT_SECRET_KEY")
        if not pub:
            return None
    else:
        pub, sec = key_map[key_alias]

    client = Langfuse(
        public_key=pub,
        secret_key=sec,
        host=os.environ.get("LANGFUSE_URL", "http://langfuse-server:3000"),
    )
    _langfuse_clients[key_alias] = client
    return client


class LagoCallback(CustomLogger):
    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        # ... existing Lago event code ...

        # ── Langfuse trace (per-tenant) ───────────────────────────────────
        try:
            key_alias = kwargs.get("metadata", {}).get("user_api_key_alias", "default")
            lf = _get_langfuse_client(key_alias)
            if lf:
                usage = response_obj.get("usage", {})
                lf.trace(
                    name=f"llm-{model}",
                    input=kwargs.get("messages", []),
                    output=response_obj.get("choices", [{}])[0]
                           .get("message", {}).get("content", ""),
                    metadata={
                        "model": model,
                        "key_alias": key_alias,
                        "latency_ms": int((end_time - start_time) * 1000),
                        "input_tokens": usage.get("prompt_tokens", 0),
                        "output_tokens": usage.get("completion_tokens", 0),
                    },
                    usage={
                        "input": usage.get("prompt_tokens", 0),
                        "output": usage.get("completion_tokens", 0),
                        "unit": "TOKENS",
                    },
                )
                lf.flush()
        except Exception as e:
            log.warning(f"Langfuse trace failed for {key_alias}: {e}")
```

### Env var for tenant key routing

```
# Format: alias:public_key:secret_key (comma-separated)
LANGFUSE_TENANT_KEYS=langflow-prod:pk-lf-xxx:sk-lf-xxx,autonomyx-mcp-prod:pk-lf-yyy:sk-lf-yyy

# Default project (catches tenants not yet provisioned)
LANGFUSE_DEFAULT_PUBLIC_KEY=pk-lf-default
LANGFUSE_DEFAULT_SECRET_KEY=sk-lf-default

LANGFUSE_URL=http://langfuse-server:3000
LANGFUSE_ADMIN_KEY=YOUR_LANGFUSE_ADMIN_KEY
```

---

## What Langfuse enables for model improvement

### Day 1 — observability
- Every LLM call traced: model, latency, tokens, cost, input, output
- Per-tenant dashboards at `traces.openautonomyx.com`
- Automatic anomaly detection: latency spikes, error rate, cost outliers

### Week 2 — evaluation
- Tag traces as good/bad (human feedback via Langfuse UI)
- Run LLM-as-judge evals: does the output answer the question?
- Compare Qwen3-30B vs cloud fallback on same inputs

### Month 2 — dataset curation
- Export failing traces as evaluation datasets
- Use to benchmark new model versions before promoting
- Build golden datasets per task type (code, reason, summarise)

### Month 3 — fine-tuning trigger
- Identify recurring failure patterns per task type
- Export failure traces as fine-tuning training data
- Fine-tune Qwen3-8B on your specific workload → closes gap vs 30B
- Validated improvement loop: trace → evaluate → fine-tune → re-evaluate

### The compounding moat
Every month of production traffic lets you fine-tune local models on your customers'
exact task distribution.

OpenAI, Anthropic, and Groq do NOT train on your API call data (opted out by default
in their ToS). But they also optimise their models for the average of millions of
diverse use cases — not your specific ones.

You can fine-tune Qwen3 on what your customers actually do:
- Indian legal document extraction
- Python + FastAPI codegen for SaaS backends  
- Hindi-English mixed-language prompts
- Domain-specific terminology your customers use daily

A model fine-tuned on 10,000 real production traces from your actual workload
outperforms a larger general model on that workload. Precision beats scale on
specialised tasks. That is the sustainable moat — not price.

---

## Updated multi-tenancy claim (what you can say)

```
✅ "Billing is fully isolated per tenant (Lago)"
✅ "Access and identity are fully isolated per tenant (Keycloak)"
✅ "Trace and prompt data is fully isolated per tenant (Langfuse organisations)"
✅ "API spend logs are isolated per virtual key (LiteLLM)"
✅ "Compute is shared (standard for SaaS LLM providers)"
✅ "Prompts routed to your Langfuse project, not visible to other tenants"

❌ Do not say: "Infrastructure is isolated" (shared Ollama + LiteLLM process)
❌ Do not say: "Data never leaves our servers" (it goes through shared compute)
✅ Do say: "Private deployment available for full infrastructure isolation"
```

---

## Env vars (add to .env.example)

```
# Langfuse
LANGFUSE_DB_PASSWORD=YOUR_LANGFUSE_DB_PASSWORD
LANGFUSE_NEXTAUTH_SECRET=YOUR_32_CHAR_SECRET
LANGFUSE_SALT=YOUR_32_CHAR_SALT
LANGFUSE_ENCRYPTION_KEY=YOUR_32_CHAR_HEX_KEY   # must be 64 hex chars
LANGFUSE_ADMIN_EMAIL=admin@openautonomyx.com
LANGFUSE_ADMIN_PASSWORD=YOUR_ADMIN_PASSWORD
LANGFUSE_ADMIN_KEY=YOUR_LANGFUSE_ADMIN_KEY
LANGFUSE_KC_CLIENT_ID=langfuse
LANGFUSE_KC_CLIENT_SECRET=YOUR_KC_CLIENT_SECRET
LANGFUSE_INIT_ORG_ID=autonomyx-platform
LANGFUSE_INIT_PROJECT_ID=platform-default
LANGFUSE_DEFAULT_PUBLIC_KEY=pk-lf-YOUR_KEY
LANGFUSE_DEFAULT_SECRET_KEY=sk-lf-YOUR_KEY
LANGFUSE_TENANT_KEYS=                           # populated by kc_lago_sync.py

# Generate secrets:
# LANGFUSE_NEXTAUTH_SECRET: openssl rand -base64 32
# LANGFUSE_SALT: openssl rand -base64 32
# LANGFUSE_ENCRYPTION_KEY: openssl rand -hex 32
```

---

## Output checklist additions

- [ ] Langfuse docker-compose services added (server + db + redis)
- [ ] `lago_callback.py` extended with per-tenant Langfuse trace routing
- [ ] `kc_lago_sync.py` extended with Langfuse org + project creation on GROUP_CREATE
- [ ] `LANGFUSE_TENANT_KEYS` env var documented and wired
- [ ] Langfuse Keycloak OIDC client created in realm setup commands
- [ ] Langfuse env vars in `.env.example`
- [ ] Multi-tenancy claims table documented for sales/marketing use
