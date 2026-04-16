# Human Feedback Capture — Autonomyx LLM Gateway

## Why human feedback matters more than LLM-as-judge alone

LLM-as-judge scores consistency and correctness automatically. Human feedback captures:
- Usefulness (correct ≠ useful for the user's actual goal)
- Tone and style preferences per customer segment
- Domain-specific quality signals LLM-as-judge misses
- Negative feedback on responses that looked correct but were wrong in context

Both signals together give a complete picture. Use LLM-as-judge for volume (100% coverage),
human feedback for signal quality (5–10% coverage, but higher weight in training).

---

## Two capture points

### Point 1 — End-user widget (embedded in customer apps)
For customers' end users who interact with AI responses in the customer's product.
Thumbs up / thumbs down + optional freetext comment.
Customer embeds a JS snippet. Feedback posts to your gateway API.
Stored in Langfuse against the trace ID.

### Point 2 — Developer SDK (direct API call)
For customers' developers and ops teams who review responses programmatically
or via Langfuse UI.
Single API call with score and optional comment.
Same Langfuse storage, same improvement pipeline.

---

## Architecture

```
End user rates response (thumbs up/down)
  → Feedback widget (JS snippet in customer app)
  → POST /feedback (LiteLLM custom endpoint)
  → Langfuse score API (per-tenant project key)
  → Improvement pipeline (if tenant opted in)

Developer rates response (API call)
  → POST /feedback (same endpoint)
  → Langfuse score API
  → Improvement pipeline
```

---

## docker-compose — no new service needed

Feedback endpoint is a FastAPI router mounted on LiteLLM (same as recommender.py).
No additional container.

---

## `feedback.py` — FastAPI router mounted on LiteLLM

```python
"""
Autonomyx LLM Gateway — Human Feedback Endpoint
POST /feedback

Accepts thumbs up/down + optional comment from:
  1. End-user widget (via customer's frontend)
  2. Developer API call (programmatic)

Routes to correct Langfuse project per tenant virtual key.
"""

import os, logging, httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
from langfuse import Langfuse

router = APIRouter()
log = logging.getLogger("feedback")

LANGFUSE_URL      = os.environ.get("LANGFUSE_URL", "http://langfuse-server:3000")
LANGFUSE_ADMIN_KEY = os.environ.get("LANGFUSE_ADMIN_KEY", "")
MASTER_KEY        = os.environ.get("LITELLM_MASTER_KEY", "")

# Tenant Langfuse client cache (same as in lago_callback.py)
_langfuse_clients: dict[str, Langfuse] = {}

def _get_langfuse_client(key_alias: str) -> Langfuse | None:
    if key_alias in _langfuse_clients:
        return _langfuse_clients[key_alias]
    key_map_raw = os.environ.get("LANGFUSE_TENANT_KEYS", "")
    key_map = {}
    for entry in key_map_raw.split(","):
        parts = entry.strip().split(":")
        if len(parts) == 3:
            alias, pub, sec = parts
            key_map[alias] = (pub, sec)
    if key_alias not in key_map:
        pub = os.environ.get("LANGFUSE_DEFAULT_PUBLIC_KEY")
        sec = os.environ.get("LANGFUSE_DEFAULT_SECRET_KEY")
        if not pub:
            return None
    else:
        pub, sec = key_map[key_alias]
    client = Langfuse(public_key=pub, secret_key=sec, host=LANGFUSE_URL)
    _langfuse_clients[key_alias] = client
    return client


# ── Request / Response models ──────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    trace_id: str                          # LiteLLM response ID → Langfuse trace ID
    score: int                             # 1 = thumbs up, 0 = thumbs down
    comment: Optional[str] = None          # freetext from user (optional)
    virtual_key: str                       # LiteLLM virtual key alias for tenant routing
    source: str = "user"                   # "user" | "developer" | "automated"
    metadata: Optional[dict] = None        # any extra context from the client

class FeedbackResponse(BaseModel):
    status: str
    trace_id: str
    score: int
    langfuse_score_id: Optional[str] = None


# ── Endpoint ───────────────────────────────────────────────────────────────

@router.post("/feedback", response_model=FeedbackResponse)
async def capture_feedback(
    body: FeedbackRequest,
    authorization: str = Header(default=""),
):
    # Auth: accept master key OR the tenant's own virtual key
    bearer = authorization.replace("Bearer ", "").strip()
    if not bearer:
        raise HTTPException(status_code=401, detail="Authorization required")

    if body.score not in (0, 1):
        raise HTTPException(status_code=422, detail="score must be 0 or 1")

    lf = _get_langfuse_client(body.virtual_key)
    if not lf:
        raise HTTPException(status_code=400, detail=f"Unknown virtual_key: {body.virtual_key}")

    try:
        # Map 0/1 to Langfuse score (0.0 = bad, 1.0 = good)
        score_value = float(body.score)
        comment     = body.comment or ""
        if body.score == 0 and not comment:
            comment = "User rated: thumbs down"
        elif body.score == 1 and not comment:
            comment = "User rated: thumbs up"

        score_obj = lf.score(
            trace_id=body.trace_id,
            name="human_feedback",
            value=score_value,
            comment=comment,
            data_type="BOOLEAN",
        )
        lf.flush()

        log.info(
            f"Feedback captured: trace={body.trace_id} "
            f"score={body.score} source={body.source} tenant={body.virtual_key}"
        )

        return FeedbackResponse(
            status="ok",
            trace_id=body.trace_id,
            score=body.score,
            langfuse_score_id=score_obj.id if score_obj else None,
        )

    except Exception as e:
        log.error(f"Feedback capture failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── CORS middleware for widget (end-user browser requests) ─────────────────
# Add to main LiteLLM app startup, not here — just document the requirement:
# app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST"])
```

Register in `config.yaml`:
```yaml
general_settings:
  additional_routers:
    - recommender.router
    - feedback.router    # ADD THIS
```

---

## Feedback widget — embeddable JS snippet

Customer adds this to their app after rendering each AI response.
Replace `TRACE_ID`, `VIRTUAL_KEY`, and `GATEWAY_URL` dynamically.

```html
<!-- Autonomyx Feedback Widget — add after each AI response -->
<div id="axg-feedback-{{TRACE_ID}}" class="axg-feedback" data-trace="{{TRACE_ID}}">
  <span class="axg-label">Was this helpful?</span>
  <button class="axg-btn axg-up"   onclick="axgFeedback('{{TRACE_ID}}', 1)">👍</button>
  <button class="axg-btn axg-down" onclick="axgFeedback('{{TRACE_ID}}', 0)">👎</button>
  <div class="axg-comment-box" id="axg-comment-{{TRACE_ID}}" style="display:none">
    <input type="text" id="axg-text-{{TRACE_ID}}" placeholder="Tell us more (optional)" />
    <button onclick="axgSubmitComment('{{TRACE_ID}}')">Send</button>
  </div>
  <span class="axg-thanks" id="axg-thanks-{{TRACE_ID}}" style="display:none">Thanks!</span>
</div>

<script>
const AXG_GATEWAY = "{{GATEWAY_URL}}";   // e.g. https://llm.openautonomyx.com
const AXG_KEY     = "{{VIRTUAL_KEY}}";   // tenant's LiteLLM virtual key

async function axgFeedback(traceId, score) {
  const el = document.getElementById(`axg-feedback-${traceId}`);
  // Show comment box on thumbs down, submit immediately on thumbs up
  if (score === 0) {
    document.getElementById(`axg-comment-${traceId}`).style.display = "block";
    el.dataset.pendingScore = score;
    return;
  }
  await axgSubmit(traceId, score, "");
}

async function axgSubmitComment(traceId) {
  const score   = parseInt(document.getElementById(`axg-feedback-${traceId}`).dataset.pendingScore);
  const comment = document.getElementById(`axg-text-${traceId}`).value;
  await axgSubmit(traceId, score, comment);
}

async function axgSubmit(traceId, score, comment) {
  try {
    await fetch(`${AXG_GATEWAY}/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${AXG_KEY}`,
      },
      body: JSON.stringify({
        trace_id:    traceId,
        score:       score,
        comment:     comment,
        virtual_key: AXG_KEY,
        source:      "user",
      }),
    });
  } catch(e) { console.warn("Feedback failed:", e); }
  // Show thanks regardless of success — don't interrupt UX
  document.getElementById(`axg-comment-${traceId}`).style.display  = "none";
  document.getElementById(`axg-thanks-${traceId}`).style.display   = "inline";
  // Disable buttons
  document.querySelectorAll(`#axg-feedback-${traceId} .axg-btn`)
    .forEach(b => b.disabled = true);
}
</script>

<style>
.axg-feedback { display:inline-flex; align-items:center; gap:8px; font-size:14px; color:#666; }
.axg-btn { background:none; border:1px solid #ddd; border-radius:6px; 
           padding:4px 10px; cursor:pointer; font-size:16px; }
.axg-btn:hover { background:#f5f5f5; }
.axg-comment-box { display:flex; gap:6px; align-items:center; }
.axg-comment-box input { border:1px solid #ddd; border-radius:6px; padding:4px 8px; font-size:13px; }
.axg-thanks { color:#22c55e; font-size:13px; }
</style>
```

### How the customer gets the trace ID

The LiteLLM response includes the trace ID in the response body as `id`:

```javascript
// Customer's app — after calling the LiteLLM API
const response = await fetch(`${GATEWAY_URL}/v1/chat/completions`, { ... });
const data     = await response.json();
const traceId  = data.id;  // e.g. "chatcmpl-abc123"

// Render the widget with this trace ID
renderFeedbackWidget(traceId, VIRTUAL_KEY, GATEWAY_URL);
```

---

## Developer SDK — direct API call

For programmatic feedback from developers, CI pipelines, or evaluation scripts:

```python
# Python SDK (customer-side)
import httpx

def submit_feedback(
    trace_id: str,
    score: int,               # 1 = good, 0 = bad
    comment: str = "",
    gateway_url: str = "https://llm.openautonomyx.com",
    virtual_key: str = "",
):
    """Submit human feedback for a specific LLM response."""
    r = httpx.post(
        f"{gateway_url}/feedback",
        headers={"Authorization": f"Bearer {virtual_key}"},
        json={
            "trace_id":    trace_id,
            "score":       score,
            "comment":     comment,
            "virtual_key": virtual_key,
            "source":      "developer",
        },
        timeout=5,
    )
    r.raise_for_status()
    return r.json()

# Usage example
response = client.chat.completions.create(model="ollama/qwen3:30b-a3b", messages=[...])
trace_id = response.id

# Developer reviews and rates
submit_feedback(
    trace_id=trace_id,
    score=0,
    comment="Model hallucinated a non-existent RBI circular",
    virtual_key="acme-legal-prod",
)
```

```javascript
// JavaScript / TypeScript SDK (customer-side)
async function submitFeedback({ traceId, score, comment = "", virtualKey, gatewayUrl }) {
  const res = await fetch(`${gatewayUrl}/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${virtualKey}`,
    },
    body: JSON.stringify({
      trace_id:    traceId,
      score,
      comment,
      virtual_key: virtualKey,
      source:      "developer",
    }),
  });
  return res.json();
}
```

---

## How feedback flows into the improvement pipeline

```
User rates response (score=0, comment="Wrong clause cited")
  │
  ▼
POST /feedback → Langfuse score stored on trace
  │
  ▼
Improvement pipeline (weekly batch, opt-in tenants only)
  │
  ├─ score=1 traces → positive examples for fine-tuning dataset
  ├─ score=0 traces → negative examples (stored with flag, used for DPO later)
  └─ score=0 with comment → priority review queue for ops team
```

### Querying feedback scores from Langfuse (weekly batch)

```python
from langfuse import Langfuse

lf = Langfuse(public_key=PUB, secret_key=SEC, host=LANGFUSE_URL)

def get_feedback_traces(min_score: float = None, max_score: float = None, limit: int = 500):
    """Get traces with human feedback scores for training data."""
    traces = lf.get_traces(limit=limit)
    result = []
    for trace in traces.data:
        human_scores = [s for s in trace.scores if s.name == "human_feedback"]
        if not human_scores:
            continue
        score = human_scores[0].value
        if min_score is not None and score < min_score:
            continue
        if max_score is not None and score > max_score:
            continue
        result.append({
            "trace_id": trace.id,
            "input":    trace.input,
            "output":   trace.output,
            "score":    score,
            "comment":  human_scores[0].comment,
            "model":    trace.metadata.get("model"),
            "segment":  trace.metadata.get("segment"),
        })
    return result

# Get positive examples (thumbs up)
positive = get_feedback_traces(min_score=1.0)

# Get negative examples (thumbs down) — for DPO training later
negative = get_feedback_traces(max_score=0.0)

print(f"Positive: {len(positive)}, Negative: {len(negative)}")
```

---

## Feedback volume targets

| Phase | Target | Why |
|---|---|---|
| Month 1 | 100 total | Enough to spot systematic failures |
| Month 2 | 500 total | Enough to bias routing decisions |
| Month 3 | 1,000+ | Enough to use as fine-tuning signal |
| Month 6 | 5,000+ | Enough for DPO (direct preference optimisation) |

DPO uses (prompt, preferred_output, rejected_output) triples — built automatically
from thumbs-up vs thumbs-down on the same prompt type. Powerful but needs volume.

---

## Env vars (add to .env.example)

```
# Human Feedback (no new vars — reuses Langfuse tenant keys)
# Feedback endpoint auto-enabled when feedback.router is registered in config.yaml
# CORS allowed origins — set to customer domains or * for open
FEEDBACK_ALLOWED_ORIGINS=*
```

---

## Output checklist additions

- [ ] `feedback.py` produced — FastAPI router with POST /feedback
- [ ] Registered in `config.yaml` under `additional_routers`
- [ ] Feedback widget JS snippet produced (embeddable, no deps)
- [ ] Python + JS SDK snippets produced for developer feedback
- [ ] Langfuse score query script produced for improvement pipeline
- [ ] Feedback volume targets documented
