# autonomyx-llm-gateway

**Autonomyx LLM Gateway** — end-to-end LiteLLM proxy skill for the Autonomyx platform.

Produces a complete, production-ready LLM gateway stack covering 14 model providers, billing, auth, observability, local language translation, human feedback, and segment-specific model improvement.

---

## What this skill produces

| Artifact | Description |
|---|---|
| `config.yaml` | LiteLLM model list, routing, fallbacks, budgets |
| `docker-compose.yml` | Full stack — Coolify or generic Docker variant |
| `prometheus.yml` | Metrics scrape config |
| `.env.example` | All env vars, all providers, no real keys |
| `lago_callback.py` | Dual-track billing callback (LiteLLM → Lago) |
| `recommender.py` | Model recommender FastAPI router |
| `feedback.py` | Human feedback capture endpoint |
| `translator_server.py` | Local language translation sidecar |
| `classifier/` | Local task classifier (sentence-transformers + LogisticRegression) |
| `kc_lago_sync.py` | Keycloak group → Lago + LiteLLM tenant sync |
| `ollama-pull.sh` | Model pull script (96GB RAM, Option C stack) |
| `test-tokens.sh` | Token count + dual-track billing verify |

---

## Stack

### Inference
- **LiteLLM** — unified proxy for 14 providers
- **Ollama** — local model runtime (always-on: Qwen3-30B-A3B + Qwen2.5-Coder-32B + Qwen2.5-14B)

### Providers covered
Local: Ollama, vLLM, HuggingFace TGI
Cloud: OpenAI, Anthropic/Claude, Google Gemini, Mistral, Groq, Fireworks, Together.ai, OpenRouter, Azure OpenAI, AWS Bedrock

### Billing
- **Lago** (OSS, self-hosted) — metered billing, invoicing, customer plans
- **LiteLLM Postgres** — operational spend logs, real-time budget enforcement
- Dual-track: LiteLLM enforces budgets, Lago generates invoices

### Auth
- **Keycloak** — SSO, tenant group management, OIDC for all services

### Observability
- **Langfuse v3** — per-tenant LLM tracing, human feedback, eval datasets
- **Prometheus + Grafana** — infrastructure metrics (dashboard ID 17587)

### Email
- **Docker Mailserver** — self-hosted SMTP for Lago invoices + Keycloak auth emails

### Translation
- **fastText LID** (Apache 2.0) — language detection, 917KB
- **IndicTrans2** (MIT) — 22 Indian languages ↔ English
- **Opus-MT** (Apache 2.0) — Arabic + Southeast Asian ↔ English
- Native routing via **Qwen3-30B-A3B** for major Indian languages (no translation overhead)

> ⚠️ NLLB-200 and SeamlessM4T are CC-BY-NC 4.0 — not commercially usable. Neither is included.

### Model Improvement
- Opt-in human feedback via embeddable widget + developer SDK
- LLM-as-judge scoring via Langfuse
- RAG per segment via SurrealDB + nomic-embed-text
- LoRA fine-tuning via Unsloth + QLoRA (GPU phase)
- PII anonymisation before any training data storage

---

## Two-node deployment (recommended)

| 96GB Primary | 48GB Secondary |
|---|---|
| LiteLLM, Ollama, Prometheus, Grafana, Classifier, Translator | Langfuse, Lago, Keycloak, Mailserver |
| Peak RAM: ~84GB | Peak RAM: ~20GB |

No Kubernetes required. Two independent Coolify-managed Docker Compose stacks.

---

## Model stack (96GB CPU-only VPS)

| Model | RAM | Always-on | Tasks |
|---|---|---|---|
| Qwen3-30B-A3B Q4_K_M | 19GB | ✅ | reason, agent, chat |
| Qwen2.5-Coder-32B Q4_K_M | 22GB | ✅ | code |
| Qwen2.5-14B Q4_K_M | 9GB | ✅ | extract, structured output |
| Llama 3.2 11B Vision Q4_K_M | 9GB | LRU | vision |
| Llama 3.1 8B Q4_K_M | 6GB | LRU | chat overflow |
| Gemma 3 9B Q4_K_M | 6GB | LRU | long_context |

---

## Pricing tiers

| Tier | Price | Compute |
|---|---|---|
| Free | 10M tokens/month | Shared |
| Developer | ₹999/month | Shared |
| Growth | ₹4,999/month | Shared |
| SaaS Basic | ₹14,999/month | Shared + white-label |
| Private Node | ₹50,000+/month | Dedicated |

Shared SaaS: billing and trace data isolated per tenant. Compute shared (standard for SaaS LLM providers).
Private Node: full infrastructure isolation, DPDP DPA signable.

---

## Service decision log

All 19 services have documented decision rationale, rejected alternatives, migration cost, and review dates. See `references/service-decision-log.md`.

Next bulk review: **October 2026**

---

## Skill structure

```
autonomyx-llm-gateway/
├── SKILL.md                          # Master skill — 16 steps + output checklist
└── references/
    ├── config-template.md            # Annotated config.yaml — all 14 providers
    ├── docker-compose-template.md    # Coolify + generic Docker variants
    ├── defaults.md                   # Canonical default values
    ├── env-vars.md                   # All env vars, all services
    ├── model-limits.md               # Context windows + max output per model
    ├── lago-integration.md           # Dual-track billing setup
    ├── mailserver-integration.md     # SMTP, DNS, DKIM
    ├── keycloak-integration.md       # Auth, tenant sync, OIDC
    ├── langflow-integration.md       # Langflow → gateway wiring
    ├── mcp-integration.md            # autonomyx-mcp → gateway wiring
    ├── model-recommender.md          # /recommend endpoint, scoring, registry
    ├── local-classifier.md           # sentence-transformers sidecar
    ├── local-model-catalogue.md      # Model tiers, 96GB Option C stack
    ├── profitability.md              # Pricing architecture, cost model, GTM
    ├── langfuse-integration.md       # Multi-tenant tracing, tenancy audit
    ├── model-improvement.md          # Opt-in feedback, RAG, fine-tuning
    ├── human-feedback.md             # Widget + SDK + Langfuse score routing
    ├── translation.md                # IndicTrans2 + Opus-MT + fastText LID
    ├── two-node-setup.md             # 96GB + 48GB node split, migration
    ├── runtime-decision-log.md       # Ollama vs Docker Model Runner
    └── service-decision-log.md       # All 19 services: why chosen, review dates
```

---

## Part of the Autonomyx Skills Marketplace

- Skills repo: [agentnxxt/agentskills](https://github.com/agentnxxt/agentskills)
- Platform: [openautonomyx.com](https://openautonomyx.com)
- Contact: chinmay@openautonomyx.com
- Book: [cal.com/thefractionalpm](https://cal.com/thefractionalpm)
