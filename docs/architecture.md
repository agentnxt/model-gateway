# Architecture

Autonomyx Model Gateway is a complete, self-hosted AI platform. Not a proxy. Not a toolkit.

## What it is

One deployment gives you local models running on your infrastructure, intelligent routing to the right model for every task, per-tenant billing and observability, pre-built AI workflows, and 22 Indian languages built in.

## Two-node layout (operator)

```
96GB VPS — inference                    48GB VPS — business logic
────────────────────────────            ────────────────────────────────
LiteLLM     unified API proxy           Langfuse    per-tenant tracing
Ollama      local model runtime         Lago        metered billing
Langflow    workflow engine             Keycloak    SSO + tenant auth
Prometheus  metrics                     Mailserver  SMTP for invoices
Grafana     dashboards
Classifier  task routing sidecar
Translator  22-language sidecar
Playwright  web scraper + RAG sidecar
```

The 48GB node runs business logic that serves all tenants. The 96GB node handles all AI inference.

## Customer private node (single VPS)

A private node customer gets one dedicated VPS running:

```
LiteLLM + Ollama + Postgres + Prometheus + Grafana + Langflow + Playwright
```

They do **not** run Lago, Keycloak, Langfuse, or Mailserver. Those live on your 48GB operator node and serve all customers. Their traces go to your Langfuse (isolated per tenant org), their billing goes to your Lago, their auth goes to your Keycloak.

## Request flow

```
Customer app
  │
  ▼
LiteLLM /v1/chat/completions
  │  checks virtual key budget (Postgres)
  │  logs trace to Langfuse (customer's org)
  │  fires usage event to Lago
  │
  ├─ Local model → Ollama (Qwen3-30B, Coder-32B, etc.)
  └─ Cloud fallback → OpenAI / Claude / Groq (if local fails or budget allows)
```

## Workflow flow (Langflow)

```
Customer app
  │
  ▼
Langflow /api/v1/run/{flow_id}   ← Langflow API key (auth only)
  │
  ▼
Flow runs internally
  │  calls LiteLLM with customer's virtual key (spend tracking)
  │  may call Playwright sidecar (web scraping)
  │  may call Translator sidecar (22 languages)
  │  may call Classifier sidecar (task routing)
  │
  ▼
Structured JSON response
```

## Model stack (96GB node)

| Model | Tasks | RAM | Status |
|---|---|---|---|
| Qwen3-30B-A3B Q4_K_M | reason, agent, chat, policy, analysis | 19GB | Always-on |
| Qwen2.5-Coder-32B Q4_K_M | code review, generation, debugging | 22GB | Always-on |
| Qwen2.5-14B Q4_K_M | extract, structured output | 9GB | Always-on |
| Llama3.2-Vision-11B Q4_K_M | vision tasks | 9GB | Warm slot |
| Llama3.1-8B Q4_K_M | chat overflow | 6GB | Warm slot |
| Gemma3-9B Q4_K_M | long context | 6GB | Warm slot |
| nomic-embed-text | RAG embeddings | 274MB | Always-on |

Peak RAM: ~84GB / 96GB. 12GB headroom.

## Tenancy model

| Layer | Isolation | Mechanism |
|---|---|---|
| Auth (Keycloak) | Full | Group per tenant |
| Billing (Lago) | Full | external_customer_id per tenant |
| LiteLLM keys | Full | Virtual key per tenant, per-key budget |
| Traces (Langfuse) | Full | Organisation per tenant, DB-level |
| Compute (Ollama) | Shared | Standard for SaaS LLM providers |
| Langflow UI | Not available | Internal use only — OSS limitation |

## Licence-safe stack

All services are MIT, Apache 2.0, or AGPL. Two models explicitly excluded:

- NLLB-200 (Meta) — CC-BY-NC 4.0, not commercially usable
- SeamlessM4T (Meta) — CC-BY-NC 4.0, not commercially usable

Translation uses IndicTrans2 (MIT) and Opus-MT (Apache 2.0) instead.
