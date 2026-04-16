---
name: autonomyx-llm-gateway
description: >
  Autonomyx LLM Gateway — end-to-end LiteLLM proxy setup for 14 providers: Ollama, vLLM, TGI,
  OpenAI, Claude, Gemini, Mistral, Groq, Fireworks, Together.ai, OpenRouter, Azure, Bedrock.
  Produces config.yaml, docker-compose.yml, .env.example, token-count test script, Prometheus/
  Grafana billing stack, Langflow wiring, and autonomyx-mcp wiring. Deploys to Coolify or
  generic Docker. ALWAYS trigger for: LiteLLM, LLM proxy, LLM gateway, model routing, virtual
  keys, token tracking, cost tracking, LLM billing, "route to multiple models", "unified LLM
  API", "OpenAI-compatible endpoint", "connect Langflow to LLMs", "LiteLLM config", "docker
  compose for LLM", or any request to configure, deploy, or extend multi-model LLM infra.
---

# Autonomyx LLM Gateway Skill

Produces a complete, working LiteLLM proxy setup for the Autonomyx stack.

## Outputs this skill always produces

| Artifact | Description |
|---|---|
| `config.yaml` | LiteLLM model list, routing, fallbacks, rate limits |
| `docker-compose.yml` | LiteLLM proxy + Postgres + Prometheus + Grafana |
| `prometheus.yml` | Scrape config for LiteLLM metrics endpoint |
| `grafana-dashboard.json` | Token + cost dashboard (importable) |
| `.env.example` | All required env vars, documented |
| `test-tokens.sh` | curl-based token count + cost verify script |
| `langflow-integration.md` | How to point Langflow custom LLM at the gateway |
| `mcp-integration.md` | How to wire autonomyx-mcp to use the gateway |

---

## Step 1 — Gather Inputs

Before generating any file, confirm:

1. **Which providers are active** — check which API keys the user has. Generate model blocks only for confirmed providers. Include commented-out stubs for the rest.
2. **Local model hosts** — for Ollama/vLLM/TGI: ask for the host:port (default: `host.docker.internal:11434` for Ollama, `host.docker.internal:8000` for vLLM).
3. **Coolify vs generic Docker** — affects volume paths and network mode.
4. **Master key** — generate a secure default or let user supply one.
5. **Postgres credentials** — generate defaults or user-supplied.

If the user says "just generate defaults", use the values in `references/defaults.md`.

---

## Step 2 — Generate config.yaml

Read `references/config-template.md` for the full annotated template.

Key rules:
- Every model entry needs: `model_name` (alias), `litellm_params.model` (provider/model string), `litellm_params.api_key` (env var ref, never hardcoded)
- Group models by provider in comments
- Always include a `router_settings` block with `routing_strategy: usage-based-routing`
- Always include `fallbacks` — local model → cloud fallback
- Token counting: set `max_tokens` per model using values from `references/model-limits.md`
- Budget limits: set `max_budget` and `budget_duration` in `litellm_settings`

---

## Step 3 — Generate docker-compose.yml

Read `references/docker-compose-template.md`.

Services to include:
- `litellm` — proxy container
- `litellm-db` — Postgres 15
- `prometheus` — scrapes `/metrics` on LiteLLM
- `grafana` — token/cost dashboards

Coolify-specific:
- Add `labels` block for Coolify reverse proxy (Traefik)
- Use named volumes (not bind mounts)
- Network: `coolify` external network

Generic Docker:
- Use bind mounts for config files
- Expose port `4000` directly

---

## Step 4 — Generate .env.example

One block per provider. See `references/env-vars.md` for the full list. Rules:
- Never emit real keys — always `YOUR_KEY_HERE` placeholders
- Group: Local → OpenAI-compatible cloud → Enterprise
- Include `LITELLM_MASTER_KEY`, `DATABASE_URL`, `STORE_MODEL_IN_DB=True`

---

## Step 5 — Token Count & Billing Test

Generate `test-tokens.sh`:

```bash
#!/bin/bash
# Test token counting and cost tracking for Autonomyx LLM Gateway
BASE_URL="${LITELLM_BASE_URL:-http://localhost:4000}"
KEY="${LITELLM_KEY:-sk-autonomyx-test}"

echo "=== Model List ==="
curl -s "$BASE_URL/v1/models" -H "Authorization: Bearer $KEY" | jq '.data[].id'

echo "=== Test Completion + Token Count ==="
curl -s "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role":"user","content":"Say hello in 5 words."}],
    "max_tokens": 20
  }' | jq '{model: .model, usage: .usage, cost: .["_hidden_params"]}'

echo "=== Spend by Key ==="
curl -s "$BASE_URL/key/info" -H "Authorization: Bearer $KEY" | jq '{total_spend: .info.spend, budget: .info.max_budget}'

echo "=== Spend by Model ==="
curl -s "$BASE_URL/spend/logs?limit=5" \
  -H "Authorization: Bearer $KEY" | jq '.[] | {model, spend, total_tokens}'
```

---

## Step 6 — Langflow Integration

Read `references/langflow-integration.md` and emit it as `langflow-integration.md`.

Summary:
- In Langflow, add a **Custom OpenAI** component
- Base URL: `http://litellm:4000/v1` (if co-deployed) or `http://vps.agnxxt.com:4000/v1`
- API Key: LiteLLM virtual key
- Model: any alias from `config.yaml` model_name field
- All Langflow flows automatically get token tracking + cost logging via LiteLLM

---

## Step 7 — autonomyx-mcp Integration

Read `references/mcp-integration.md` and emit it as `mcp-integration.md`.

Summary:
- In FastMCP server, set env var `OPENAI_API_BASE=http://litellm:4000/v1`
- Set `OPENAI_API_KEY` to a LiteLLM virtual key
- All MCP tool calls route through the gateway — fully tracked

---

## Step 8 — Prometheus + Grafana

Generate `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: litellm
    static_configs:
      - targets: ['litellm:4000']
    metrics_path: /metrics
```

For Grafana: instruct user to import `references/grafana-dashboard.json` (dashboard ID `17587` — the official LiteLLM community dashboard on grafana.com).

---

## Routing & Fallback Strategy (always apply)

```
Local (Ollama/vLLM) → same-tier cloud (Groq/Together) → OpenAI/Anthropic
```

- Set `num_retries: 3` on all models
- Set `request_timeout: 60`
- Use `allowed_fails: 2` before fallback triggers

---

## Reference Files

| File | When to read |
|---|---|
| `references/defaults.md` | User says "use defaults" — canonical values |
| `references/config-template.md` | Generating config.yaml — full annotated template |
| `references/model-limits.md` | Token limits for all 14 providers |
| `references/docker-compose-template.md` | Generating docker-compose.yml |
| `references/env-vars.md` | Generating .env.example |
| `references/langflow-integration.md` | Step 6 Langflow wiring |
| `references/mcp-integration.md` | Step 7 autonomyx-mcp wiring |
| `references/lago-integration.md` | Step 8.5 Lago billing — compose services, callback, Lago UI setup, dual-track verify |
| `references/mailserver-integration.md` | Step 8.6 Docker Mailserver — compose, DNS, SMTP wiring for Lago + Keycloak |
| `references/keycloak-integration.md` | Step 8.7 Keycloak — compose, realm setup, kc_lago_sync.py, user/tenant management |
| `references/model-recommender.md` | Step 8.8 Model Recommender — recommender.py, model_registry.json, scoring logic, wiring |
| `references/local-classifier.md` | Step 8.9 Local Classifier — sentence-transformers sidecar, training data, auto-upgrade logic |
| `references/local-model-catalogue.md` | Step 8.10 Local Model Catalogue — best model per task, tiered deployment, Ollama + vLLM split, benchmarks |
| `references/profitability.md` | Step 8.11 Profitability — cost/token model, three-tier pricing, GPU phase projections, hybrid routing, GTM sequence |
| `references/langfuse-integration.md` | Step 8.12 Langfuse — multi-tenant trace routing, model improvement loop, complete tenancy audit |
| `references/model-improvement.md` | Step 8.13 Model Improvement — opt-in consent, prompt optimisation, routing optimisation, RAG, fine-tuning per segment, PII anonymisation |
| `references/human-feedback.md` | Step 8.14 Human Feedback — /feedback endpoint, embeddable widget, developer SDK, Langfuse score routing |
| `references/translation.md` | Step 8.15 Translation — native Qwen3 routing, IndicTrans2 (MIT), Opus-MT (Apache 2.0), fastText LID, pivot architecture, language matrix |
| `references/two-node-setup.md` | Step 8.16 Two-Node Setup — 96GB primary + 48GB secondary, migration procedure, Qwen2.5-14B addition, no K8s required |
| `references/runtime-decision-log.md` | Reference only — Ollama vs Docker Model Runner decision log, migration triggers, not a step |
| `references/service-decision-log.md` | Reference only — All 19 services: why chosen, alternatives rejected, migration cost, review dates |
| `references/preflight-guard.md` | Step 8.8 Pre-flight guard — tokeniser map, cost rates, context rejection, TPM limits |

---

## Step 8.5 — Lago Billing (dual-track)

Read `references/lago-integration.md` in full. Produce:

1. **Lago docker-compose additions** — append lago-api, lago-worker, lago-clock, lago-front, lago-db, lago-redis to the existing compose file. Add `lago-db-data` and `lago-redis-data` to the volumes block.
2. **`lago_callback.py`** — LiteLLM custom success callback that fires usage events to Lago per completed request (input tokens, output tokens, request count). Maps LiteLLM `key_alias` → Lago `external_customer_id`.
3. **config.yaml addition** — register `LagoCallback` under `litellm_settings.success_callback`.
4. **Lago env vars** — appended to `.env.example` (LAGO_API_KEY, LAGO_SECRET_KEY_BASE, encryption keys).
5. **Lago UI setup instructions** — billable metrics, plans, customer creation steps.
6. **Dual-track verify commands** — curl checks against both LiteLLM spend endpoint and Lago events/usage endpoints.

---

## Output Checklist

Before declaring done, verify every item is produced:

- [ ] `config.yaml` — model list, routing, fallbacks, budgets, Lago callback registered, Qwen3-30B-A3B + Qwen2.5-Coder-32B + Qwen2.5-14B always-on entries
- [ ] `docker-compose.yml` — full stack: LiteLLM + Postgres + Prometheus + Grafana + Lago (api/worker/clock/front/db/redis) + Mailserver + Keycloak (server/db) + Langfuse (server/db/redis) + Ollama + Classifier + Translator. Coolify variant: Traefik labels + coolify network. Generic variant: exposed ports.
- [ ] `prometheus.yml`
- [ ] `.env.example` — all providers + Lago vars, no real keys
- [ ] `lago_callback.py` — custom success callback
- [ ] `test-tokens.sh` — includes dual-track verify (LiteLLM spend + Lago events)
- [ ] `langflow-integration.md`
- [ ] `mcp-integration.md`
- [ ] Lago UI setup steps delivered (billable metrics, plans, customers)
- [ ] Told user where to get Grafana dashboard (ID 17587)
- [ ] `docker-compose.yml` includes mailserver (ports 25/465/587/993)
- [ ] DNS records table produced (A, MX, SPF, DKIM, DMARC)
- [ ] `billing@openautonomyx.com` mailbox setup commands provided
- [ ] Lago SMTP env vars wired to mailserver
- [ ] Keycloak services in compose (keycloak, keycloak-db, keycloak-lago-sync)
- [ ] `kc_lago_sync.py` produced — GROUP_CREATE/DELETE → Lago + LiteLLM
- [ ] Realm `autonomyx` setup commands provided
- [ ] OIDC endpoints reference delivered
- [ ] Keycloak env vars in `.env.example`
- [ ] Logto references removed from all docs
- [ ] `recommender.py` produced — FastAPI router mounted on LiteLLM
- [ ] `model_registry.json` produced — all gateway models with cost/capability/quality
- [ ] `/recommend` endpoint documented with request/response example
- [ ] Langflow + autonomyx-mcp wiring for recommender provided
- [ ] `classifier/Dockerfile` produced
- [ ] `classifier/classifier_server.py` produced — sentence-transformers + LogisticRegression
- [ ] `classifier/training_data.json` produced — 80 seed examples across 8 task types
- [ ] `recommender.py` `infer_task()` updated — local-first, auto-upgrade on low confidence
- [ ] `RECOMMENDER_MODE=local` default in `.env.example`
- [ ] Accuracy targets and retraining instructions documented
- [ ] `ollama-pull.sh` produced — Tier 1 auto-pull, Tier 2/3 instructions
- [ ] `config.yaml` updated — Tier 1 Ollama entries active, Tier 2/3 commented opt-in
- [ ] `model_registry.json` updated — task_default_for + tier fields on all local models
- [ ] Fallback chain updated — local tier 1 → tier 2 → cloud per task type
- [ ] VPS minimum spec documented (16GB RAM, 60GB disk)
- [ ] Lago plans generated matching three-tier pricing (Developer / SaaS / Enterprise)
- [ ] complexity_score wired into recommender.py routing
- [ ] Pricing page HTML artifact generated
- [ ] DPDP DPA positioning documented for Enterprise tier
- [ ] `preflight_guard.py` produced — tokeniser map, context check, TPM, budget check
- [ ] `Dockerfile.litellm` produced — adds transformers + sentencepiece
- [ ] `DEFAULT_TPM_LIMIT` in `.env.example`
- [ ] Client-facing error messages documented

## Step 8.6 — Docker Mailserver

Read `references/mailserver-integration.md` in full. Produce:

1. **docker-compose additions** — append `mailserver` service with correct Coolify labels, volumes, ports (25, 465, 587, 993).
2. **DNS records table** — A, MX, SPF, DKIM, DMARC for `openautonomyx.com`.
3. **Initial setup commands** — create `billing@openautonomyx.com` mailbox, generate DKIM key.
4. **Lago SMTP env block** — wire `LAGO_SMTP_*` vars to mailserver service.
5. **Keycloak SMTP config** — API call to configure realm email settings.
6. **Mailserver env vars** — appended to `.env.example`.
7. **Verify command** — test email send + log check.

---

## Step 8.7 — Keycloak (replaces Logto)

Read `references/keycloak-integration.md` in full. Produce:

1. **docker-compose additions** — `keycloak`, `keycloak-db`, `keycloak-lago-sync` services + `keycloak-db-data` volume.
2. **`kc_lago_sync.py`** — event-driven sync: Keycloak GROUP_CREATE → Lago customer + LiteLLM virtual key; GROUP_DELETE → archive + delete.
3. **Realm setup commands** — create `autonomyx` realm, OIDC client `autonomyx-gateway`.
4. **User management commands** — create user, assign to group (tenant).
5. **OIDC endpoints reference** — for Langflow, LiteLLM UI, app integrations.
6. **Keycloak env vars** — appended to `.env.example`.
7. **Tenant lifecycle summary** — onboard/offboard flow in plain language.

Note: Keycloak replaces Logto. Remove all Logto references from docs if present.


## Step 8.8 — Pre-flight Token Guard

Read `references/preflight-guard.md` in full. Produce:

1. **`preflight_guard.py`** — `PreflightGuard(CustomLogger)` with:
   - Model-correct tokeniser map (tiktoken for OpenAI/Azure, HF AutoTokenizer for Llama/Mistral/TGI, approx ratio for Claude/Gemini)
   - Cost rate table (input/output USD per 1M tokens for all 14 providers)
   - Context window limit table (all models)
   - Pre-call checks: context exceeded → HTTP 400, TPM exceeded → HTTP 429, budget exhausted → HTTP 429
   - Preflight metadata attached to request for downstream logging
2. **`Dockerfile.litellm`** — extends base LiteLLM image, adds `transformers sentencepiece`
3. **docker-compose update** — mount `preflight_guard.py`, use custom image build
4. **config.yaml update** — register `PreflightGuard` under `custom_callbacks`
5. **`.env.example` addition** — `DEFAULT_TPM_LIMIT`
6. **Redis upgrade note** — show how to replace in-memory TPM with `lago-redis`


## Step 8.8 — Model Recommender

Read `references/model-recommender.md` in full. Produce:

1. **`recommender.py`** — FastAPI router registered in LiteLLM `config.yaml` under `additional_routers`. Exposes `POST /recommend`. Infers task type from prompt via Claude Haiku. Reads budget from LiteLLM Postgres + Lago. Reads latency/error rate from Prometheus. Returns ranked list with fit scores, budget remaining, tokens remaining, reset time.
2. **`model_registry.json`** — one entry per model in `config.yaml`, with cost/1k, capabilities, quality score, latency tier, privacy flag.
3. **config.yaml addition** — register `recommender.router` under `general_settings.additional_routers`.
4. **docker-compose additions** — mount `recommender.py` and `model_registry.json` into LiteLLM container. Add `RECOMMENDER_INFERENCE_MODEL` and `PROMETHEUS_URL` env vars.
5. **Langflow wiring** — HTTP Request node pattern to auto-select model per request.
6. **autonomyx-mcp wiring** — `get_best_model()` helper function.
7. **Env vars** — `RECOMMENDER_INFERENCE_MODEL`, `PROMETHEUS_URL` in `.env.example`.

Note: `infer_task()` in recommender.py must use the local classifier (see Step 8.9) not a cloud API. Cloud is auto-upgrade only.


## Step 8.9 — Local Classifier

Read `references/local-classifier.md` in full. Produce:

1. **`classifier/Dockerfile`** — Python 3.12-slim, installs sentence-transformers, scikit-learn, FastAPI. Serves on port 8100 (internal only).
2. **`classifier/classifier_server.py`** — FastAPI server. On startup: loads `all-MiniLM-L6-v2`, trains LogisticRegression on `training_data.json`, saves model to `/app/model`. Endpoints: `POST /classify`, `POST /retrain`, `GET /health`.
3. **`classifier/training_data.json`** — 80 seed examples across 8 task types (chat, code, reason, summarise, extract, vision, long_context, agent). Instruct user to extend to 100+ per class.
4. **docker-compose addition** — `classifier` service on `coolify` network, `classifier-model` named volume for model persistence.
5. **Updated `infer_task()` in `recommender.py`** — local classifier first via `http://classifier:8100/classify`. If confidence >= threshold (default 0.80): return local. If below threshold AND `RECOMMENDER_MODE=auto` AND cloud key present: upgrade to cheapest available cloud model (Haiku > gpt-4o-mini > groq/llama3). Fall back to local on any cloud error.
6. **Env vars** — `CLASSIFIER_URL`, `CONFIDENCE_THRESHOLD`, `RECOMMENDER_MODE`, `AUTO_RETRAIN_ON_STARTUP` in `.env.example`.
7. **Verify commands** — standalone classifier test + full `/recommend` test with `RECOMMENDER_MODE=local` and no cloud keys.


## Step 8.10 — Local Model Catalogue

Read `references/local-model-catalogue.md` in full. Produce:

1. **`ollama-pull.sh`** — pulls all 6 Tier 1 models on startup. Prints Tier 2 manual pull commands. Prints Tier 3 vLLM note.
2. **docker-compose additions** — `ollama` service with `OLLAMA_MAX_LOADED_MODELS=2`, `OLLAMA_FLASH_ATTENTION=1`. `vllm` service commented out (GPU opt-in).
3. **`config.yaml` additions** — Tier 1 Ollama model entries active. Tier 2 and Tier 3 entries present but commented with `# opt-in` markers.
4. **`model_registry.json` updates** — add `task_default_for`, `tier`, and `private: true` to all local model entries.
5. **Fallback chain** — update `router_settings.fallbacks` in `config.yaml`: local Tier 1 → local Tier 2 → cloud fast → cloud flagship per task type.
6. **VPS spec note** — document minimum (16GB RAM, 60GB disk) and recommended (32GB RAM) in setup instructions.
7. **Benchmark table** — include in output so user understands why each model was chosen.


## Step 8.11 — Profitability & Pricing

Read `references/profitability.md` in full. Produce:

1. **Lago plan configs** — three plans (Starter ₹999, SaaS Basic ₹14,999, Enterprise custom) with correct billable metric codes matching `lago_callback.py`.
2. **complexity_score** addition to `recommender.py` — 7 scoring signals, routes complexity > 0.8 to cloud or /think mode.
3. **`pricing.html`** — single-page pricing page with benchmark table, three tiers, free tier CTA. Autonomyx brand colours.
4. **GPU phase config** — vLLM docker-compose service with continuous batching (`max-num-seqs: 256`), speculative decoding (Qwen3-3B draft), prefix caching enabled.
5. **Cost model comment block** — in `docker-compose.yml` header, document current cost/token and revenue ceiling per deployment phase.
6. **DPDP enterprise note** — one-page markdown: what DPDP Act 2023 means for enterprise customers, what Autonomyx provides (DPA, data residency, audit trail).


## Step 8.12 — Langfuse (multi-tenant observability + improvement loop)

Read `references/langfuse-integration.md` in full. Produce:

1. **docker-compose additions** — `langfuse-server`, `langfuse-db`, `langfuse-redis` on Coolify network with Traefik labels at `traces.openautonomyx.com`. Keycloak OIDC SSO wired.
2. **Extended `lago_callback.py`** — add per-tenant Langfuse trace routing. Each virtual key alias maps to a Langfuse project via `LANGFUSE_TENANT_KEYS` env var. Falls back to default project if key not mapped.
3. **Extended `kc_lago_sync.py`** — on GROUP_CREATE: create Langfuse org + project alongside Lago customer + LiteLLM key. Store returned API keys for tenant use.
4. **Langfuse Keycloak OIDC client** — add to realm setup commands in `keycloak-integration.md`.
5. **Env vars** — all Langfuse vars in `.env.example` with generation commands.
6. **Multi-tenancy claims table** — what you can and cannot claim, for sales and marketing use.
7. **Model improvement roadmap** — four-phase plan: observability → evaluation → dataset curation → fine-tuning.


## Step 8.13 — Segment-Specific Model Improvement

Read `references/model-improvement.md` in full. Produce:

1. **`improvement/anonymiser.py`** — PII stripping with Indian-specific patterns (PAN, Aadhaar, Indian mobile, email, card numbers). Required before any trace is stored for training.
2. **Extended `lago_callback.py`** — opt-in check before logging to improvement dataset. Segment lookup from `TENANT_SEGMENTS` env var.
3. **`improvement/rag_middleware.py`** — RAG enrichment using `nomic-embed-text` via Ollama + SurrealDB vector search. Per-tenant, per-segment collection scoping.
4. **`improvement/ingest.py`** — document ingestion pipeline: chunk → embed → store in SurrealDB with tenant_id isolation.
5. **`improvement/finetune.py`** — QLoRA fine-tuning with Unsloth on opt-in traces. Produces LoRA adapter per segment. GPU-only, run on RunPod A100 not VPS.
6. **SurrealDB schema** — vector collections per segment with tenant_id isolation and MTREE index.
7. **model_registry.json additions** — `fine_tuned_for` field, segment-specific fine-tuned model entries.
8. **Improvement timeline** — 6-month roadmap: prompt optimisation → routing → RAG → fine-tuning.
9. **Opt-in ToS language** — plain English, suitable for SaaS ToS insertion.


## Step 8.14 — Human Feedback Capture

Read `references/human-feedback.md` in full. Produce:

1. **`feedback.py`** — FastAPI router mounted on LiteLLM. POST /feedback accepts trace_id, score (0/1), comment, virtual_key, source. Routes to correct Langfuse tenant project. Returns score ID.
2. **Registered in `config.yaml`** — under `additional_routers` alongside recommender.router.
3. **Feedback widget** — self-contained JS + CSS snippet, zero external dependencies. Thumbs up → immediate submit. Thumbs down → shows comment box. Customer embeds after each AI response using response `id` as trace_id.
4. **Python SDK snippet** — `submit_feedback()` function for developer-side feedback.
5. **JavaScript SDK snippet** — `submitFeedback()` for frontend integration.
6. **Langfuse score query script** — `get_feedback_traces()` for weekly improvement pipeline batch.
7. **Feedback volume targets** — month-by-month targets to DPO readiness.

## Step 8.15 — Local Language Translation

Read `references/translation.md` in full. Produce:

1. **`translator_server.py`** — FastAPI sidecar on port 8200. Loads: fastText LID (917KB, auto-download), IndicTrans2 distilled 200M ×2 directions (MIT licence), Opus-MT pairs lazy-loaded on first use (Apache 2.0). Endpoints: POST /translate, GET /languages, GET /health.
2. **docker-compose addition** — `translator` service, 8GB mem_limit, `translator-models` volume for model caching.
3. **`translation_middleware.py`** — detect language → if native Qwen3: route direct → if not: pivot translate to English → call LLM → translate response back.
4. **Language support matrix** — which languages go native vs IndicTrans2 vs Opus-MT. Include RAM allocation update (4GB added).
5. **Licence guardrail** — explicitly note NLLB-200 and SeamlessM4T are CC-BY-NC — do NOT include them.
6. **Env vars** — TRANSLATOR_URL, INDICTRANS2_DEVICE in `.env.example`.


## Step 8.16 — Two-Node Setup

Read `references/two-node-setup.md` in full. Produce:

1. **Updated `docker-compose.yml` for 96GB node** — remove Langfuse, Lago, Keycloak services. Add Qwen2.5-14B to Ollama pull list. Update `mem_limit: 76g`. Update env vars pointing to 48GB node endpoints.
2. **`docker-compose-secondary.yml`** — Langfuse + Lago + Keycloak stack for 48GB node. Include all volumes, healthchecks, Traefik labels.
3. **Migration script** — `migrate-to-secondary.sh`: pg_dump from 96GB, scp, restore on 48GB, verify, stop old containers.
4. **Updated `config.yaml`** — Qwen2.5-14B model entry, updated fallback chain with 14B in extract/summarise path.
5. **Updated `model_registry.json`** — Qwen2.5-14B entry with `always_on: true`, `tier: 2`.
6. **Updated RAM maps** — both nodes showing three operating states and headroom.
7. **Network options** — public TLS vs private network, env var changes per option.
8. **K8s not-needed rationale** — document explicitly so future team members understand the decision.

