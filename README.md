# Autonomyx Model Gateway

**A complete, self-hosted AI platform. Not a proxy. Not a toolkit. A product.**

One deployment gives you:
- Best open-source models running locally (zero API cost for compute)
- Intelligent routing — right model for every task, automatically
- Metered billing per tenant — Lago invoices, Langfuse traces
- Multi-tenant auth — Keycloak, one command to onboard a customer
- Pre-built AI workflows — ready to call, not ready to configure
- 22 Indian languages + Arabic + Southeast Asian — built in
- Human feedback loop — improves models on your actual workload

---

## What your customer does

```bash
# That's it. One call. Everything else is handled.
curl https://flows.openautonomyx.com/api/v1/run/{flow_id} \
  -H "Authorization: Bearer lf-their-api-key" \
  -d '{"input_value": "Review this contract for risk clauses"}'
```

They don't configure models. They don't manage routing. They don't touch billing.
You handle all of it. They get results.

---

## What you get as the operator

```
flows.openautonomyx.com    → Autonomyx Langflow (your pre-built workflows)
llm.openautonomyx.com      → Gateway API (direct model access for developers)
traces.openautonomyx.com   → Langfuse (per-tenant trace isolation)
billing.openautonomyx.com  → Lago (invoicing, metered plans)
auth.openautonomyx.com     → Keycloak (tenant onboarding, SSO)
metrics.openautonomyx.com  → Grafana (Prometheus, dashboard ID 17587)
mcp.openautonomyx.com      → MCP server (8 tools for Claude / agent access)
```

---

## Models running locally (zero marginal cost)

| Model | Tasks | Always-on | RAM |
|---|---|---|---|
| Qwen3-30B-A3B | reason, agent, chat | ✅ | 19GB |
| Qwen2.5-Coder-32B | code | ✅ | 22GB |
| Qwen2.5-14B | extract, structured output | ✅ | 9GB |
| Llama 3.2 11B Vision | vision | warm slot | 9GB |
| Llama 3.1 8B | chat overflow | warm slot | 6GB |
| Gemma 3 9B | long context | warm slot | 6GB |

Peak RAM: ~84GB. Runs on a 96GB VPS. No GPU required.

---

## Pre-built workflows (flows/)

| Flow | Model | What it does |
|---|---|---|
| `gateway-agent.json` | Qwen3-30B (recommended) | Language detect → recommend model → LLM → feedback capture |
| `code-review.json` | Qwen2.5-Coder-32B | Code review → JSON: bugs, security, style, score |
| `policy-creator.json` | Qwen3-30B | Generate Privacy Policy, ToS, Cookie Policy — DPDP 2023 |
| `policy-review.json` | Qwen3-30B | Analyse vendor policy → 5-domain risk report + actions |
| `feature-gap-analyzer.json` | Qwen3-30B | Compare two products across 8 dimensions → scored matrix |
| `saas-evaluator.json` | Qwen3-30B | Multi-persona SaaS evaluation → scored JSON + recommendation |
| `fraud-sentinel.json` | Qwen3-30B | Transaction fraud detection → ALLOW/WARN/BLOCK verdict |
| `app-alternatives-finder.json` | Qwen3-30B | Find OSS + commercial alternatives → ranked list |
| `saas-standardizer.json` | Qwen3-30B | Exhaustive SaaS product profile → 18-dimension JSON |
| `oss-to-saas-analyzer.json` | Qwen3-30B | Score OSS project across 5 commercial archetypes |
| `structured-data-parser.json` | Python only | Parse JSON/CSV/XML/YAML/Markdown → structured JSON (no LLM) |
| `site-scraper-rag.json` | Qwen3-30B + nomic-embed-text | Crawl any URL → structured extract → embed → SurrealDB RAG |
| `feature-gap-analyzer.json` | Qwen3-30B-A3B (always) | Compare 2-3 products → scored feature matrix + gaps + recommendation |
| `structured-data-parser.json` | Qwen2.5-Coder-32B (always) | Any data sample → Python parser code + schema + tests |

Add your own flows to `flows/` — they load into Autonomyx Langflow on startup.

---

## Customer onboarding — one command

```bash
# Create a Keycloak group → auto-provisions:
#   Lago customer (billing)
#   LiteLLM virtual key (spend tracking)
#   Langfuse organisation (trace isolation)
#   Langflow API key (workflow access)

curl -X POST https://auth.openautonomyx.com/admin/realms/autonomyx/groups \
  -H "Authorization: Bearer $KC_ADMIN_TOKEN" \
  -d '{"name": "tenant-acme"}'
# kc_lago_sync.py handles the rest automatically
```

---

## Pricing tiers (your customers)

| Tier | Price | What they get |
|---|---|---|
| Free | 10M tokens/month | Gateway API access |
| Developer | ₹999/month | 100M tokens, all local models |
| Growth | ₹4,999/month | 1B tokens, cloud fallback |
| SaaS Basic | ₹14,999/month | 5B tokens, white-label, Lago sub-billing |
| Private Node | ₹50,000+/month | Dedicated infra, DPDP DPA, India region |

Shared SaaS: billing and trace data isolated per tenant. Compute shared.
Private Node: full infrastructure isolation. DPDP DPA signable.

---

## Stack — every component chosen deliberately

19 services. Every one has documented rationale, rejected alternatives, migration cost, and a review date. See `references/service-decision-log.md`. Next review: October 2026.

| Layer | Component | Licence |
|---|---|---|
| Gateway | LiteLLM OSS | MIT |
| Models | Ollama + llama.cpp | MIT |
| Workflows | Langflow | MIT |
| Billing | Lago OSS | AGPL-3.0 |
| Auth | Keycloak | Apache 2.0 |
| Tracing | Langfuse v3 | MIT |
| Metrics | Prometheus + Grafana | Apache 2.0 |
| Translation (Indian) | IndicTrans2 | MIT |
| Translation (Arabic/SEA) | Opus-MT | Apache 2.0 |
| Language detection | fastText LID | Apache 2.0 |
| Task classifier | sentence-transformers | Apache 2.0 |

> ⚠️ NLLB-200 and SeamlessM4T are CC-BY-NC 4.0 — not commercially usable. Neither is in this stack.

---

## Two-node deployment (recommended)

```
96GB VPS — inference          48GB VPS — business logic
──────────────────────        ──────────────────────────
LiteLLM + Ollama              Langfuse
Langflow + flows              Lago
Prometheus + Grafana          Keycloak
Classifier + Translator       Mailserver
Peak: ~84GB                   Peak: ~20GB / 28GB free
```

No Kubernetes. Two Coolify-managed Docker Compose stacks.

---

## Repository structure

```
autonomyx-model-gateway/
├── README.md
├── SKILL.md                          # Claude skill — 16 steps, full output checklist
├── flows/
│   └── gateway-agent.json            # Pre-built workflow: detect → route → respond → feedback
└── references/
    ├── config-template.md            # LiteLLM config — all 14 providers
    ├── docker-compose-template.md    # Coolify + generic variants, all services
    ├── defaults.md                   # Canonical defaults
    ├── env-vars.md                   # All env vars, all services
    ├── model-limits.md               # Context windows per model
    ├── lago-integration.md           # Dual-track billing
    ├── mailserver-integration.md     # SMTP, DNS, DKIM
    ├── keycloak-integration.md       # Auth, tenant sync, OIDC
    ├── langflow-integration.md       # Gateway ↔ Langflow wiring
    ├── langflow-agent.md             # Flow architecture, variants
    ├── mcp-integration.md            # autonomyx-mcp wiring
    ├── model-recommender.md          # /recommend endpoint
    ├── local-classifier.md           # Task classifier sidecar
    ├── local-model-catalogue.md      # Model tiers, 96GB stack
    ├── profitability.md              # Pricing, cost model, GTM
    ├── langfuse-integration.md       # Multi-tenant tracing
    ├── model-improvement.md          # Opt-in feedback, RAG, fine-tuning
    ├── human-feedback.md             # Widget + SDK + Langfuse routing
    ├── translation.md                # IndicTrans2 + Opus-MT + fastText
    ├── two-node-setup.md             # 96GB + 48GB split, migration
    ├── gateway-mcp-server.md         # MCP server — 8 typed tools
    ├── deployment-agent.md           # Autonomous deployment pipeline
    ├── runtime-decision-log.md       # Ollama vs Docker Model Runner
    └── service-decision-log.md       # All 19 services: why, when to review
```

---

## Contact

- Platform: [openautonomyx.com](https://openautonomyx.com)
- Skills: [agentnxxt/agentskills](https://github.com/agentnxxt/agentskills)
- Email: chinmay@openautonomyx.com
- Book: [cal.com/thefractionalpm](https://cal.com/thefractionalpm)
