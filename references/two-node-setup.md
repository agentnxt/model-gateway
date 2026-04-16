# Two-Node Infrastructure — Autonomyx LLM Gateway

## Architecture overview

```
96GB VPS (primary)                    48GB VPS (secondary)
──────────────────────────────────    ──────────────────────────────
LiteLLM proxy          (inference)    Langfuse + DB + Redis  (traces)
Ollama (4 models)      (inference)    Lago + DB + Redis      (billing)
Postgres (LiteLLM)     (spend logs)   Keycloak + DB          (auth)
Prometheus + Grafana   (metrics)      kc_lago_sync.py        (tenant sync)
Mailserver             (email)        Nginx/Traefik          (Coolify)
Classifier sidecar     (ML)
Translation sidecar    (ML)
```

**No Kubernetes. No Swarm.** Two independent Coolify-managed Docker Compose stacks.
Inter-node communication over private network or public IPs with TLS.

---

## Why not Kubernetes at 2 nodes

K8s control plane (etcd + api-server + scheduler + kubelet) consumes:
- ~3–4GB RAM per node just for control plane
- Significant ops overhead: certificates, RBAC, CRDs, network policies
- No functional benefit over two independent Docker Compose stacks at this scale

**When to reconsider K8s:** 5+ nodes, or when you need auto-scaling pods based on
real-time load. Neither applies today.

---

## Updated RAM maps

### 96GB primary — after migration

| Component | RAM | Notes |
|---|---|---|
| OS + system | 4GB | — |
| LiteLLM + Postgres (spend) | 3GB | — |
| Prometheus + Grafana | 2GB | — |
| Mailserver | 1GB | — |
| Classifier sidecar | 2GB | — |
| Translation sidecar | 4GB | IndicTrans2 + Opus-MT + fastText |
| Langflow | 3GB | — |
| **Infrastructure subtotal** | **~19GB** | (was ~30GB before migration) |
| Qwen3-30B-A3B (always-on) | 19GB | reason, agent, chat |
| Qwen2.5-Coder-32B (always-on) | 22GB | code |
| **Qwen2.5-14B (always-on, new)** | **9GB** | extract, structured output |
| Warm slot A (8B LRU) | ~6GB | chat overflow, summarise |
| Warm slot B (11B Vision LRU) | ~9GB | vision |
| **Total peak** | **~84GB** | |
| **Headroom** | **~12GB** | |

Three operating states:
- Idle (no warm slots): ~69GB — 27GB headroom
- Typical (one warm slot): ~75GB — 21GB headroom
- Peak (both warm slots): ~84GB — 12GB headroom

**Ollama hard cap: `mem_limit: 76g`** — evicts LRU before pushing into danger zone.

### 48GB secondary — after migration

| Component | RAM | Notes |
|---|---|---|
| OS + system | 4GB | — |
| Langfuse server | 2GB | — |
| Langfuse DB (Postgres) | 2GB | — |
| Langfuse Redis | 1GB | — |
| Lago API + worker + clock | 3GB | — |
| Lago front | 1GB | — |
| Lago DB (Postgres) | 2GB | — |
| Lago Redis | 1GB | — |
| Keycloak | 2GB | — |
| Keycloak DB (Postgres) | 1GB | — |
| kc_lago_sync.py | 0.5GB | — |
| Coolify + Traefik | 1GB | — |
| **Services subtotal** | **~20GB** | |
| **Available for other services** | **~28GB** | Liferay, SurrealDB, future |

28GB available for your other Coolify-managed apps — Liferay CE, SurrealDB, etc.

---

## Network configuration

### Option A — Public IPs with TLS (simplest, Coolify default)

Services on 48GB node expose endpoints over public HTTPS.
96GB node calls them by domain name.

```
96GB node calls:
  Langfuse:  https://traces.openautonomyx.com
  Lago:      https://billing.openautonomyx.com (internal API)
  Keycloak:  https://auth.openautonomyx.com
```

Downside: billing traffic traverses public internet. Fine for Lago API calls
(small payloads, TLS encrypted). Not acceptable for DB connections.

### Option B — Private network (recommended)

Most VPS providers (Hetzner, OVH, Contabo) offer private network / vSwitch
between servers in the same datacenter at no extra cost. Use this for DB connections.

```bash
# On both nodes — check if they're at the same provider/DC
# If yes, enable private network in provider dashboard
# Typically assigns 10.x.x.x addresses

# 96GB node connects to:
# Langfuse DB: postgresql://langfuse:pass@10.0.0.2:5432/langfuse
# Lago DB:     postgresql://lago:pass@10.0.0.2:5432/lago
# Keycloak:    http://10.0.0.2:8080 (internal, no TLS needed)
```

### Env var changes on 96GB node after migration

```bash
# Langfuse — point to 48GB node
LANGFUSE_URL=https://traces.openautonomyx.com
# or on private network:
LANGFUSE_URL=http://10.0.0.2:3000

# Lago — point to 48GB node
LAGO_API_URL=https://billing.openautonomyx.com
# or on private network:
LAGO_API_URL=http://10.0.0.2:3001

# Keycloak — point to 48GB node
KC_BASE_URL=https://auth.openautonomyx.com
# or on private network:
KC_BASE_URL=http://10.0.0.2:8080

# LiteLLM config.yaml — Keycloak still at auth.openautonomyx.com (public)
# No change needed — Keycloak is behind Traefik on 48GB node
```

---

## Migration procedure — zero downtime

### Phase 1: Deploy services on 48GB node (15 min)

```bash
# On 48GB node — deploy the migrated stack
cat > docker-compose-secondary.yml << 'EOF'
# Langfuse + Lago + Keycloak stack
# See individual service configs from:
#   references/langfuse-integration.md
#   references/lago-integration.md
#   references/keycloak-integration.md
EOF

docker compose -f docker-compose-secondary.yml up -d

# Verify all services healthy
docker compose -f docker-compose-secondary.yml ps
```

### Phase 2: Restore data on 48GB node (time depends on data size)

```bash
# Export from 96GB node
docker exec autonomyx-langfuse-db pg_dump -U langfuse langfuse > langfuse_backup.sql
docker exec autonomyx-lago-db pg_dump -U lago lago > lago_backup.sql
docker exec autonomyx-keycloak-db pg_dump -U keycloak keycloak > keycloak_backup.sql

# Copy to 48GB node
scp *_backup.sql user@48GB-VPS-IP:/tmp/

# Import on 48GB node
docker exec -i autonomyx-langfuse-db psql -U langfuse langfuse < /tmp/langfuse_backup.sql
docker exec -i autonomyx-lago-db psql -U lago lago < /tmp/lago_backup.sql
docker exec -i autonomyx-keycloak-db psql -U keycloak keycloak < /tmp/keycloak_backup.sql
```

### Phase 3: Update env vars on 96GB node and restart

```bash
# Update .env on 96GB node with new service URLs (see above)
# Then rolling restart — LiteLLM first
docker compose up -d litellm
docker compose up -d kc-lago-sync

# Verify connectivity
curl https://traces.openautonomyx.com/api/public/health
curl https://billing.openautonomyx.com/api/v1/analytics/mrr \
  -H "Authorization: Bearer $LAGO_API_KEY"
```

### Phase 4: Stop old services on 96GB node

```bash
# Only after Phase 3 is confirmed working
docker stop autonomyx-langfuse autonomyx-lago-api autonomyx-lago-db \
             autonomyx-lago-redis autonomyx-keycloak autonomyx-keycloak-db

# Remove from 96GB docker-compose.yml
# Free the RAM
```

### Phase 5: Pull and start Qwen2.5-14B on 96GB node

```bash
docker exec autonomyx-ollama ollama pull qwen2.5:14b
docker exec autonomyx-ollama ollama run qwen2.5:14b "Ready." --keepalive 24h
```

---

## Updated config.yaml — add Qwen2.5-14B

```yaml
  # ── ALWAYS-ON: Tier 2 extract + structured output specialist ────────────
  - model_name: ollama/qwen2.5:14b
    litellm_params:
      model: ollama/qwen2.5:14b
      api_base: "http://ollama:11434"
```

Update fallbacks:

```yaml
router_settings:
  fallbacks:
    # extract: Tier 2 14B always-on → cloud
    - ollama/qwen2.5:14b:
        - groq/llama3-70b
        - gpt-4o-mini

    # chat overflow: 8B → 14B (both local) → cloud
    - ollama/llama3.1:8b:
        - ollama/qwen2.5:14b
        - ollama/qwen3:30b-a3b
        - groq/llama3-70b
```

---

## Updated model_registry.json — Qwen2.5-14B entry

```json
{
  "alias": "ollama/qwen2.5:14b",
  "provider": "local",
  "task_default_for": ["extract", "summarise"],
  "always_on": true,
  "tier": 2,
  "private": true,
  "quality_score": 4,
  "cost_per_1k_input": 0.0,
  "cost_per_1k_output": 0.0,
  "context_window": 131072,
  "capabilities": ["extract", "summarise", "chat", "reason", "code"],
  "latency_tier": "fast",
  "params_total": "14B",
  "params_active": "14B",
  "architecture": "dense",
  "quantisation": "Q4_K_M",
  "ram_gb": 9,
  "cpu_tokens_per_sec": "25-40",
  "notes": "Always-on Tier 2. Replaces 8B for extract and structured output tasks. 25-40 tok/s."
}
```

---

## Updated recommender routing

With Qwen2.5-14B always-on, update classifier task routing:

| Task | Primary model | Fallback |
|---|---|---|
| extract | ollama/qwen2.5:14b | ollama/qwen3:30b-a3b → cloud |
| summarise | ollama/qwen2.5:14b | ollama/mistral:7b → cloud |
| code | ollama/qwen2.5-coder:32b | groq → gpt-4o |
| reason | ollama/qwen3:30b-a3b | claude-3-5-sonnet |
| agent | ollama/qwen3:30b-a3b | claude-3-5-sonnet |
| chat | ollama/llama3.1:8b | ollama/qwen2.5:14b → cloud |
| vision | ollama/llama3.2-vision:11b | gemini-1.5-flash → gpt-4o |
| long_context | ollama/gemma3:9b | gemini-1.5-pro |

---

## Final two-node summary

```
96GB PRIMARY                         48GB SECONDARY
────────────────────────────────     ───────────────────────────────
INFERENCE STACK                      BUSINESS LOGIC STACK
  LiteLLM proxy                        Langfuse (traces, evals)
  Ollama:                              Lago (billing, invoicing)
    Qwen3-30B-A3B     19GB always-on   Keycloak (auth, SSO)
    Qwen2.5-Coder-32B 22GB always-on   kc_lago_sync.py
    Qwen2.5-14B        9GB always-on   Mailserver (invoices)
    Llama3.1-8B        6GB warm
    Llama3.2-Vision   ~9GB warm      AVAILABLE FOR OTHER APPS
  Classifier sidecar                   Liferay CE
  Translation sidecar                  SurrealDB
  Prometheus + Grafana                 Future Coolify services
  Mailserver                           ~28GB free

Peak RAM: ~84GB / 96GB               Peak RAM: ~20GB / 48GB
Headroom: ~12GB                       Headroom: ~28GB
```

**No K8s. No Swarm. Two Coolify stacks. Private network between nodes.**
**Migration: ~1 hour. Zero downtime with the phase procedure above.**

---

## Env vars (add to .env.example on 96GB node)

```
# Secondary node endpoints (after migration)
LANGFUSE_URL=https://traces.openautonomyx.com
LAGO_API_URL=https://billing.openautonomyx.com
KC_BASE_URL=https://auth.openautonomyx.com

# Or private network (recommended):
# LANGFUSE_URL=http://10.0.0.2:3000
# LAGO_API_URL=http://10.0.0.2:3001
# KC_BASE_URL=http://10.0.0.2:8080
```
