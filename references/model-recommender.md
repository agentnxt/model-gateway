# Model Recommender — Autonomyx LLM Gateway

## Architecture

```
Client POST /recommend
  → recommender.py (FastAPI router mounted on LiteLLM)
      ├── reads LiteLLM Postgres   (key spend, budget, reset period)
      ├── reads Lago API           (current period usage, invoice state)
      ├── reads Prometheus         (request rate, latency p95, error rate)
      └── infers task type from prompt (Claude claude-haiku-4-5 — fast, cheap)
          → returns ranked model list with fit scores
```

Mounted as a custom router on LiteLLM proxy — no separate service needed.

---

## docker-compose addition

Mount the recommender alongside the LiteLLM config:

```yaml
  litellm:
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./lago_callback.py:/app/lago_callback.py:ro
      - ./recommender.py:/app/recommender.py:ro        # ADD
      - ./model_registry.json:/app/model_registry.json:ro  # ADD
    environment:
      - RECOMMENDER_INFERENCE_MODEL=claude-haiku-4-5-20251001
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - PROMETHEUS_URL=http://prometheus:9090
      - LAGO_API_URL=${LAGO_API_URL}
      - LAGO_API_KEY=${LAGO_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
```

Register in `config.yaml`:
```yaml
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL
  custom_auth: recommender.custom_auth          # optional: protect /recommend
  additional_routers:
    - recommender.router
```

---

## `model_registry.json`

Capability + cost metadata for every model in the gateway.
**Update this whenever you add or remove models from config.yaml.**

```json
{
  "models": [
    {
      "alias": "ollama/llama3",
      "provider": "local",
      "cost_per_1k_input": 0.0,
      "cost_per_1k_output": 0.0,
      "context_window": 8192,
      "capabilities": ["chat", "summarise", "extract"],
      "quality_score": 3,
      "latency_tier": "medium",
      "private": true
    },
    {
      "alias": "ollama/mistral",
      "provider": "local",
      "cost_per_1k_input": 0.0,
      "cost_per_1k_output": 0.0,
      "context_window": 32768,
      "capabilities": ["chat", "summarise", "code", "extract"],
      "quality_score": 3,
      "latency_tier": "medium",
      "private": true
    },
    {
      "alias": "vllm/llama3-70b",
      "provider": "local",
      "cost_per_1k_input": 0.0,
      "cost_per_1k_output": 0.0,
      "context_window": 8192,
      "capabilities": ["chat", "code", "summarise", "reason", "extract"],
      "quality_score": 4,
      "latency_tier": "slow",
      "private": true
    },
    {
      "alias": "groq/llama3-70b",
      "provider": "groq",
      "cost_per_1k_input": 0.00059,
      "cost_per_1k_output": 0.00079,
      "context_window": 8192,
      "capabilities": ["chat", "code", "summarise", "reason", "extract"],
      "quality_score": 4,
      "latency_tier": "fast"
    },
    {
      "alias": "groq/mixtral",
      "provider": "groq",
      "cost_per_1k_input": 0.00024,
      "cost_per_1k_output": 0.00024,
      "context_window": 32768,
      "capabilities": ["chat", "summarise", "extract"],
      "quality_score": 3,
      "latency_tier": "fast"
    },
    {
      "alias": "mistral-small",
      "provider": "mistral",
      "cost_per_1k_input": 0.001,
      "cost_per_1k_output": 0.003,
      "context_window": 128000,
      "capabilities": ["chat", "summarise", "extract", "code"],
      "quality_score": 3,
      "latency_tier": "fast"
    },
    {
      "alias": "mistral-large",
      "provider": "mistral",
      "cost_per_1k_input": 0.003,
      "cost_per_1k_output": 0.009,
      "context_window": 128000,
      "capabilities": ["chat", "code", "reason", "summarise", "extract", "vision"],
      "quality_score": 5,
      "latency_tier": "medium"
    },
    {
      "alias": "together/llama3-70b",
      "provider": "together",
      "cost_per_1k_input": 0.0009,
      "cost_per_1k_output": 0.0009,
      "context_window": 8192,
      "capabilities": ["chat", "code", "summarise", "reason"],
      "quality_score": 4,
      "latency_tier": "medium"
    },
    {
      "alias": "fireworks/llama3-70b",
      "provider": "fireworks",
      "cost_per_1k_input": 0.0009,
      "cost_per_1k_output": 0.0009,
      "context_window": 8192,
      "capabilities": ["chat", "code", "summarise", "reason"],
      "quality_score": 4,
      "latency_tier": "fast"
    },
    {
      "alias": "gpt-4o-mini",
      "provider": "openai",
      "cost_per_1k_input": 0.00015,
      "cost_per_1k_output": 0.0006,
      "context_window": 128000,
      "capabilities": ["chat", "summarise", "extract", "code", "vision"],
      "quality_score": 4,
      "latency_tier": "fast"
    },
    {
      "alias": "gpt-4o",
      "provider": "openai",
      "cost_per_1k_input": 0.0025,
      "cost_per_1k_output": 0.01,
      "context_window": 128000,
      "capabilities": ["chat", "code", "reason", "summarise", "extract", "vision"],
      "quality_score": 5,
      "latency_tier": "medium"
    },
    {
      "alias": "claude-3-haiku",
      "provider": "anthropic",
      "cost_per_1k_input": 0.00025,
      "cost_per_1k_output": 0.00125,
      "context_window": 200000,
      "capabilities": ["chat", "summarise", "extract", "code"],
      "quality_score": 3,
      "latency_tier": "fast"
    },
    {
      "alias": "claude-3-5-sonnet",
      "provider": "anthropic",
      "cost_per_1k_input": 0.003,
      "cost_per_1k_output": 0.015,
      "context_window": 200000,
      "capabilities": ["chat", "code", "reason", "summarise", "extract", "vision", "agent"],
      "quality_score": 5,
      "latency_tier": "medium"
    },
    {
      "alias": "gemini-1.5-flash",
      "provider": "google",
      "cost_per_1k_input": 0.000075,
      "cost_per_1k_output": 0.0003,
      "context_window": 1000000,
      "capabilities": ["chat", "summarise", "extract", "vision", "long_context"],
      "quality_score": 3,
      "latency_tier": "fast"
    },
    {
      "alias": "gemini-1.5-pro",
      "provider": "google",
      "cost_per_1k_input": 0.00125,
      "cost_per_1k_output": 0.005,
      "context_window": 2000000,
      "capabilities": ["chat", "code", "reason", "summarise", "extract", "vision", "long_context"],
      "quality_score": 5,
      "latency_tier": "medium"
    },
    {
      "alias": "azure-gpt-4o",
      "provider": "azure",
      "cost_per_1k_input": 0.0025,
      "cost_per_1k_output": 0.01,
      "context_window": 128000,
      "capabilities": ["chat", "code", "reason", "summarise", "extract", "vision"],
      "quality_score": 5,
      "latency_tier": "medium"
    },
    {
      "alias": "bedrock-claude-3",
      "provider": "bedrock",
      "cost_per_1k_input": 0.003,
      "cost_per_1k_output": 0.015,
      "context_window": 200000,
      "capabilities": ["chat", "code", "reason", "summarise", "extract"],
      "quality_score": 5,
      "latency_tier": "medium"
    },
    {
      "alias": "openrouter/auto",
      "provider": "openrouter",
      "cost_per_1k_input": 0.0,
      "cost_per_1k_output": 0.0,
      "context_window": 200000,
      "capabilities": ["chat", "code", "reason", "summarise", "extract", "vision"],
      "quality_score": 5,
      "latency_tier": "medium",
      "note": "cost varies — openrouter routes to cheapest available"
    }
  ]
}
```

---

## `recommender.py`

```python
"""
Autonomyx LLM Gateway — Model Recommender
POST /recommend

Infers task type from prompt content (via Claude Haiku).
Reads budget state from LiteLLM Postgres + Lago + Prometheus.
Returns ranked model list with fit scores.
"""

import os, json, math, httpx, asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncpg
import anthropic

router = APIRouter()

# ── Config ────────────────────────────────────────────────────────────────
REGISTRY_PATH   = "/app/model_registry.json"
DB_URL          = os.environ["DATABASE_URL"]
LAGO_URL        = os.environ.get("LAGO_API_URL", "")
LAGO_KEY        = os.environ.get("LAGO_API_KEY", "")
PROMETHEUS_URL  = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
INFER_MODEL     = os.environ.get("RECOMMENDER_INFERENCE_MODEL", "claude-haiku-4-5-20251001")
MASTER_KEY      = os.environ.get("LITELLM_MASTER_KEY", "")

TASK_TYPES = ["chat", "code", "reason", "summarise", "extract", "vision", "long_context", "agent"]

# ── Models ────────────────────────────────────────────────────────────────
class RecommendRequest(BaseModel):
    prompt: str
    virtual_key: str                    # LiteLLM key alias or key value
    top_n: Optional[int] = 3
    require_private: Optional[bool] = False   # only local/self-hosted models

class ModelRecommendation(BaseModel):
    alias: str
    provider: str
    fit_score: float                    # 0–100
    reasons: list[str]
    estimated_cost_usd: Optional[float]
    budget_remaining_usd: float
    tokens_remaining: Optional[int]
    reset_in_hours: Optional[float]
    quality_score: int
    latency_tier: str
    capabilities: list[str]

class RecommendResponse(BaseModel):
    task_type: str
    task_confidence: float
    recommendations: list[ModelRecommendation]
    budget_state: dict

# ── Registry ──────────────────────────────────────────────────────────────
def load_registry() -> list[dict]:
    with open(REGISTRY_PATH) as f:
        return json.load(f)["models"]

# ── Task inference ─────────────────────────────────────────────────────────
async def infer_task(prompt: str) -> tuple[str, float]:
    """Use Claude Haiku to classify the task type from prompt content."""
    client = anthropic.AsyncAnthropic()
    system = (
        f"Classify the user prompt into exactly ONE task type from this list: {TASK_TYPES}. "
        "Reply with a JSON object: {\"task\": \"<type>\", \"confidence\": <0.0-1.0>}. "
        "No explanation. Only JSON."
    )
    try:
        resp = await client.messages.create(
            model=INFER_MODEL,
            max_tokens=64,
            system=system,
            messages=[{"role": "user", "content": prompt[:1000]}],  # trim for speed
        )
        data = json.loads(resp.content[0].text)
        return data.get("task", "chat"), float(data.get("confidence", 0.7))
    except Exception:
        return "chat", 0.5

# ── Budget state from LiteLLM Postgres ────────────────────────────────────
async def get_litellm_budget(key_alias: str) -> dict:
    """
    Returns: spend, max_budget, budget_duration, reset_at (ISO), tokens_used
    """
    try:
        conn = await asyncpg.connect(DB_URL)
        row = await conn.fetchrow(
            """
            SELECT spend, max_budget, budget_duration, budget_reset_at,
                   total_tokens, max_parallel_requests
            FROM "LiteLLM_VerificationToken"
            WHERE key_alias = $1
            LIMIT 1
            """,
            key_alias,
        )
        await conn.close()
        if not row:
            return {}
        reset_at = row["budget_reset_at"]
        now = datetime.now(timezone.utc)
        reset_in_hours = None
        if reset_at:
            delta = reset_at.replace(tzinfo=timezone.utc) - now
            reset_in_hours = max(0.0, delta.total_seconds() / 3600)
        return {
            "spend": float(row["spend"] or 0),
            "max_budget": float(row["max_budget"] or 0),
            "budget_duration": row["budget_duration"],
            "reset_in_hours": reset_in_hours,
            "tokens_used": int(row["total_tokens"] or 0),
        }
    except Exception as e:
        return {"error": str(e)}

# ── Usage from Lago ────────────────────────────────────────────────────────
async def get_lago_usage(key_alias: str) -> dict:
    """Returns current period token usage and charges from Lago."""
    if not LAGO_URL or not LAGO_KEY:
        return {}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"{LAGO_URL}/api/v1/customers/{key_alias}/current_usage",
                headers={"Authorization": f"Bearer {LAGO_KEY}"},
            )
            if r.status_code != 200:
                return {}
            data = r.json().get("customer_usage", {})
            charges = data.get("charges_usage", [])
            total_input = sum(
                c.get("units", 0) for c in charges
                if "input" in c.get("billable_metric", {}).get("code", "")
            )
            total_output = sum(
                c.get("units", 0) for c in charges
                if "output" in c.get("billable_metric", {}).get("code", "")
            )
            return {
                "lago_input_tokens": int(total_input),
                "lago_output_tokens": int(total_output),
                "lago_amount_cents": data.get("total_amount_cents", 0),
                "lago_currency": data.get("currency", "USD"),
            }
    except Exception:
        return {}

# ── Latency + error rate from Prometheus ──────────────────────────────────
async def get_prometheus_metrics(alias: str) -> dict:
    """Fetches p95 latency and error rate for a model alias from Prometheus."""
    if not PROMETHEUS_URL:
        return {}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            # p95 latency
            q_latency = f'histogram_quantile(0.95, rate(litellm_request_duration_seconds_bucket{{model="{alias}"}}[5m]))'
            r_lat = await client.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": q_latency},
            )
            lat_val = None
            if r_lat.status_code == 200:
                result = r_lat.json().get("data", {}).get("result", [])
                if result:
                    lat_val = float(result[0]["value"][1])

            # error rate
            q_err = f'rate(litellm_request_total{{model="{alias}", status="error"}}[5m])'
            r_err = await client.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": q_err},
            )
            err_val = None
            if r_err.status_code == 200:
                result = r_err.json().get("data", {}).get("result", [])
                if result:
                    err_val = float(result[0]["value"][1])

            return {"p95_latency_s": lat_val, "error_rate": err_val}
    except Exception:
        return {}

# ── Scoring ────────────────────────────────────────────────────────────────
def score_model(
    model: dict,
    task_type: str,
    budget_remaining: float,
    prompt_len: int,
    prom_metrics: dict,
    require_private: bool,
) -> tuple[float, list[str]]:
    """
    Returns (fit_score 0-100, reasons[]).
    Weights: capability 40 | cost-efficiency 30 | latency/reliability 20 | privacy 10
    """
    score = 0.0
    reasons = []

    # Hard filter: private required
    if require_private and not model.get("private", False):
        return -1.0, ["excluded: not a private/local model"]

    # Hard filter: capability match
    caps = model.get("capabilities", [])
    if task_type not in caps:
        return -1.0, [f"excluded: does not support task '{task_type}'"]

    # Hard filter: context window
    if model.get("context_window", 0) < prompt_len:
        return -1.0, [f"excluded: context window {model['context_window']} < prompt length {prompt_len}"]

    # ── Capability score (40 pts) ──
    cap_score = model.get("quality_score", 3) / 5 * 40
    score += cap_score
    reasons.append(f"quality {model.get('quality_score')}/5 for '{task_type}'")

    # ── Cost-efficiency score (30 pts) ──
    cost_per_1k = model.get("cost_per_1k_input", 0) + model.get("cost_per_1k_output", 0)
    if cost_per_1k == 0:
        cost_score = 30  # local/free
        reasons.append("free (local model)")
    else:
        # Normalise: cheapest possible ~0.00015, expensive ~0.025
        cost_score = max(0, 30 * (1 - math.log10(max(cost_per_1k, 0.00001) + 1) / math.log10(0.026)))
        est_cost = cost_per_1k * (prompt_len / 750)  # rough token estimate
        if budget_remaining > 0 and est_cost > budget_remaining:
            return -1.0, [f"excluded: estimated cost ${est_cost:.4f} exceeds remaining budget ${budget_remaining:.4f}"]
        reasons.append(f"~${cost_per_1k:.5f}/1k tokens")
    score += cost_score

    # ── Latency/reliability score (20 pts) ──
    latency_map = {"fast": 20, "medium": 13, "slow": 6}
    lat_base = latency_map.get(model.get("latency_tier", "medium"), 13)
    p95 = prom_metrics.get("p95_latency_s")
    err = prom_metrics.get("error_rate", 0) or 0
    latency_penalty = min(10, err * 100)  # up to -10 pts for errors
    lat_score = max(0, lat_base - latency_penalty)
    score += lat_score
    if p95:
        reasons.append(f"p95 latency {p95:.1f}s")
    if err and err > 0.01:
        reasons.append(f"error rate {err*100:.1f}%")

    # ── Privacy bonus (10 pts) ──
    if model.get("private", False):
        score += 10
        reasons.append("private/local — data stays on VPS")

    return round(score, 1), reasons

# ── Main endpoint ──────────────────────────────────────────────────────────
@router.post("/recommend", response_model=RecommendResponse)
async def recommend(
    body: RecommendRequest,
    authorization: str = Header(default=""),
):
    # Auth: accept master key or any valid bearer
    bearer = authorization.replace("Bearer ", "").strip()
    if bearer not in (MASTER_KEY,) and not bearer:
        raise HTTPException(status_code=401, detail="Unauthorized")

    registry = load_registry()
    prompt_len = len(body.prompt)   # chars; rough proxy for tokens

    # Parallel fetch: task inference + budget state + lago usage
    task_type, confidence, litellm_budget, lago_usage = await asyncio.gather(
        infer_task(body.prompt),
        asyncio.coroutine(lambda: None)(),  # placeholder
        get_litellm_budget(body.virtual_key),
        get_lago_usage(body.virtual_key),
    )
    # Re-run correctly (gather doesn't unpack tuples from infer_task)
    task_type, confidence = await infer_task(body.prompt)
    litellm_budget, lago_usage = await asyncio.gather(
        get_litellm_budget(body.virtual_key),
        get_lago_usage(body.virtual_key),
    )

    spend = litellm_budget.get("spend", 0)
    max_budget = litellm_budget.get("max_budget", 0)
    budget_remaining = max(0.0, max_budget - spend)
    reset_in_hours = litellm_budget.get("reset_in_hours")
    tokens_used = litellm_budget.get("tokens_used", 0)

    # Fetch Prometheus metrics for all models in parallel
    prom_tasks = {m["alias"]: get_prometheus_metrics(m["alias"]) for m in registry}
    prom_results = await asyncio.gather(*prom_tasks.values())
    prom_map = dict(zip(prom_tasks.keys(), prom_results))

    # Score all models
    scored = []
    for model in registry:
        fit_score, reasons = score_model(
            model, task_type, budget_remaining,
            prompt_len, prom_map.get(model["alias"], {}),
            body.require_private,
        )
        if fit_score < 0:
            continue

        cost_per_1k = model.get("cost_per_1k_input", 0) + model.get("cost_per_1k_output", 0)
        est_cost = cost_per_1k * (prompt_len / 750) if cost_per_1k > 0 else 0.0

        # Estimate tokens remaining by cost
        tokens_remaining = None
        if cost_per_1k > 0 and budget_remaining > 0:
            tokens_remaining = int((budget_remaining / cost_per_1k) * 1000)

        scored.append(ModelRecommendation(
            alias=model["alias"],
            provider=model["provider"],
            fit_score=fit_score,
            reasons=reasons,
            estimated_cost_usd=round(est_cost, 6) if est_cost else None,
            budget_remaining_usd=round(budget_remaining, 4),
            tokens_remaining=tokens_remaining,
            reset_in_hours=round(reset_in_hours, 2) if reset_in_hours else None,
            quality_score=model.get("quality_score", 3),
            latency_tier=model.get("latency_tier", "medium"),
            capabilities=model.get("capabilities", []),
        ))

    # Sort by fit_score desc
    scored.sort(key=lambda x: x.fit_score, reverse=True)

    budget_state = {
        "spend_usd": round(spend, 4),
        "max_budget_usd": round(max_budget, 4),
        "remaining_usd": round(budget_remaining, 4),
        "budget_duration": litellm_budget.get("budget_duration"),
        "reset_in_hours": round(reset_in_hours, 2) if reset_in_hours else None,
        "tokens_used_total": tokens_used,
        "lago_input_tokens": lago_usage.get("lago_input_tokens"),
        "lago_output_tokens": lago_usage.get("lago_output_tokens"),
        "lago_spend_cents": lago_usage.get("lago_amount_cents"),
    }

    return RecommendResponse(
        task_type=task_type,
        task_confidence=round(confidence, 2),
        recommendations=scored[: body.top_n],
        budget_state=budget_state,
    )
```

---

## Request / Response example

```bash
curl -X POST http://localhost:4000/recommend \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a Python function that parses JSON from a REST API and handles rate limiting with exponential backoff",
    "virtual_key": "langflow-prod",
    "top_n": 3,
    "require_private": false
  }'
```

```json
{
  "task_type": "code",
  "task_confidence": 0.94,
  "recommendations": [
    {
      "alias": "claude-3-5-sonnet",
      "provider": "anthropic",
      "fit_score": 87.5,
      "reasons": ["quality 5/5 for 'code'", "~$0.018/1k tokens", "p95 latency 1.2s"],
      "estimated_cost_usd": 0.000024,
      "budget_remaining_usd": 6.42,
      "tokens_remaining": 357000,
      "reset_in_hours": 312.5,
      "quality_score": 5,
      "latency_tier": "medium",
      "capabilities": ["chat","code","reason","summarise","extract","vision","agent"]
    },
    {
      "alias": "gpt-4o",
      "provider": "openai",
      "fit_score": 82.1,
      "reasons": ["quality 5/5 for 'code'", "~$0.0125/1k tokens", "p95 latency 0.9s"],
      "estimated_cost_usd": 0.000016,
      "budget_remaining_usd": 6.42,
      "tokens_remaining": 513600,
      "reset_in_hours": 312.5,
      "quality_score": 5,
      "latency_tier": "medium",
      "capabilities": ["chat","code","reason","summarise","extract","vision"]
    },
    {
      "alias": "vllm/llama3-70b",
      "provider": "local",
      "fit_score": 74.0,
      "reasons": ["quality 4/5 for 'code'", "free (local model)", "private/local — data stays on VPS"],
      "estimated_cost_usd": 0.0,
      "budget_remaining_usd": 6.42,
      "tokens_remaining": null,
      "reset_in_hours": 312.5,
      "quality_score": 4,
      "latency_tier": "slow",
      "capabilities": ["chat","code","summarise","reason","extract"]
    }
  ],
  "budget_state": {
    "spend_usd": 3.58,
    "max_budget_usd": 10.0,
    "remaining_usd": 6.42,
    "budget_duration": "30d",
    "reset_in_hours": 312.5,
    "tokens_used_total": 1842300,
    "lago_input_tokens": 1204100,
    "lago_output_tokens": 638200,
    "lago_spend_cents": 358
  }
}
```

---

## Scoring breakdown

| Dimension | Weight | Signal |
|---|---|---|
| Capability match | 40 pts | quality_score × task_type match |
| Cost efficiency | 30 pts | log-normalised cost/1k vs budget remaining |
| Latency + reliability | 20 pts | latency_tier + Prometheus p95 + error rate |
| Privacy (local) | 10 pts | model.private == true |

Hard exclusions (score = -1, model dropped):
- Task type not in model capabilities
- Prompt length exceeds context window
- Estimated cost exceeds remaining budget
- `require_private=true` and model is not local

---

## Env vars (add to .env.example)

```
# Model Recommender
RECOMMENDER_INFERENCE_MODEL=claude-haiku-4-5-20251001
PROMETHEUS_URL=http://prometheus:9090
```

---

## Wiring into Langflow

In any Langflow flow, add an **HTTP Request** node before the LLM node:

```
POST http://litellm:4000/recommend
body: { "prompt": "{user_input}", "virtual_key": "langflow-prod", "top_n": 1 }
→ extract recommendations[0].alias
→ pass as model_name to OpenAI component
```

Langflow flow automatically uses the cheapest capable model given current budget.

---

## Wiring into autonomyx-mcp

```python
import httpx

async def get_best_model(prompt: str, key_alias: str) -> str:
    r = httpx.post(
        "http://litellm:4000/recommend",
        headers={"Authorization": f"Bearer {LITELLM_MASTER_KEY}"},
        json={"prompt": prompt, "virtual_key": key_alias, "top_n": 1},
        timeout=5,
    )
    recs = r.json().get("recommendations", [])
    return recs[0]["alias"] if recs else "gpt-4o-mini"

# In MCP tool:
model = await get_best_model(user_prompt, "autonomyx-mcp-prod")
response = client.chat.completions.create(model=model, messages=[...])
```
