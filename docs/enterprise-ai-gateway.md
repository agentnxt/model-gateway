# Enterprise AI Gateway Blueprint

This blueprint turns the Autonomyx Model Gateway into an enterprise AI model gateway and control plane, not a simple provider proxy. It is intended for architecture reviews, implementation planning, and audits of new gateway features.

## Core Architecture Principles

- **Control plane first:** authentication, tenant resolution, policy, routing, fallback, observability, and billing are first-class capabilities that cannot be bypassed by request input.
- **Multi-tenant by default:** every request is resolved to a tenant before policy, routing, provider execution, logging, or billing occurs.
- **Centralized policy enforcement:** model access, token caps, rate limits, routing restrictions, and environment rules are defined centrally and enforced before provider calls.
- **Provider-neutral execution:** provider adapters normalize OpenAI, Anthropic, Google, Groq, local Ollama, and future model APIs into canonical request and response contracts.
- **Immutable accountability:** audit, usage, and billing events are structured, append-only, and queryable by tenant, user, model, status, and time range.

## Mandatory Request Pipeline

Every model request must pass through the following stages in this strict order:

1. **Authentication Layer** validates API keys, JWTs, or service tokens.
2. **Tenant Resolver** maps the authenticated principal to `tenant_id`, `user_id`, plan, budget scope, and environment.
3. **Policy Engine** enforces model access, quotas, token caps, routing restrictions, and development or production rules.
4. **Router** selects the best candidate sequence using cost, latency, health, tenant budget, request type, and policy constraints.
5. **Fallback Manager** applies retries, timeout handling, fallback chains, and circuit-breaker state.
6. **Provider Adapter Layer** converts the canonical gateway request into provider-specific API calls.
7. **Model Execution** invokes the selected local or cloud model.
8. **Observability Hook** records structured traces, metrics, logs, and audit events.
9. **Billing Engine** reconciles input tokens, output tokens, total cost, quotas, and tenant budget state.
10. **Response Formatter** returns a stable OpenAI-compatible or gateway-native response shape.

```text
Client / SDK / Workflow
        |
        v
+----------------------+      reject unauthenticated requests
| 1. Authentication    |--------------------------------------+
+----------------------+                                      |
        |                                                     |
        v                                                     |
+----------------------+      attach tenant_id, plan, budget  |
| 2. Tenant Resolver   |--------------------------------------+
+----------------------+                                      |
        |                                                     |
        v                                                     |
+----------------------+      deny non-compliant requests      |
| 3. Policy Engine     |--------------------------------------+
+----------------------+                                      |
        |                                                     |
        v                                                     |
+----------------------+      ranked candidate chain           |
| 4. Router            |--------------------------------------+
+----------------------+                                      |
        |                                                     |
        v                                                     |
+----------------------+      retry, timeout, circuit break    |
| 5. Fallback Manager  |--------------------------------------+
+----------------------+                                      |
        |                                                     |
        v                                                     |
+----------------------+      provider-normalized request      |
| 6. Provider Adapter  |--------------------------------------+
+----------------------+                                      |
        |                                                     |
        v                                                     |
+----------------------+                                      |
| 7. Model Execution   |                                      |
+----------------------+                                      |
        |                                                     |
        v                                                     |
+----------------------+      logs, traces, metrics, audits    |
| 8. Observability     |                                      |
+----------------------+                                      |
        |                                                     |
        v                                                     |
+----------------------+      usage ledger + budget update     |
| 9. Billing Engine    |                                      |
+----------------------+                                      |
        |                                                     |
        v                                                     |
+----------------------+                                      |
| 10. Response Format  |                                      |
+----------------------+                                      |
        |                                                     |
        v                                                     v
      Client                                           Structured denial
```

## Multi-Tenancy Requirements

Every request context must include these fields before entering the policy engine:

| Field | Purpose |
| --- | --- |
| `tenant_id` | Required isolation and billing boundary. |
| `user_id` | Required actor identity for audit and abuse investigations. |
| `api_key_id` or `jwt_subject` | Credential identifier without storing raw secrets in logs. |
| `plan` | Determines quota, budget, model class, and fallback eligibility. |
| `environment` | Applies production, staging, development, or sandbox policies. |
| `budget_scope` | Selects monthly, project, team, or customer budget ledger. |

Tenant isolation must apply to:

- API keys and JWT claims.
- model allowlists and denylists.
- rate-limit counters and token quotas.
- billing ledgers and invoice events.
- traces, logs, and audit events.
- cached routing statistics and request metadata.

## Central Policy Engine

Policies are centrally defined and evaluated before routing. Request input can provide metadata, but it must never override centralized tenant, environment, or model policy.

The policy engine must enforce:

- allowed and blocked models per tenant and plan.
- maximum input, output, and total tokens per request.
- requests-per-minute and tokens-per-minute limits.
- monthly hard and soft budgets.
- data-handling rules such as sensitive or regulated data requiring local-only models.
- production safeguards such as blocking experimental models unless explicitly allowed.
- routing rules that constrain the router candidate set rather than trusting a requested model name.

Recommended decision output:

```json
{
  "allow": true,
  "tenant_id": "tenant_acme",
  "effective_model_policy": {
    "allowed_models": ["qwen3-30b", "qwen2.5-coder-32b", "gpt-4o-mini"],
    "blocked_models": ["openrouter/auto"],
    "local_only": false
  },
  "limits": {
    "max_input_tokens": 32000,
    "max_output_tokens": 4096,
    "rpm": 120,
    "tpm": 250000
  },
  "routing_constraints": {
    "request_type": "code",
    "fallback_allowed": true,
    "cloud_fallback_allowed": true
  },
  "deny_reasons": []
}
```

## Routing Logic

Routing must produce a deterministic, explainable candidate sequence. It should never select a model that the policy engine removed from the candidate set.

Candidate scoring should include:

- provider and model health.
- model capability for the request type (`chat`, `reasoning`, `code`, `vision`, `embedding`, or `structured_output`).
- estimated cost and remaining tenant budget.
- observed latency and timeout rate.
- tenant plan and cloud-fallback eligibility.
- data residency, local-only, or privacy restrictions.

Example route decision:

```json
{
  "route_id": "rt_01HX...",
  "strategy": "balanced",
  "primary_model": "qwen2.5-coder-32b",
  "fallback_chain": ["qwen3-30b", "groq/llama3-70b", "gpt-4o-mini"],
  "decision_factors": {
    "request_type": "code",
    "budget_remaining_usd": 42.18,
    "cloud_fallback_allowed": true,
    "sensitive_data": false
  }
}
```

## Fault Tolerance Requirements

The gateway must implement provider resilience without duplicating client-visible side effects.

- **Fallback chains:** ordered per request type, tenant plan, and policy constraints.
- **Retries:** bounded exponential backoff for retryable errors only.
- **Timeouts:** provider-specific connect, read, and total deadlines.
- **Circuit breakers:** provider and model health state that removes unhealthy candidates from routing until recovery.
- **Idempotency:** client-supplied or generated idempotency keys for safe retry accounting.
- **Partial failure handling:** streaming failures should emit structured terminal errors and reconcile partial usage when possible.

## Observability Contract

Every request must emit structured telemetry with the following minimum fields:

| Field | Description |
| --- | --- |
| `trace_id` | End-to-end correlation identifier. |
| `tenant_id` | Tenant that owns the request and billing event. |
| `user_id` | Authenticated actor or service account. |
| `api_key_id` | Hashed or opaque key identifier. |
| `request_type` | Chat, reasoning, code, embedding, vision, or workflow. |
| `model_requested` | Client-requested model or route hint. |
| `model_used` | Actual model that executed successfully or failed last. |
| `fallback_used` | Boolean plus fallback hop count when applicable. |
| `input_tokens` | Final counted or estimated prompt tokens. |
| `output_tokens` | Final counted completion tokens. |
| `latency_ms` | End-to-end latency visible to the client. |
| `provider_latency_ms` | Provider execution latency excluding gateway overhead. |
| `cost_usd` | Reconciled provider or internal cost. |
| `status` | Success, denied, failed, timeout, cancelled, or fallback_success. |
| `deny_reasons` | Policy denial reasons when blocked. |

Logs and audit events must be JSON or another structured format suitable for indexing.

## Billing, Quotas, and Budget Enforcement

Billing and quota enforcement must occur in both pre-call and post-call stages.

- Pre-call checks estimate maximum possible token usage and budget exposure.
- Post-call reconciliation records actual usage and cost.
- Monthly budgets must support hard and soft thresholds.
- Soft limits can downgrade to cheaper or local models.
- Hard limits must deny or require operator override.
- Usage ledger rows must be append-only and include route, model, tenant, user, token, and cost metadata.

## Security Requirements

- Store API keys only as salted hashes or dedicated KMS/HSM-backed secrets.
- Never log raw API keys, bearer tokens, provider keys, prompts marked sensitive, or credential-bearing headers.
- Require all provider access through gateway-managed credentials.
- Enforce authentication, tenant resolution, and policy before any model call.
- Make audit logs append-only and tamper-evident where possible.
- Treat tenant-provided metadata as untrusted input.
- Keep provider credentials isolated by environment and tenant where required.

## Recommended Module Structure

```text
gateway/
  api/                 # HTTP routes, schemas, response formatting
  auth/                # API key hashing, JWT validation, service principals
  tenants/             # tenant resolver, plans, entitlements
  policy/              # OPA/client policy adapters and policy decision types
  routing/             # scoring, candidate selection, route explanations
  resilience/          # retries, timeouts, circuit breakers, idempotency
  providers/           # OpenAI, Anthropic, Gemini, Groq, Ollama adapters
  observability/       # structured logs, metrics, traces, audit events
  billing/             # usage ledger, quotas, pricing, budget enforcement
  domain/              # canonical request/response/value objects
  storage/             # Postgres, Redis, object storage integrations
  tests/               # contract, policy, routing, resilience, billing tests
```

## Enterprise Readiness Checklist

Use this checklist before calling a change production-ready:

- [ ] Requests cannot reach a provider adapter without authenticated `tenant_id` and evaluated policy.
- [ ] Policy denies are tested for blocked models, token caps, sensitive data, expired tenants, and hard budget limits.
- [ ] Router tests prove denied models never appear in the candidate sequence.
- [ ] Fallback tests prove retries are bounded and circuit breakers suppress unhealthy models.
- [ ] Billing tests prove estimated and actual usage are reconciled with append-only ledger entries.
- [ ] Observability tests prove every success, denial, failure, and fallback emits required structured fields.
- [ ] Security tests prove raw API keys and bearer tokens are never logged.
- [ ] Tenant isolation tests prove one tenant cannot query another tenant's keys, traces, usage, or budgets.
