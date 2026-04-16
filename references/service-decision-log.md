# Service Decision Log — Autonomyx LLM Gateway

## Purpose

Every service in the stack was chosen for specific reasons.
This log records why, what was rejected, and when to revisit.
Review dates are hard calendar reminders — not optional.

**Owner:** Chinmay / Autonomyx infrastructure team
**Format:** Each service has why-chosen, why-alternatives-rejected, migration cost, review date, and trigger condition.

---

## Review calendar

| Review date | Services due |
|---|---|
| **October 2026** | LiteLLM, Ollama, Lago, Langfuse, Docker Mailserver, IndicTrans2, Opus-MT, sentence-transformers, SurrealDB |
| **April 2027** | Postgres, Prometheus, Grafana, Redis, Unsloth+QLoRA, Langflow, FastMCP |
| **October 2027** | Coolify |
| **April 2028** | fastText LID |

---

## 1. LiteLLM — LLM Proxy / Gateway

**Chosen:** LiteLLM OSS (`ghcr.io/berriai/litellm:main-stable`)
**Review date:** October 2026
**Trigger:** vLLM added for GPU phase — evaluate whether LiteLLM's vLLM integration is production-ready

### Why LiteLLM

- Only OSS gateway with native support for all 14 providers in one config file
- Virtual key management with per-key budgets, rate limits, model access lists — built-in multi-tenancy for billing
- Postgres-backed spend logging out of the box
- Prometheus `/metrics` endpoint — zero integration work
- Custom router (`additional_routers`) — lets us mount recommender.py and feedback.py on the same process
- LangChain, Langflow, autonomyx-mcp all have native LiteLLM support
- Active development — weekly releases

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| OpenRouter | Cloud-only — sends prompts to external servers. Incompatible with local model routing and privacy positioning |
| PortKey | SaaS product — same issue. No self-hosted option with full feature parity |
| MLflow Gateway | Good for ML experiment tracking, not built for production multi-tenant proxy with billing |
| Kong AI Gateway | Heavyweight — requires Kong infrastructure. Overkill. No native virtual key billing model |
| Custom FastAPI proxy | We'd rebuild LiteLLM from scratch. Months of work for features we get for free |

### Migration cost: Low
Both LiteLLM and any alternative expose OpenAI-compatible APIs.
Clients (Langflow, MCP) need zero changes. Only config.yaml changes.

---

## 2. Ollama — Local Model Runtime

**Chosen:** Ollama (latest)
**Review date:** October 2026
**Trigger:** First fine-tuned model ready for OCI distribution OR GPU added to infrastructure

### Why Ollama

- Mature on Linux CPU — our primary deployment target
- `OLLAMA_KEEP_ALIVE=24h` — pins 32B models in RAM permanently. No cold-start.
- Every model in our stack (Qwen3-30B-A3B, Qwen2.5-Coder-32B, Qwen2.5-14B, Llama3.2-Vision-11B, Gemma3-9B) has documented Ollama + Linux CPU configurations with known RAM figures
- LiteLLM native provider — battle-tested integration
- `OLLAMA_FLASH_ATTENTION=1` — 30% RAM reduction on attention layers

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| Docker Model Runner | Launched April 2025, optimised for Apple Silicon. Linux CPU less mature. No KEEP_ALIVE equivalent — lazy loading unacceptable for always-on 32B models. OCI model distribution is a genuine advantage — planned migration trigger |
| vLLM | Best for GPU throughput. CPU mode experimental and slower than llama.cpp. One model per process — can't run 4 models on one instance. Chosen for GPU Phase 2 |
| llama.cpp direct | No model management, no API server, no multi-model handling. Would require custom scripting for everything Ollama gives free |
| HuggingFace TGI | No native GGUF support. More complex setup. Less flexible for GGUF quantised models |
| LocalAI | Less active development. Smaller community. Less tested with LiteLLM |

### Migration cost: Low
Both Ollama and Docker Model Runner expose OpenAI-compatible APIs.
LiteLLM config change is 2 lines per model. Zero client impact.
See `runtime-decision-log.md` for full migration procedure.

---

## 3. Keycloak — Auth / IAM / SSO

**Chosen:** Keycloak 24
**Review date:** April 2027
**Trigger:** None expected. Keycloak is mature and stable.

### Why Keycloak

- Replaced Logto (original choice) — Logto lacks enterprise features needed for tenant lifecycle management
- Group-based tenancy model maps cleanly to our Keycloak group → Lago customer → LiteLLM key sync architecture
- Full OIDC/SAML support — enterprise customers can federate their own IdP
- Admin API — kc_lago_sync.py polls group events programmatically
- Apache 2.0 — no licence risk
- Self-hostable — data never leaves our infra
- Battle-tested — used by Red Hat, major banks, healthcare orgs

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| Logto | Was original choice. Lacks enterprise group lifecycle management. Admin API less mature for programmatic tenant provisioning |
| Auth0 | SaaS — prompts traverse Auth0's servers. Incompatible with privacy positioning. Pricing escalates with MAUs |
| Clerk | SaaS, developer-focused, no enterprise SAML/LDAP federation. Not suitable for B2B tenancy |
| Ory Hydra | OAuth2/OIDC server only — no user management UI, no admin console. Requires building everything on top |
| Authentik | Good alternative. Less enterprise adoption than Keycloak. Smaller community. Could work if Keycloak proves too heavy |
| Casdoor | Less mature than Keycloak for enterprise use cases |

### Migration cost: High
Migrating auth is a major project — SSO integrations, user sessions, OIDC client configs all break.
Only migrate if Keycloak becomes untenable (unlikely). Authentik is the only realistic alternative.

---

## 4. Lago — Usage-based Billing / Metering

**Chosen:** Lago OSS (self-hosted)
**Review date:** October 2026
**Trigger:** Revenue > ₹50L MRR — evaluate Lago Cloud managed vs self-hosted ops cost

### Why Lago

- Only serious OSS usage-based billing platform with MIT licence
- Native metered billing — SUM aggregation on token events maps directly to our LLM usage model
- Invoice generation, payment provider integration (Razorpay, Stripe), customer portal
- Lago customer = external_customer_id maps cleanly to Keycloak group ID
- Self-hostable — billing data never leaves our infra
- API-first — `lago_callback.py` fires events programmatically per LLM call

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| Stripe Billing | Per-seat or flat subscription only without significant custom work. Metered billing via Stripe Meters is new and limited. No invoice generation for Indian GST requirements |
| Orb | SaaS — billing data goes to Orb's servers. Not self-hostable. Pricing adds up |
| Metronome | Enterprise SaaS, expensive, US-focused |
| Amberflo | SaaS, same issue |
| OpenMeter | Good OSS alternative. Less mature than Lago. Worth watching |
| Custom Postgres | We'd build Lago from scratch — invoice generation, dunning, plan management are months of work |

### Migration cost: Medium
Lago's invoice history and customer records would need migration. Plan and metric configs re-created.
Lago Cloud is a drop-in for self-hosted — same API, managed infra. Most likely upgrade path.

---

## 5. Langfuse — LLM Observability / Tracing

**Chosen:** Langfuse v3 OSS (self-hosted)
**Review date:** October 2026
**Trigger:** Multi-node Langfuse needed OR trace volume requires ClickHouse backend

### Why Langfuse

- Only serious OSS LLM observability platform with full multi-tenancy (Organisation → Project → User hierarchy, DB-level isolation)
- Per-tenant project API keys — our per-tenant Langfuse routing architecture works natively
- Human feedback scoring API — feeds directly into improvement pipeline
- LLM-as-judge eval framework — built-in
- Dataset management for fine-tuning — export traces as training data
- Keycloak OIDC SSO — single sign-on for our ops team
- MIT licence — no commercial restrictions
- Active development — weekly releases

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| LangSmith | LangChain's product — SaaS, traces leave our infra. No self-hosted OSS option with full feature parity |
| Helicone | SaaS. Same issue |
| Arize Phoenix | OSS but less mature multi-tenancy. Better for ML model monitoring broadly, not LLM-specific |
| Weights & Biases | ML experiment tracking — not purpose-built for LLM observability |
| Braintrust | SaaS. No self-hosted |
| Custom Postgres | Would need to build trace ingestion, UI, eval framework, dataset management. Months of work |

### Migration cost: Medium
Trace data format is Langfuse-specific. Eval datasets and scores would need re-ingestion.
Not worth migrating unless scale demands it.

---

## 6. Postgres — Relational Database

**Chosen:** Postgres 15-alpine
**Review date:** April 2027
**Trigger:** None planned. Postgres is the foundation.

### Why Postgres

- Industry standard for transactional workloads
- Used by LiteLLM, Langfuse, Lago, Keycloak natively — all have official Postgres support
- Row-level security (RLS) — planned addition for LiteLLM spend log isolation
- pgvector extension — future option for RAG if SurrealDB doesn't meet needs
- alpine image — minimal attack surface, small container
- No licence risk — fully open source

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| MySQL / MariaDB | LiteLLM, Langfuse, Lago all prefer Postgres. Would need compatibility validation |
| CockroachDB | Distributed — unnecessary complexity for single-node setup. Postgres-compatible but not identical |
| Neon | Serverless Postgres — SaaS, data leaves infra. Good for future cloud phase |
| Supabase | Managed Postgres + extras — SaaS |

### Migration cost: High
Multiple services depend on Postgres. Migration would require coordinated downtime.
No realistic migration planned.

---

## 7. Prometheus — Metrics Collection

**Chosen:** Prometheus (latest)
**Review date:** April 2027
**Trigger:** Metrics cardinality becomes expensive to store — evaluate VictoriaMetrics

### Why Prometheus

- LiteLLM exposes native `/metrics` endpoint in Prometheus format
- Industry standard — every monitoring tool integrates with it
- Pairs natively with Grafana
- 30-day retention configured — sufficient for operational monitoring
- No licence risk

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| InfluxDB | Different query language (Flux). More complex setup for our use case |
| VictoriaMetrics | Better long-term storage efficiency — worth considering at scale. Drop-in Prometheus replacement |
| Datadog | SaaS, expensive, data leaves infra |
| New Relic | Same |

### Migration cost: Low
VictoriaMetrics is Prometheus-compatible. Grafana dashboards unchanged.
Easy migration when needed.

---

## 8. Grafana — Metrics Visualisation

**Chosen:** Grafana OSS (latest)
**Review date:** April 2027
**Trigger:** None expected

### Why Grafana

- Native Prometheus datasource
- LiteLLM community dashboard (ID 17587) — importable, no build required
- Per-organisation scoping — planned for per-tenant dashboard isolation
- OSS — no licence risk

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| Grafana Cloud | SaaS — metrics leave infra |
| Datadog / New Relic | Expensive SaaS |
| Kibana | ELK stack — overkill for metrics |
| Metabase | Better for SQL analytics, not time-series metrics |

### Migration cost: Low. No realistic migration planned.

---

## 9. Docker Mailserver — SMTP / Email Delivery

**Chosen:** Docker Mailserver (self-hosted)
**Review date:** October 2026
**Trigger:** Deliverability issues (spam folder rates > 5%) OR volume > 10k emails/month

### Why Docker Mailserver

- Self-hosted SMTP — invoice emails (from Lago) and auth emails (from Keycloak) never leave our infra
- Full DKIM/SPF/DMARC support — deliverability comparable to cloud providers when configured correctly
- Rspamd anti-spam built-in
- No per-email cost at low volume
- Single container — simple ops

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| Brevo (Sendinblue) | SaaS — email content leaves infra. Acceptable for marketing, not for invoices/auth |
| AWS SES | Good option for Phase 2 cloud. Per-email pricing. Data leaves infra |
| Mailgun | SaaS, same issue |
| Resend | Developer-focused SaaS, new, no self-hosted |
| Postal | More complex self-hosted option. Overkill vs Docker Mailserver |

### Migration cost: Low
Lago and Keycloak just need SMTP credentials updated. DNS records stay the same.
AWS SES is the most likely upgrade path if deliverability becomes an issue.

---

## 10. Coolify — PaaS / Deployment Platform

**Chosen:** Coolify (latest)
**Review date:** October 2027
**Trigger:** 5+ nodes OR horizontal auto-scaling required

### Why Coolify

- Self-hosted Heroku/Vercel equivalent — manages Docker Compose stacks with a UI
- Multi-server support — already manages both VPS nodes from one dashboard
- Traefik integration — automatic TLS, reverse proxy, subdomain routing
- Built-in environment variable management — critical for our 40+ env vars
- One-click deployments — reduces ops burden significantly
- OSS — no licence risk

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| Portainer | Container management, not PaaS. No deployment automation, no Traefik integration |
| Dokku | Single-server focus. Less UI. More manual |
| Caprover | Good alternative. Less active development than Coolify |
| Raw Docker Compose | No UI, no multi-server, no automatic TLS. High ops burden |
| Kubernetes | 3-4GB RAM overhead per node for control plane. Steep learning curve. No benefit at 2-node scale |

### Migration cost: High
Coolify manages our entire deployment. Migration = rebuilding all service configs in another tool.
No realistic migration planned until K8s is genuinely needed (5+ nodes).

---

## 11. IndicTrans2 — Indian Language Translation

**Chosen:** IndicTrans2 distilled 200M (AI4Bharat, MIT licence)
**Review date:** October 2026
**Trigger:** Quality score < 0.75 on specific language pair after 30 days of traces → evaluate full 1.1B

### Why IndicTrans2

- Only commercially usable (MIT) high-quality Indian language translation model
- Covers all 22 scheduled Indian languages
- SOTA on Dravidian language pairs — beats GPT-4 on several
- LoRA fine-tuning supported — can improve on our customer domain data
- AI4Bharat — IIT Madras backed, India-specific, actively maintained
- Distilled 200M fits in ~1GB RAM

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| NLLB-200 (Meta) | CC-BY-NC 4.0 — **commercially blocked**. Cannot use |
| SeamlessM4T (Meta) | CC-BY-NC 4.0 — **commercially blocked**. Cannot use |
| Google Translate API | SaaS — prompts leave infra. Per-character pricing adds up at scale |
| Azure Translator | SaaS, same issue |
| Qwen3 native only | Qwen3 handles major Indian languages natively (Hindi, Tamil, Telugu, etc.) but weaker on low-resource languages (Odia, Assamese, Santali, Manipuri). IndicTrans2 fills the gap |

### Migration cost: Low
Translation is a sidecar — swap the model, keep the API interface.

---

## 12. Opus-MT — Arabic + Southeast Asian Translation

**Chosen:** Helsinki-NLP Opus-MT (Apache 2.0)
**Review date:** October 2026
**Trigger:** Quality score < 0.70 on Arabic or SEA language pair → evaluate commercial API pass-through

### Why Opus-MT

- Apache 2.0 — commercially safe
- 300MB per language pair — extremely lightweight
- Fast on CPU — 500-1000 tokens/sec
- Covers Arabic, Thai, Vietnamese, Indonesian, Malay, Tagalog, Sinhala
- Lazy-loaded — only language pairs actually used are in RAM

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| NLLB-200 | CC-BY-NC 4.0 — **commercially blocked** |
| SeamlessM4T | CC-BY-NC 4.0 — **commercially blocked** |
| Google Translate API | SaaS — prompts leave infra |
| Qwen3 native | Handles Arabic and major SEA languages natively. Opus-MT is fallback for lower-resource pairs where Qwen3 quality drops |

### Migration cost: Low. Swap model files, keep API interface.

---

## 13. fastText LID — Language Identification

**Chosen:** fastText lid.176.ftz (Apache 2.0, 917KB)
**Review date:** April 2028
**Trigger:** None. fastText LID is essentially solved technology.

### Why fastText LID

- 917KB — trivially small
- 176 language support including all Indian languages, Arabic, SEA
- ~1ms inference — adds zero latency
- Apache 2.0 — no licence risk
- Accuracy: ~93% on short texts, ~98% on texts > 50 chars
- Used in production by Wikipedia, Mozilla, major NLP pipelines

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| langdetect | Python port of Google's language-detection. Slower, less accurate on Indian scripts |
| lingua-py | More accurate on short texts but 50MB+ model. Overkill |
| CLD3 | Google's model. Less coverage of Indian languages |
| Qwen3 as LID | Using a 30B model to detect language is absurd when fastText does it in 1ms |

### Migration cost: Trivial. One file swap.

---

## 14. sentence-transformers (all-MiniLM-L6-v2) — Task Classifier

**Chosen:** all-MiniLM-L6-v2 (Apache 2.0, 80MB)
**Review date:** October 2026
**Trigger:** Non-English traffic > 20% of requests → migrate to paraphrase-multilingual-MiniLM-L12-v2

### Why all-MiniLM-L6-v2

- 80MB — fits in classifier sidecar comfortably
- ~50ms inference on CPU — fast enough for real-time routing
- 93%+ accuracy on our 8-class task classifier (chat/code/reason/summarise/extract/vision/long_context/agent) with 100+ examples per class
- Apache 2.0 — no licence risk
- Battle-tested — most downloaded sentence-transformer model

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| all-mpnet-base-v2 | 420MB, ~2% accuracy gain. Not worth 5× RAM increase for marginal improvement |
| paraphrase-multilingual-MiniLM-L12-v2 | 470MB, supports 50+ languages. Chosen as migration path when non-English traffic > 20% |
| OpenAI text-embedding-3-small | Cloud API — adds latency, cost, external dependency. Defeats the purpose of a local classifier |
| Custom trained classifier | Would require labelled dataset, training infrastructure. all-MiniLM-L6-v2 with fine-tuning on our data is sufficient |

### Migration cost: Low. Swap model, retrain classifier, keep API interface.

---

## 15. SurrealDB — Vector DB / Multi-model DB (RAG)

**Chosen:** SurrealDB Cloud (`schemadb-06ehsj292ppah8kbsk9pmnjjbc.aws-aps1.surreal.cloud`)
**Review date:** October 2026
**Trigger:** RAG goes live in production — validate retrieval quality vs dedicated vector DB alternatives

### Why SurrealDB

- Already in the Autonomyx stack — no new service to operate
- MTREE vector index — native approximate nearest-neighbour search
- Multi-model — handles both structured data (tenant configs, model registry) and vector embeddings in one DB
- SurrealQL — familiar query language for the team
- Apache 2.0 OSS / Cloud managed option

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| Qdrant | Better pure vector search performance. Worth evaluating if SurrealDB retrieval quality is insufficient. No multi-model capability |
| Weaviate | More complex setup. Better for large-scale vector workloads |
| Chroma | Simple, Python-native. Good for prototyping, less suitable for production multi-tenant |
| pgvector (Postgres extension) | Would consolidate into existing Postgres. Good alternative — avoids a new service |
| Milvus | Enterprise-grade but heavy. Overkill at our scale |

### Migration cost: Medium
RAG pipeline queries would need updating. Vector data re-ingested.
Qdrant is the most likely migration target if SurrealDB vector quality is insufficient.

---

## 16. Redis — Cache / Message Queue

**Chosen:** Redis 7-alpine
**Review date:** April 2027
**Trigger:** Redis licence becomes problematic — evaluate Valkey

### Why Redis

- Required by Langfuse, Lago, Keycloak — all have official Redis support
- Redis 7 uses SSPL licence — not OSI-approved but acceptable for self-hosted use (not for SaaS redistribution)
- alpine image — minimal footprint
- Fast, battle-tested

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| Valkey | Redis fork under BSD licence after Redis licence change. Drop-in replacement. No adoption reason yet but low migration cost |
| KeyDB | Multi-threaded Redis fork. No advantage at our scale |
| Dragonfly | High-performance Redis alternative. Overkill at current scale |
| Memcached | No pub/sub, no sorted sets — Langfuse and Lago need these |

### Migration cost: Trivial
Valkey is wire-compatible with Redis. Image swap only.

---

## 17. Unsloth + QLoRA — Fine-tuning Framework

**Chosen:** Unsloth + QLoRA (Apache 2.0)
**Review date:** April 2027
**Trigger:** DPO phase begins — evaluate OpenRLHF for preference optimisation

### Why Unsloth

- 2× faster than HuggingFace TRL for QLoRA fine-tuning
- 70% less VRAM — critical for GPU cost control on RunPod
- Supports Qwen3, Llama3, Mistral, Gemma — all models in our stack
- Produces standard LoRA adapters — deployable via any framework
- Day-zero access to new models (Qwen3.5, etc.) — Alibaba/Qwen partnership
- Apache 2.0 — no licence risk

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| HuggingFace TRL | Standard, well-documented. 2× slower and more VRAM than Unsloth. Worth using if Unsloth has issues |
| LLaMA-Factory | Good alternative. Slightly less polished for our specific model stack |
| Axolotl | Production-grade, popular. More configuration overhead than Unsloth for our use case |
| OpenRLHF | Better for RLHF/DPO at scale. Planned for when human feedback volume reaches DPO threshold (5k+ rated pairs) |

### Migration cost: Low
LoRA adapters are framework-agnostic. Training code change only.

---

## 18. Langflow — Visual Flow Builder

**Chosen:** Langflow (self-hosted, Coolify)
**Review date:** April 2027
**Trigger:** None expected — Langflow is core Autonomyx infra

### Why Langflow

- Core Autonomyx platform component — autonomyx-langflow-expert skill already built
- Visual flow builder — non-technical customers can build AI workflows
- LiteLLM integration — Langflow flows route through our gateway automatically
- MCP server support — flows can use MCP tools
- RAG pipeline support — vector store, embedding, retrieval components built-in
- Apache 2.0 — no licence risk

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| n8n | General automation, not AI-first. No native LLM flow components |
| Flowise | Similar to Langflow. Less active development. Smaller ecosystem |
| Dify | SaaS-first, complex self-hosting. More opinionated than Langflow |
| Custom FastAPI | We'd build Langflow from scratch. Not worth it |

### Migration cost: High
Langflow flows would need rebuilding in alternative tool.
No realistic migration planned.

---

## 19. FastMCP — MCP Server Framework

**Chosen:** FastMCP (Python, MIT)
**Review date:** April 2027
**Trigger:** MCP specification v2 released — validate FastMCP compatibility

### Why FastMCP

- Simplest way to build MCP servers in Python
- Decorator-based — tools defined with `@mcp.tool()`
- Typed inputs/outputs — integrates with Pydantic
- OpenAPI schema export — documents all tools automatically
- MIT licence — no restrictions
- autonomyx-mcp already built on FastMCP — established pattern

### Why alternatives were rejected

| Alternative | Rejected because |
|---|---|
| MCP Python SDK direct | More boilerplate. FastMCP is a thin, well-designed wrapper |
| TypeScript MCP SDK | Would require Node.js in our Python stack. No advantage |
| Custom HTTP server | We'd rebuild FastMCP. Not worth it |

### Migration cost: Low
MCP tools are framework-agnostic at the protocol level.
FastMCP → MCP SDK is a straightforward port.

---

## How to use this log

1. **When evaluating a new tool:** check if it replaces anything in this log first
2. **When a trigger fires:** do not migrate without re-running the comparison — the landscape changes fast
3. **On review dates:** spend 1 hour checking if the "why alternatives were rejected" still holds
4. **When adding a new service:** add it here before merging to main

---

*Last updated: April 2026*
*Next bulk review: October 2026*
