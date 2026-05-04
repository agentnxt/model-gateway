# Model Gateway Architecture (LiteLLM-free)

This document defines a production-grade, async-first LLM gateway architecture built on our own codebase (no LiteLLM dependency).

## 1) High-level architecture diagram

```text
                    +-----------------------------+
                    |  Client Apps / SDKs / MCP  |
                    +--------------+--------------+
                                   |
                                   v
                        +----------+-----------+
                        | API Layer (FastAPI)  |
                        | /v1/chat, /v1/embed  |
                        | /v1/responses, /ws   |
                        +----------+-----------+
                                   |
                                   v
                 +-----------------+------------------+
                 |  Auth & Governance Middleware      |
                 |  - API key validation              |
                 |  - tenant policy / model ACL       |
                 |  - rate-limit precheck             |
                 +-----------------+------------------+
                                   |
                                   v
                     +-------------+-------------+
                     | Request Orchestrator      |
                     | - normalize request       |
                     | - select route strategy   |
                     | - retries/failover        |
                     | - streaming coordinator   |
                     +------+------+-------------+
                            |      |
            +---------------+      +----------------+
            |                                    |
            v                                    v
 +----------+----------+              +----------+----------+
 | Routing Engine      |              | Cost & Usage Engine |
 | - candidate models  |              | - token estimate    |
 | - latency scores    |              | - final token cost  |
 | - price scores      |              | - per-tenant ledger |
 +----------+----------+              +----------+----------+
            |                                    |
            +----------------+-------------------+
                             |
                             v
                  +----------+-----------+
                  | Provider Adapter SPI |
                  | OpenAI / Anthropic   |
                  | Gemini / Groq / etc. |
                  +----+------------+----+
                       |            |
                       v            v
                 External APIs   Local models

Cross-cutting:
- Redis: rate limits, idempotency keys, hot routing stats, stream resume cursors
- Postgres: API keys, model registry, pricing table, usage/billing ledger, audit events
- Observability: OpenTelemetry traces + Prometheus metrics + structured logs
```

## 2) Layer responsibilities

### A. API Layer
- Exposes OpenAI-compatible endpoints (`/v1/chat/completions`, `/v1/embeddings`) plus internal admin endpoints.
- Handles request parsing, schema validation, and response serialization.
- Supports SSE and WebSocket streaming.
- No provider-specific logic.

### B. Auth & Governance Middleware
- Validates API keys and resolves `tenant_id`.
- Applies model access policy (allow/deny list per tenant).
- Runs rate-limit precheck (RPM/TPM + burst).
- Injects request context (trace_id, tenant_id, budget scope).

### C. Request Orchestrator
- Converts API payload into internal canonical request object.
- Chooses routing strategy (cost, latency, balanced, pinned).
- Executes call chain with retry policy and failover.
- Owns streaming lifecycle and client backpressure handling.

### D. Routing Engine
- Produces ranked candidates from model registry and real-time stats.
- Scores candidates by weighted policy:
  - `cost_score`
  - `latency_score`
  - `health_score`
  - optional `quality_tier`
- Returns fallback sequence (not just one model).

### E. Provider Adapter Layer (SPI)
- One adapter per provider.
- Maps canonical request to provider-specific format.
- Normalizes provider response into canonical response.
- Converts provider streaming events into unified event protocol.

### F. Cost & Usage Engine
- Calculates estimated pre-call cost (for budget checks).
- Reconciles actual usage post-call (input/output tokens).
- Writes immutable usage ledger rows.
- Exposes billing aggregates per tenant/key/model.

### G. Platform/Infra Services
- Redis: distributed counters, lock-free throttling, hot cache.
- Postgres: source of truth for config + billing + audits.
- Metrics/logs/traces exported via OTEL collectors.

## 3) Interfaces and contracts

```python
# domain/contracts.py
from typing import AsyncIterator, Protocol
from dataclasses import dataclass

@dataclass
class CanonicalRequest:
    tenant_id: str
    api_key_id: str
    model_hint: str | None
    messages: list[dict]
    max_tokens: int | None
    temperature: float | None
    stream: bool
    metadata: dict

@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    total_tokens: int

@dataclass
class CanonicalResponse:
    id: str
    model: str
    output_text: str | None
    usage: Usage
    finish_reason: str | None
    raw: dict

class ProviderAdapter(Protocol):
    name: str

    async def chat(self, req: CanonicalRequest) -> CanonicalResponse: ...

    async def stream_chat(self, req: CanonicalRequest) -> AsyncIterator[dict]: ...

    async def healthcheck(self) -> bool: ...

class RoutingStrategy(Protocol):
    async def rank_candidates(self, req: CanonicalRequest) -> list["RouteCandidate"]: ...

class RateLimiter(Protocol):
    async def check_and_consume(
        self, tenant_id: str, api_key_id: str, est_tokens: int
    ) -> tuple[bool, dict]: ...
```

Design rule: orchestrator depends on `Protocol` contracts only (dependency inversion).

## 4) Example request flow

1. Client calls `POST /v1/chat/completions` with `Authorization: Bearer sk_...`.
2. API layer validates schema and creates request context.
3. Auth middleware resolves tenant and key, checks ACL + rate limits.
4. Orchestrator canonicalizes payload.
5. Routing engine returns ranked candidates, e.g. `[gpt-4.1-mini, claude-haiku, gemini-flash]`.
6. Orchestrator calls first provider adapter.
7. If timeout/429/5xx, retry according to policy, then fail over to next candidate.
8. For streaming: adapter yields chunks -> orchestrator normalizes -> API sends SSE/WebSocket frames.
9. On completion/failure, cost engine writes usage + cost row in Postgres.
10. Metrics/traces/logs emitted with route, latency, retries, and final provider.

## 5) Suggested folder structure

```text
gateway/
  app/
    main.py
    api/
      v1_chat.py
      v1_embeddings.py
      v1_responses.py
      ws_stream.py
    middleware/
      auth.py
      rate_limit.py
      tracing.py
  domain/
    models.py
    contracts.py
    errors.py
  orchestrator/
    service.py
    retry.py
    stream.py
  routing/
    engine.py
    strategies/
      cost.py
      latency.py
      balanced.py
  providers/
    base.py
    openai_adapter.py
    anthropic_adapter.py
    gemini_adapter.py
    registry.py
  usage/
    tokenizer.py
    pricing.py
    ledger.py
  infra/
    db/
      models.py
      repositories.py
      migrations/
    redis/
      limiter.py
      cache.py
    observability/
      logging.py
      metrics.py
      tracing.py
  config/
    settings.py
    model_catalog.yaml
  tests/
    unit/
    integration/
    contract/
```

## 6) Tech stack recommendations (MVP)

- **Python 3.12** + **FastAPI** + **Uvicorn** (async, mature ecosystem)
- **httpx** for provider calls (timeouts, retries, async streaming)
- **Pydantic v2** for request/response schemas
- **Postgres** + **SQLAlchemy 2.0** + **Alembic**
- **Redis** for rate limiting + ephemeral routing stats
- **OpenTelemetry** SDK + Collector
- **Prometheus** + Grafana dashboards
- Optional worker: **Arq/Celery** for async billing aggregation jobs

## 7) Key edge cases / failure scenarios

- Provider returns partial stream then drops connection.
  - Emit terminal error event to client.
  - Mark route attempt as failed; do not silently switch providers mid-generation unless policy explicitly allows it.

- Retry storm during provider outage.
  - Use bounded retries + jittered backoff + circuit breaker per provider/model.

- Inaccurate token estimate pre-call.
  - Pre-check uses estimate; post-call reconciliation adjusts ledger with actual usage.

- Timeout after provider actually processed request.
  - Use idempotency key at orchestrator/provider layer when possible.
  - Record ambiguous state for later reconciliation.

- Rate-limit race across replicas.
  - Redis atomic LUA script for check-and-consume.

- SSE client disconnect.
  - Cancel upstream provider stream immediately to reduce cost leakage.

- API key revoked during long stream.
  - Revalidate at chunk intervals (lightweight) or enforce max stream duration.

## Trade-offs and scaling path

### MVP trade-offs
- Start with per-request routing (no long-term ML ranking).
- Keep strategies simple weighted scoring from Redis + static pricing table.
- Postgres ledger append-only, aggregate with periodic jobs.

### Scaling path
- Add online route optimizer using historical quality/latency/cost outcomes.
- Split gateway into control plane (config/policy) and data plane (inference routing).
- Shard usage ledger by tenant or time.
- Introduce Kafka/Redpanda for high-volume event pipelines.

## Bonus: add a new provider with minimal changes

1. Implement new adapter file (e.g., `providers/mistral_adapter.py`) conforming to `ProviderAdapter`.
2. Register adapter in `providers/registry.py`.
3. Add models + pricing rows in `model_catalog.yaml` and pricing table.
4. No orchestrator or routing engine code changes required.

## Bonus: orchestrator and routing pseudo-code

```python
# orchestrator/service.py
async def handle_chat(req: CanonicalRequest):
    est_tokens = tokenizer.estimate(req)
    allowed, rl_meta = await rate_limiter.check_and_consume(req.tenant_id, req.api_key_id, est_tokens)
    if not allowed:
        raise RateLimitExceeded(rl_meta)

    candidates = await routing_strategy.rank_candidates(req)
    attempts = []

    for c in candidates:
        adapter = provider_registry.get(c.provider)
        try:
            with timeout(c.timeout_ms):
                if req.stream:
                    async for event in adapter.stream_chat(req):
                        yield stream_normalizer(event, c)
                    return
                else:
                    resp = await adapter.chat(req)
                    await usage_ledger.record_success(req, resp, c)
                    return resp
        except RetryableProviderError as e:
            attempts.append((c, str(e)))
            await retry_policy.sleep_next_backoff(len(attempts))
            continue

    await usage_ledger.record_failure(req, attempts)
    raise UpstreamUnavailable(attempts)
```

```python
# routing/strategies/balanced.py
async def rank_candidates(req):
    pool = await catalog.get_candidates(req.model_hint, tenant_id=req.tenant_id)
    scored = []
    for m in pool:
        latency = await metrics.p95_latency(m)
        err_rate = await metrics.error_rate(m)
        price = await pricing.estimated_cost_per_1k(m)

        score = (
            0.45 * normalize_cost(price)
            + 0.35 * normalize_latency(latency)
            + 0.20 * normalize_health(err_rate)
        )
        scored.append((score, m))

    ranked = [m for _, m in sorted(scored, key=lambda x: x[0])]
    return ranked
```
