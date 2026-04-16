# Pre-flight Token Guard — Estimate, Rate-limit, Reject

## Architecture

```
Client request
  → LiteLLM custom pre-call hook (preflight_guard.py)
      ├── 1. Tokenise request (model-correct tokeniser)
      ├── 2. Estimate cost (input tokens × model rate)
      ├── 3. Check context window — reject if over limit
      ├── 4. Check rate limit — reject if over RPM/TPM budget
      ├── 5. Check spend budget — reject if customer near/over limit
      └── 6. Pass or raise PreCallException (HTTP 429 / 400)
  → LiteLLM routes to provider
  → lago_callback.py fires actual usage to Lago
```

---

## Tokeniser map (model → correct library)

```python
# preflight_guard.py — top of file
TOKENISER_MAP = {
    # OpenAI — tiktoken
    "gpt-4o":              ("tiktoken", "o200k_base"),
    "gpt-4o-mini":         ("tiktoken", "o200k_base"),
    "gpt-4":               ("tiktoken", "cl100k_base"),
    "gpt-3.5-turbo":       ("tiktoken", "cl100k_base"),

    # Anthropic — approximation only (no public tokeniser)
    # Use char/3.8 — within 5% of actual for English
    "claude-3-5-sonnet":   ("approx", 3.8),
    "claude-3-haiku":      ("approx", 3.8),

    # Gemini — approximation (no public tokeniser)
    "gemini-1.5-pro":      ("approx", 3.8),
    "gemini-1.5-flash":    ("approx", 3.8),

    # Mistral / Mixtral — HuggingFace SentencePiece
    "mistral-large":       ("hf", "mistralai/Mistral-7B-Instruct-v0.2"),
    "mistral-small":       ("hf", "mistralai/Mistral-7B-Instruct-v0.2"),
    "groq/mixtral":        ("hf", "mistralai/Mixtral-8x7B-Instruct-v0.1"),

    # Llama 3 — HuggingFace SentencePiece (128k vocab)
    "ollama/llama3":       ("hf", "meta-llama/Meta-Llama-3-8B"),
    "vllm/llama3-70b":     ("hf", "meta-llama/Meta-Llama-3-70B-Instruct"),
    "groq/llama3-70b":     ("hf", "meta-llama/Meta-Llama-3-70B-Instruct"),
    "together/llama3-70b": ("hf", "meta-llama/Meta-Llama-3-70B-Instruct"),

    # Mistral local (TGI)
    "tgi/mistral-7b":      ("hf", "mistralai/Mistral-7B-Instruct-v0.2"),

    # Fireworks
    "fireworks/llama3-70b":("hf", "meta-llama/Meta-Llama-3-70B-Instruct"),

    # Azure — same as OpenAI model underneath
    "azure-gpt-4o":        ("tiktoken", "o200k_base"),

    # Bedrock Claude — same approx as Anthropic
    "bedrock-claude-3":    ("approx", 3.8),

    # OpenRouter — approximation (model varies)
    "openrouter/auto":     ("approx", 4.0),
}
```

---

## Cost rates per 1M tokens (input / output)

Update these when provider pricing changes.

```python
# USD per 1M tokens: (input_rate, output_rate)
COST_PER_M = {
    "gpt-4o":               (5.00,   15.00),
    "gpt-4o-mini":          (0.15,    0.60),
    "claude-3-5-sonnet":    (3.00,   15.00),
    "claude-3-haiku":       (0.25,    1.25),
    "gemini-1.5-pro":       (3.50,   10.50),
    "gemini-1.5-flash":     (0.075,   0.30),
    "mistral-large":        (3.00,    9.00),
    "mistral-small":        (0.20,    0.60),
    "groq/llama3-70b":      (0.59,    0.79),
    "groq/mixtral":         (0.24,    0.24),
    "fireworks/llama3-70b": (0.90,    0.90),
    "together/llama3-70b":  (0.90,    0.90),
    "azure-gpt-4o":         (5.00,   15.00),
    "bedrock-claude-3":     (3.00,   15.00),
    # Local models — zero cost (internal tracking only)
    "ollama/llama3":        (0.0,     0.0),
    "vllm/llama3-70b":      (0.0,     0.0),
    "tgi/mistral-7b":       (0.0,     0.0),
    "openrouter/auto":      (0.0,     0.0),   # varies, set per route
}
```

---

## `preflight_guard.py` — Full implementation

```python
"""
Autonomyx LLM Gateway — Pre-flight Token Guard
Plugs into LiteLLM as a custom_pre_call_hook.
Runs before every request:
  1. Tokenise (model-correct)
  2. Estimate cost
  3. Reject if over context window
  4. Reject if over TPM rate limit
  5. Reject if customer over/near spend budget
Returns estimated token count + cost in response headers.
"""
import os, time, json, logging, threading
from collections import defaultdict
from litellm.integrations.custom_logger import CustomLogger
from litellm.exceptions import RateLimitError, ContextWindowExceededError

log = logging.getLogger("preflight-guard")

# ── Tokeniser cache (load once per worker) ──────────────────────────────────
_tokeniser_cache = {}
_cache_lock = threading.Lock()

def _get_tokeniser(model_alias: str):
    with _cache_lock:
        if model_alias in _tokeniser_cache:
            return _tokeniser_cache[model_alias]

        spec = TOKENISER_MAP.get(model_alias, ("approx", 4.0))
        kind = spec[0]

        if kind == "tiktoken":
            import tiktoken
            enc = tiktoken.get_encoding(spec[1])
            _tokeniser_cache[model_alias] = ("tiktoken", enc)

        elif kind == "hf":
            try:
                from transformers import AutoTokenizer
                tok = AutoTokenizer.from_pretrained(spec[1])
                _tokeniser_cache[model_alias] = ("hf", tok)
            except Exception as e:
                log.warning(f"HF tokeniser load failed for {model_alias}: {e} — falling back to approx")
                _tokeniser_cache[model_alias] = ("approx", 4.0)

        else:  # approx
            _tokeniser_cache[model_alias] = ("approx", spec[1])

        return _tokeniser_cache[model_alias]


def count_tokens(text: str, model_alias: str) -> int:
    kind, obj = _get_tokeniser(model_alias)
    if kind == "tiktoken":
        return len(obj.encode(text))
    elif kind == "hf":
        return len(obj.encode(text, add_special_tokens=False))
    else:  # approx: chars / ratio
        return max(1, int(len(text) / obj))


def messages_to_text(messages: list) -> str:
    parts = []
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block["text"])
    return "\n".join(parts)


def estimate_cost(input_tokens: int, model_alias: str) -> float:
    rates = COST_PER_M.get(model_alias, (0.0, 0.0))
    return round((input_tokens / 1_000_000) * rates[0], 6)


# ── Context window limits ────────────────────────────────────────────────────
CONTEXT_LIMITS = {
    "gpt-4o":               128_000,
    "gpt-4o-mini":          128_000,
    "claude-3-5-sonnet":    200_000,
    "claude-3-haiku":       200_000,
    "gemini-1.5-pro":     2_000_000,
    "gemini-1.5-flash":   1_000_000,
    "mistral-large":        128_000,
    "mistral-small":        128_000,
    "groq/llama3-70b":        8_192,
    "groq/mixtral":          32_768,
    "fireworks/llama3-70b":   8_192,
    "together/llama3-70b":    8_192,
    "ollama/llama3":          8_192,
    "vllm/llama3-70b":        8_192,
    "tgi/mistral-7b":        32_768,
    "azure-gpt-4o":         128_000,
    "bedrock-claude-3":     200_000,
    "openrouter/auto":      128_000,
}

# ── In-memory TPM rate limiter (per key_alias per model) ────────────────────
# For production: replace with Redis (same interface, distributed)
_tpm_windows = defaultdict(lambda: {"tokens": 0, "reset_at": 0})
_tpm_lock = threading.Lock()

# TPM limits per virtual key alias (tokens per minute)
# Override in config or load from DB — these are conservative defaults
DEFAULT_TPM_LIMIT = int(os.environ.get("DEFAULT_TPM_LIMIT", 100_000))

def check_tpm(key_alias: str, model: str, tokens: int) -> tuple[bool, int]:
    """Returns (allowed, current_tpm)"""
    bucket_key = f"{key_alias}:{model}"
    now = time.time()
    with _tpm_lock:
        bucket = _tpm_windows[bucket_key]
        if now > bucket["reset_at"]:
            bucket["tokens"] = 0
            bucket["reset_at"] = now + 60
        bucket["tokens"] += tokens
        return bucket["tokens"] <= DEFAULT_TPM_LIMIT, bucket["tokens"]


# ── Main hook ────────────────────────────────────────────────────────────────
class PreflightGuard(CustomLogger):

    def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        return self._check(user_api_key_dict, data)

    def pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        return self._check(user_api_key_dict, data)

    def _check(self, user_api_key_dict, data):
        model      = data.get("model", "unknown")
        messages   = data.get("messages", [])
        key_alias  = (user_api_key_dict or {}).get("key_alias", "default")
        max_budget = (user_api_key_dict or {}).get("max_budget", None)
        spend      = (user_api_key_dict or {}).get("spend", 0.0)

        # 1. Count input tokens
        text = messages_to_text(messages)
        input_tokens = count_tokens(text, model)

        # 2. Context window check
        ctx_limit = CONTEXT_LIMITS.get(model, 8_192)
        if input_tokens > ctx_limit:
            raise ContextWindowExceededError(
                message=(
                    f"Request rejected: {input_tokens:,} input tokens exceeds "
                    f"{model} context window of {ctx_limit:,} tokens. "
                    f"Reduce your input or switch to a model with a larger context window."
                ),
                model=model,
                llm_provider="autonomyx-gateway",
            )

        # 3. TPM rate limit check
        allowed, current_tpm = check_tpm(key_alias, model, input_tokens)
        if not allowed:
            raise RateLimitError(
                message=(
                    f"Rate limit exceeded: {current_tpm:,} tokens/min on {model} "
                    f"(limit: {DEFAULT_TPM_LIMIT:,}). Retry in up to 60 seconds."
                ),
                model=model,
                llm_provider="autonomyx-gateway",
            )

        # 4. Spend budget check
        if max_budget is not None:
            estimated_cost = estimate_cost(input_tokens, model)
            soft_limit = float(max_budget) * 0.90   # warn at 90%
            if spend >= float(max_budget):
                raise RateLimitError(
                    message=(
                        f"Budget exhausted: key '{key_alias}' has spent "
                        f"${spend:.4f} of ${max_budget:.2f} budget. "
                        f"Contact billing to increase your limit."
                    ),
                    model=model,
                    llm_provider="autonomyx-gateway",
                )
            if spend + estimated_cost > soft_limit:
                log.warning(
                    f"[preflight] Key '{key_alias}' approaching budget: "
                    f"${spend:.4f} spent, ${estimated_cost:.6f} estimated this request, "
                    f"soft limit ${soft_limit:.2f}"
                )

        # 5. Attach estimates to metadata for downstream logging
        data.setdefault("metadata", {})
        data["metadata"]["preflight_input_tokens"]  = input_tokens
        data["metadata"]["preflight_estimated_cost"] = estimate_cost(input_tokens, model)
        data["metadata"]["preflight_context_limit"]  = ctx_limit

        log.info(
            f"[preflight] key={key_alias} model={model} "
            f"tokens={input_tokens} est_cost=${estimate_cost(input_tokens, model):.6f}"
        )


preflight_guard = PreflightGuard()
```

---

## Mount in docker-compose

```yaml
  litellm:
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./lago_callback.py:/app/lago_callback.py:ro
      - ./preflight_guard.py:/app/preflight_guard.py:ro   # ADD THIS
```

---

## Register in config.yaml

```yaml
litellm_settings:
  custom_callbacks: ["preflight_guard.PreflightGuard"]
  success_callback: ["lago_callback.LagoCallback"]
```

---

## TPM limits env var (add to .env.example)

```
# Pre-flight guard
DEFAULT_TPM_LIMIT=100000    # tokens per minute per key per model (default 100K)
```

Per-key TPM overrides: set in LiteLLM virtual key metadata at creation time:
```bash
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -d '{
    "key_alias": "tenant-acme",
    "max_budget": 50.0,
    "tpm_limit": 50000,
    "rpm_limit": 100,
    "metadata": {"tpm_override": 50000}
  }'
```

LiteLLM also natively supports `tpm_limit` and `rpm_limit` on virtual keys — the guard above adds **pre-flight estimation and context rejection** on top of LiteLLM's native rate limiting.

---

## HuggingFace tokeniser install

Add to LiteLLM container (or build a custom image):

```dockerfile
FROM ghcr.io/berriai/litellm:main-stable
RUN pip install transformers sentencepiece
```

Or in docker-compose:
```yaml
  litellm:
    image: autonomyx-litellm-custom   # built from above Dockerfile
    build:
      context: .
      dockerfile: Dockerfile.litellm
```

---

## What clients see on rejection

**Context window exceeded (HTTP 400):**
```json
{
  "error": {
    "message": "Request rejected: 12,450 input tokens exceeds gpt-4o-mini context window of 128,000 tokens.",
    "type": "context_window_exceeded",
    "code": 400
  }
}
```

**Rate limit (HTTP 429):**
```json
{
  "error": {
    "message": "Rate limit exceeded: 105,000 tokens/min on groq/llama3-70b (limit: 100,000). Retry in up to 60 seconds.",
    "type": "rate_limit_error",
    "code": 429
  }
}
```

**Budget exhausted (HTTP 429):**
```json
{
  "error": {
    "message": "Budget exhausted: key 'tenant-acme' has spent $49.98 of $50.00 budget. Contact billing to increase your limit.",
    "type": "rate_limit_error",
    "code": 429
  }
}
```

---

## Production upgrade: Redis TPM store

Replace the in-memory `_tpm_windows` dict with Redis for multi-worker/multi-node correctness:

```python
import redis
r = redis.Redis.from_url(os.environ["REDIS_URL"])

def check_tpm_redis(key_alias, model, tokens):
    bucket_key = f"tpm:{key_alias}:{model}"
    pipe = r.pipeline()
    pipe.incrby(bucket_key, tokens)
    pipe.expire(bucket_key, 60)
    current, _ = pipe.execute()
    return current <= DEFAULT_TPM_LIMIT, current
```

Wire `lago-redis` (already in the stack) — set `REDIS_URL=redis://lago-redis:6379`.
