# Local Model Catalogue — Autonomyx LLM Gateway

## Design principle

**Tiered deployment. Small by default, large as opt-in.**

- **Tier 1 (default)** — pulled automatically on stack startup. ≤13B params. Runs on 16GB RAM VPS.
- **Tier 2 (opt-in)** — pulled manually. 14B–33B. Needs 32GB+ RAM or GPU.
- **Tier 3 (opt-in, GPU only)** — 34B+. Needs 48GB+ VRAM or multi-GPU. Served via vLLM.

Runtime split:
- **Ollama** — Tier 1 and Tier 2 (small/medium models, easy management, auto quantisation)
- **vLLM** — Tier 2 large and Tier 3 (32B+, OpenAI-compatible API, better throughput)

---

## Best model per task type

### `chat` — General conversation, Q&A, explanations

| Tier | Model | Ollama tag | Size | RAM | Notes |
|---|---|---|---|---|---|
| 1 ✅ | Llama 3.1 8B Instruct | `llama3.1:8b` | 4.7GB | 8GB | Default. Best chat at 8B. Fast RLHF. |
| 2 | Mistral Small 3.1 22B | `mistral-small3.1:22b` | 13GB | 24GB | Noticeably better reasoning |
| 3 | Llama 3.3 70B Instruct | vLLM: `meta-llama/Llama-3.3-70B-Instruct` | 40GB | 48GB VRAM | Near GPT-4o quality |

---

### `code` — Code generation, debugging, review, refactoring

| Tier | Model | Ollama tag | Size | RAM | Notes |
|---|---|---|---|---|---|
| 1 ✅ | Qwen2.5-Coder 7B Instruct | `qwen2.5-coder:7b` | 4.7GB | 8GB | Default. #1 at 7B on HumanEval (88.4%) |
| 2 | Qwen2.5-Coder 14B Instruct | `qwen2.5-coder:14b` | 9GB | 16GB | Meaningful jump on multi-file tasks |
| 3 | Qwen2.5-Coder 32B Instruct | vLLM: `Qwen/Qwen2.5-Coder-32B-Instruct` | 19GB | 40GB VRAM | Best open code model. Beats GPT-4o on HumanEval (92.7%) |

---

### `reason` — Multi-step reasoning, math, logic, analysis

| Tier | Model | Ollama tag | Size | RAM | Notes |
|---|---|---|---|---|---|
| 1 ✅ | Qwen3 8B | `qwen3:8b` | 5.2GB | 8GB | Default. Hybrid thinking mode. Strong MATH benchmark |
| 2 | Qwen3 14B | `qwen3:14b` | 9GB | 16GB | Clear step up on GPQA and competition math |
| 3 | Qwen3 32B | vLLM: `Qwen/Qwen3-32B` | 20GB | 40GB VRAM | Best open reasoning model. MATH score rivals o1-mini |

> **Qwen3 thinking mode**: prefix prompt with `/think` to enable chain-of-thought.
> prefix with `/no_think` to skip for faster responses. Default: auto.

---

### `summarise` — Document summarisation, TL;DR, executive summaries

| Tier | Model | Ollama tag | Size | RAM | Notes |
|---|---|---|---|---|---|
| 1 ✅ | Mistral 7B Instruct v0.3 | `mistral:7b-instruct` | 4.1GB | 8GB | Default. Fast, clean instruction following |
| 2 | Mistral Small 3.1 22B | `mistral-small3.1:22b` | 13GB | 24GB | Much better on long documents, 128k context |
| 3 | Llama 3.3 70B Instruct | vLLM: `meta-llama/Llama-3.3-70B-Instruct` | 40GB | 48GB VRAM | Best abstractive quality |

---

### `extract` — Structured data extraction, NER, parsing

| Tier | Model | Ollama tag | Size | RAM | Notes |
|---|---|---|---|---|---|
| 1 ✅ | Llama 3.1 8B Instruct | `llama3.1:8b` | 4.7GB | 8GB | Default. Shared with chat. Precise JSON output |
| 2 | Qwen2.5 14B Instruct | `qwen2.5:14b` | 9GB | 16GB | Better at nested/complex schema extraction |
| 3 | Qwen2.5 32B Instruct | vLLM: `Qwen/Qwen2.5-32B-Instruct` | 19GB | 40GB VRAM | Highest extraction accuracy on structured docs |

> For extraction tasks, always add `"response_format": {"type": "json_object"}` in the request.

---

### `vision` — Image description, OCR, chart/diagram analysis

| Tier | Model | Ollama tag | Size | RAM | Notes |
|---|---|---|---|---|---|
| 1 ✅ | Llama 3.2 11B Vision Instruct | `llama3.2-vision:11b` | 7.9GB | 16GB | Default. Best open vision under 20GB |
| 2 | Llama 3.2 90B Vision Instruct | vLLM: `meta-llama/Llama-3.2-90B-Vision-Instruct` | 55GB | 80GB VRAM | Near GPT-4o Vision quality |
| 3 | Qwen2-VL 72B Instruct | vLLM: `Qwen/Qwen2-VL-72B-Instruct` | 44GB | 80GB VRAM | Best open vision model overall. Beats GPT-4V on OCRBench |

> Vision Tier 1 requires 16GB RAM minimum — it is the only Tier 1 model above 8GB.
> If VPS has only 16GB total, deploy vision on-demand rather than always-loaded.

---

### `long_context` — Documents > 32k tokens, full codebases, book-length inputs

| Tier | Model | Ollama tag | Size | RAM | Notes |
|---|---|---|---|---|---|
| 1 ✅ | Gemma 3 9B Instruct | `gemma3:9b` | 5.8GB | 10GB | Default. 128k context. Strong recall on LongBench |
| 2 | Gemma 3 27B Instruct | `gemma3:27b` | 17GB | 32GB | Best quality/context trade-off. 128k context |
| 3 | Llama 3.1 70B Instruct | vLLM: `meta-llama/Llama-3.1-70B-Instruct` | 40GB | 48GB VRAM | 128k context, highest quality |

> Gemma 3 uses a sliding window attention mechanism — effective context is 128k but
> retrieval accuracy drops after ~80k tokens on complex queries. For 100k+ docs, chunk first.

---

### `agent` — Tool calling, multi-step workflows, orchestration

| Tier | Model | Ollama tag | Size | RAM | Notes |
|---|---|---|---|---|---|
| 1 ✅ | Qwen3 8B | `qwen3:8b` | 5.2GB | 8GB | Default. Shared with reason. Best tool-calling at 8B |
| 2 | Qwen3 14B | `qwen3:14b` | 9GB | 16GB | Noticeably better multi-tool chaining |
| 3 | Qwen3 32B | vLLM: `Qwen/Qwen3-32B` | 20GB | 40GB VRAM | Best open agent model. Reliable parallel tool calls |

---

## Tier 1 default stack summary

Models pulled automatically on first Ollama startup. Total: ~37GB disk, ~60GB RAM peak (not all loaded simultaneously — Ollama evicts LRU models from memory).

| Model | Ollama tag | Disk | Tasks |
|---|---|---|---|
| Llama 3.1 8B Instruct | `llama3.1:8b` | 4.7GB | chat, extract |
| Qwen2.5-Coder 7B Instruct | `qwen2.5-coder:7b` | 4.7GB | code |
| Qwen3 8B | `qwen3:8b` | 5.2GB | reason, agent |
| Mistral 7B Instruct v0.3 | `mistral:7b-instruct` | 4.1GB | summarise |
| Llama 3.2 11B Vision Instruct | `llama3.2-vision:11b` | 7.9GB | vision |
| Gemma 3 9B Instruct | `gemma3:9b` | 5.8GB | long_context |

**Minimum VPS spec for Tier 1:** 16GB RAM, 60GB free disk, 4 CPU cores.
**Recommended:** 32GB RAM (allows 2 models in memory simultaneously).

---

## docker-compose — Ollama with auto-pull

```yaml
  ollama:
    image: ollama/ollama:latest
    container_name: autonomyx-ollama
    restart: always
    networks:
      - coolify
    volumes:
      - ollama-data:/root/.ollama
      - ./ollama-pull.sh:/ollama-pull.sh:ro
    environment:
      - OLLAMA_MAX_LOADED_MODELS=2        # max models in RAM simultaneously
      - OLLAMA_NUM_PARALLEL=4             # concurrent requests per model
      - OLLAMA_FLASH_ATTENTION=1          # reduces memory by ~30%
    entrypoint: ["/bin/sh", "-c", "ollama serve & sleep 5 && sh /ollama-pull.sh && wait"]
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Add to `volumes:`:
```yaml
  ollama-data:
```

---

## `ollama-pull.sh` — Tier 1 auto-pull on startup

```bash
#!/bin/sh
# Tier 1 models — pulled automatically
# Comment out any you don't want loaded

set -e
echo "=== Pulling Tier 1 models ==="

ollama pull llama3.1:8b
ollama pull qwen2.5-coder:7b
ollama pull qwen3:8b
ollama pull mistral:7b-instruct
ollama pull llama3.2-vision:11b
ollama pull gemma3:9b

echo "=== Tier 1 models ready ==="
echo ""
echo "=== To pull Tier 2 (optional, needs 32GB RAM) ==="
echo "  docker exec autonomyx-ollama ollama pull mistral-small3.1:22b"
echo "  docker exec autonomyx-ollama ollama pull qwen2.5-coder:14b"
echo "  docker exec autonomyx-ollama ollama pull qwen3:14b"
echo "  docker exec autonomyx-ollama ollama pull qwen2.5:14b"
echo "  docker exec autonomyx-ollama ollama pull gemma3:27b"
echo ""
echo "=== Tier 3 models require vLLM — see vllm service ==="
```

---

## vLLM — Tier 3 opt-in service

Add to docker-compose only when Tier 3 model is needed. Requires GPU.

```yaml
  vllm:
    image: vllm/vllm-openai:latest
    container_name: autonomyx-vllm
    restart: unless-stopped
    networks:
      - coolify
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    environment:
      - HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}
    command: >
      --model ${VLLM_MODEL:-Qwen/Qwen2.5-Coder-32B-Instruct}
      --tensor-parallel-size ${VLLM_TP_SIZE:-1}
      --max-model-len ${VLLM_MAX_LEN:-8192}
      --gpu-memory-utilization 0.90
      --enable-chunked-prefill
    volumes:
      - vllm-cache:/root/.cache/huggingface
```

Add to `volumes:`:
```yaml
  vllm-cache:
```

Add to `.env.example`:
```
# vLLM Tier 3 (GPU required)
VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct
VLLM_TP_SIZE=1        # tensor parallel — set to GPU count
VLLM_MAX_LEN=8192
HF_TOKEN=hf_YOUR_TOKEN_HERE
```

---

## Updated `model_registry.json` — task_default flag

Add `"task_default": true` to the Tier 1 model for each task.
The recommender uses this to pre-filter when `require_local=true` and no scoring context available.

Tier 1 defaults to add/update in `model_registry.json`:

```json
{"alias": "ollama/llama3.1:8b",          "task_default_for": ["chat", "extract"], "tier": 1},
{"alias": "ollama/qwen2.5-coder:7b",     "task_default_for": ["code"],            "tier": 1},
{"alias": "ollama/qwen3:8b",             "task_default_for": ["reason", "agent"], "tier": 1},
{"alias": "ollama/mistral:7b-instruct",  "task_default_for": ["summarise"],       "tier": 1},
{"alias": "ollama/llama3.2-vision:11b",  "task_default_for": ["vision"],          "tier": 1},
{"alias": "ollama/gemma3:9b",            "task_default_for": ["long_context"],    "tier": 1}
```

---

## config.yaml additions — Tier 1 model entries

```yaml
  # ── LOCAL: Ollama Tier 1 defaults ──────────────────────────────────────

  - model_name: ollama/llama3.1:8b
    litellm_params:
      model: ollama/llama3.1:8b
      api_base: "http://ollama:11434"

  - model_name: ollama/qwen2.5-coder:7b
    litellm_params:
      model: ollama/qwen2.5-coder:7b
      api_base: "http://ollama:11434"

  - model_name: ollama/qwen3:8b
    litellm_params:
      model: ollama/qwen3:8b
      api_base: "http://ollama:11434"

  - model_name: ollama/mistral:7b-instruct
    litellm_params:
      model: ollama/mistral:7b-instruct
      api_base: "http://ollama:11434"

  - model_name: ollama/llama3.2-vision:11b
    litellm_params:
      model: ollama/llama3.2-vision:11b
      api_base: "http://ollama:11434"

  - model_name: ollama/gemma3:9b
    litellm_params:
      model: ollama/gemma3:9b
      api_base: "http://ollama:11434"

  # ── LOCAL: Ollama Tier 2 (opt-in, uncomment when ready) ────────────────
  # - model_name: ollama/mistral-small3.1:22b
  #   litellm_params:
  #     model: ollama/mistral-small3.1:22b
  #     api_base: "http://ollama:11434"
  #
  # - model_name: ollama/qwen2.5-coder:14b
  #   litellm_params:
  #     model: ollama/qwen2.5-coder:14b
  #     api_base: "http://ollama:11434"
  #
  # - model_name: ollama/qwen3:14b
  #   litellm_params:
  #     model: ollama/qwen3:14b
  #     api_base: "http://ollama:11434"
  #
  # - model_name: ollama/gemma3:27b
  #   litellm_params:
  #     model: ollama/gemma3:27b
  #     api_base: "http://ollama:11434"

  # ── LOCAL: vLLM Tier 3 (opt-in, GPU required) ──────────────────────────
  # - model_name: vllm/qwen2.5-coder:32b
  #   litellm_params:
  #     model: openai/Qwen/Qwen2.5-Coder-32B-Instruct
  #     api_base: "http://vllm:8000/v1"
  #     api_key: "EMPTY"
  #
  # - model_name: vllm/qwen3:32b
  #   litellm_params:
  #     model: openai/Qwen/Qwen3-32B
  #     api_base: "http://vllm:8000/v1"
  #     api_key: "EMPTY"
```

---

## Fallback chain — updated with local tiers

```yaml
router_settings:
  fallbacks:
    # code: local small → local large → cloud fast → cloud flagship
    - ollama/qwen2.5-coder:7b:
        - ollama/qwen2.5-coder:14b    # Tier 2 if available
        - groq/llama3-70b             # cloud fast
        - gpt-4o                      # cloud flagship

    # reason/agent: local → cloud
    - ollama/qwen3:8b:
        - ollama/qwen3:14b
        - claude-3-5-sonnet

    # chat: local → cloud cheap
    - ollama/llama3.1:8b:
        - groq/llama3-70b
        - gpt-4o-mini

    # vision: local → cloud
    - ollama/llama3.2-vision:11b:
        - gemini-1.5-flash            # cheapest cloud vision
        - gpt-4o

    # long_context: local → gemini (2M context)
    - ollama/gemma3:9b:
        - gemini-1.5-pro              # 2M context window
        - claude-3-5-sonnet           # 200k context
```

---

## Benchmarks — justification for model choices

Sources: HuggingFace Open LLM Leaderboard, LiveCodeBench, MATH-500, LongBench (Jan 2026).

| Task | Model | Key benchmark | Score |
|---|---|---|---|
| code/T1 | Qwen2.5-Coder 7B | HumanEval+ | 88.4% |
| code/T3 | Qwen2.5-Coder 32B | HumanEval+ | 92.7% |
| reason/T1 | Qwen3 8B | MATH-500 | 87.3% |
| reason/T3 | Qwen3 32B | MATH-500 | 94.1% |
| vision/T1 | Llama 3.2 11B Vision | MMBench | 72.6% |
| vision/T3 | Qwen2-VL 72B | OCRBench | 87.7% |
| long_ctx/T1 | Gemma 3 9B | LongBench avg | 71.2% |
| chat/T1 | Llama 3.1 8B | MT-Bench | 8.2/10 |

All Tier 1 models are within 5–8% of their Tier 3 counterparts on their primary task.
The gap is largest for `code` (Qwen2.5-Coder 7B vs 32B: ~4%) and `reason` (Qwen3 8B vs 32B: ~7%).

---

## 96GB RAM — Option C deployment (code + reasoning dominant)

### Memory allocation

| Component | RAM reserved |
|---|---|
| OS + system | 4GB |
| Infrastructure (LiteLLM, Postgres, Prometheus, Grafana, Lago, Keycloak, Mailserver, Classifier, Langflow) | 22GB |
| **Qwen2.5-Coder 32B Q4_K_M** (always-on, code) | 22GB |
| **Qwen3 32B Q4_K_M** (always-on, reason + agent) | 22GB |
| **3rd warm slot** — LRU-evicted 8B model (chat/summarise/extract/vision/long_context) | 6GB |
| **Headroom / future services** | 20GB |
| **Total** | 96GB |

### Always-on models (never evicted)

These two are pinned in RAM. Ollama keeps them loaded regardless of idle time.

```bash
# Pull always-on 32B models (Q4_K_M quantisation — best quality/RAM trade-off)
docker exec autonomyx-ollama ollama pull qwen2.5-coder:32b
docker exec autonomyx-ollama ollama pull qwen3:32b
```

### On-demand 8B models (warm slot, LRU-evicted after idle)

One 8B model stays warm at a time. The least-recently-used is evicted when a new task type arrives. Cold-start: ~3–5s.

```bash
# These are pulled by ollama-pull.sh automatically (Tier 1)
# llama3.1:8b     → chat, extract
# mistral:7b      → summarise
# llama3.2-vision:11b → vision (11B, needs 9GB — evicts the current 8B slot)
# gemma3:9b       → long_context
```

### Ollama configuration for Option C

```yaml
  ollama:
    environment:
      - OLLAMA_MAX_LOADED_MODELS=3        # 2 pinned 32B + 1 warm 8B slot
      - OLLAMA_NUM_PARALLEL=4             # concurrent requests per model
      - OLLAMA_FLASH_ATTENTION=1          # ~30% RAM reduction on attention layers
      - OLLAMA_KEEP_ALIVE=24h             # keep 32B models alive 24h (effectively pinned)
```

Set `OLLAMA_KEEP_ALIVE=24h` on the 32B models at pull time:

```bash
# Pin 32B models — they won't be evicted for 24h after last request
docker exec autonomyx-ollama ollama run qwen2.5-coder:32b --keepalive 24h &
docker exec autonomyx-ollama ollama run qwen3:32b --keepalive 24h &
```

Or set globally and accept that all models stay warm for 24h (fine on 96GB with MAX_LOADED_MODELS=3):

```
OLLAMA_KEEP_ALIVE=24h
```

### Updated `ollama-pull.sh` for Option C

```bash
#!/bin/sh
# Option C: code + reasoning dominant, 96GB RAM VPS
# 32B always-on, 8B on-demand

set -e
echo "=== Pulling Tier 1 on-demand models (8B) ==="
ollama pull llama3.1:8b
ollama pull mistral:7b-instruct
ollama pull llama3.2-vision:11b
ollama pull gemma3:9b

echo "=== Pulling always-on 32B models ==="
echo "    This will take 10-20 minutes on first run (~40GB download)"
ollama pull qwen2.5-coder:32b
ollama pull qwen3:32b

echo "=== Warming 32B models (load into RAM now) ==="
ollama run qwen2.5-coder:32b "Ready." &
ollama run qwen3:32b "Ready." &
wait

echo "=== Option C stack ready ==="
echo ""
echo "RAM usage (approx):"
echo "  Infrastructure:       22GB"
echo "  qwen2.5-coder:32b:    22GB (always-on)"
echo "  qwen3:32b:            22GB (always-on)"
echo "  Warm 8B slot:          6GB (LRU)"
echo "  Headroom:             24GB"
echo ""
echo "Monitor: docker exec autonomyx-ollama ollama ps"
```

### Updated `config.yaml` model entries for Option C

```yaml
  # ── ALWAYS-ON: 32B task specialists ────────────────────────────────────
  - model_name: ollama/qwen2.5-coder:32b
    litellm_params:
      model: ollama/qwen2.5-coder:32b
      api_base: "http://ollama:11434"

  - model_name: ollama/qwen3:32b
    litellm_params:
      model: ollama/qwen3:32b
      api_base: "http://ollama:11434"

  # ── ON-DEMAND: 8B generalists (warm slot, LRU-evicted) ─────────────────
  - model_name: ollama/llama3.1:8b
    litellm_params:
      model: ollama/llama3.1:8b
      api_base: "http://ollama:11434"

  - model_name: ollama/mistral:7b-instruct
    litellm_params:
      model: ollama/mistral:7b-instruct
      api_base: "http://ollama:11434"

  - model_name: ollama/llama3.2-vision:11b
    litellm_params:
      model: ollama/llama3.2-vision:11b
      api_base: "http://ollama:11434"

  - model_name: ollama/gemma3:9b
    litellm_params:
      model: ollama/gemma3:9b
      api_base: "http://ollama:11434"
```

### Updated `model_registry.json` entries for Option C

```json
{"alias": "ollama/qwen2.5-coder:32b", "task_default_for": ["code"],            "tier": 1, "always_on": true,  "private": true, "quality_score": 5, "cost_per_1k_input": 0.0, "cost_per_1k_output": 0.0, "context_window": 32768, "capabilities": ["code", "reason", "extract"], "latency_tier": "medium"},
{"alias": "ollama/qwen3:32b",         "task_default_for": ["reason", "agent"], "tier": 1, "always_on": true,  "private": true, "quality_score": 5, "cost_per_1k_input": 0.0, "cost_per_1k_output": 0.0, "context_window": 32768, "capabilities": ["reason", "agent", "chat", "code", "summarise", "extract"], "latency_tier": "medium"},
{"alias": "ollama/llama3.1:8b",       "task_default_for": ["chat", "extract"], "tier": 1, "always_on": false, "private": true, "quality_score": 3, "cost_per_1k_input": 0.0, "cost_per_1k_output": 0.0, "context_window": 8192,  "capabilities": ["chat", "extract", "summarise"], "latency_tier": "fast"},
{"alias": "ollama/mistral:7b-instruct","task_default_for": ["summarise"],      "tier": 1, "always_on": false, "private": true, "quality_score": 3, "cost_per_1k_input": 0.0, "cost_per_1k_output": 0.0, "context_window": 32768, "capabilities": ["chat", "summarise", "extract"], "latency_tier": "fast"},
{"alias": "ollama/llama3.2-vision:11b","task_default_for": ["vision"],         "tier": 1, "always_on": false, "private": true, "quality_score": 4, "cost_per_1k_input": 0.0, "cost_per_1k_output": 0.0, "context_window": 128000,"capabilities": ["vision", "extract", "summarise"], "latency_tier": "medium"},
{"alias": "ollama/gemma3:9b",         "task_default_for": ["long_context"],    "tier": 1, "always_on": false, "private": true, "quality_score": 4, "cost_per_1k_input": 0.0, "cost_per_1k_output": 0.0, "context_window": 128000,"capabilities": ["long_context", "summarise", "chat"], "latency_tier": "medium"}
```

### Updated fallback chain for Option C

```yaml
router_settings:
  fallbacks:
    # code: 32B always-on → cloud fast → cloud flagship
    - ollama/qwen2.5-coder:32b:
        - groq/llama3-70b
        - gpt-4o

    # reason + agent: 32B always-on → cloud
    - ollama/qwen3:32b:
        - claude-3-5-sonnet
        - gpt-4o

    # chat: 8B on-demand → 32B (overkill but available) → cloud cheap
    - ollama/llama3.1:8b:
        - ollama/qwen3:32b
        - groq/llama3-70b

    # summarise: 8B on-demand → 32B → cloud
    - ollama/mistral:7b-instruct:
        - ollama/qwen3:32b
        - groq/mixtral

    # vision: 11B on-demand → cloud (no larger local vision without GPU)
    - ollama/llama3.2-vision:11b:
        - gemini-1.5-flash
        - gpt-4o

    # long_context: 9B on-demand → gemini (2M context window)
    - ollama/gemma3:9b:
        - gemini-1.5-pro
        - claude-3-5-sonnet
```

### CPU throughput expectations (96GB, no GPU)

| Model | Quantisation | Tokens/sec (est.) | Suitable for |
|---|---|---|---|
| Qwen2.5-Coder 32B Q4_K_M | 4-bit | 8–12 tok/s | Batch code tasks, non-real-time |
| Qwen3 32B Q4_K_M | 4-bit | 8–12 tok/s | Reasoning chains, agent steps |
| Llama 3.1 8B Q4_K_M | 4-bit | 40–60 tok/s | Real-time chat, extractions |
| Mistral 7B Q4_K_M | 4-bit | 40–60 tok/s | Summarisation |
| Llama 3.2 11B Vision Q4_K_M | 4-bit | 25–35 tok/s | Vision (image processing adds latency) |
| Gemma 3 9B Q4_K_M | 4-bit | 35–50 tok/s | Long context |

> 8–12 tok/s on 32B is workable for non-interactive tasks (batch analysis, agent pipelines,
> background processing). For real-time chat at 32B quality, route to cloud.
> Qwen3 8B at 40–60 tok/s is the best local real-time option.

### CPU optimisation flags for Ollama

```yaml
  ollama:
    environment:
      - OLLAMA_FLASH_ATTENTION=1       # reduces RAM by ~30% on attention
      - OLLAMA_NUM_PARALLEL=4          # 4 concurrent requests — good for 96GB
      - GOMLX_FORCE_CPU_THREADS=16     # use 16 CPU threads for inference
      - OLLAMA_MAX_LOADED_MODELS=3
      - OLLAMA_KEEP_ALIVE=24h
```

Also set on the host before starting Docker:
```bash
# Maximise memory bandwidth for llama.cpp (used by Ollama internally)
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

### Upgrade path — when to add GPU

Switch from CPU to GPU when:
- 32B throughput < 5 tok/s under concurrent load (measure with Prometheus)
- Concurrent users > 10 hitting 32B models simultaneously
- Agent pipelines require < 2s latency per step

At that point, a single A100 80GB or H100 80GB replaces all of the above with 60–120 tok/s.
The docker-compose vLLM service is already scaffolded — uncomment and point at GPU.

### Monitor RAM headroom

```bash
# Watch live
watch -n5 'free -h && docker exec autonomyx-ollama ollama ps'

# Alert if headroom < 10GB
docker exec autonomyx-prometheus   promtool query instant http://localhost:9090   'node_memory_MemAvailable_bytes / 1024 / 1024 / 1024'
```

---

## Best-experience stack — 96GB CPU-only (final recommendation)

### Selected stack: Qwen3-30B-A3B + Qwen2.5-Coder-32B

**Decision rationale:**
- Qwen3-30B-A3B (MoE, 3B active) → reason + agent: 15–25 tok/s. Faster than dense 32B at
  comparable quality. MoE architecture activates only 3B parameters per token — CPU inference
  behaves like a 3B model in speed while drawing on 30B parameter knowledge.
- Qwen2.5-Coder-32B (dense) → code: best open code model period. No compromise here.
- Combined RAM: ~41GB always-on. Leaves 55GB for infrastructure + 3 warm 8B slots.
- Quality gap vs dense Qwen3-32B on MATH-500: ~3%. Speed advantage: ~50%. MoE wins on
  experience for interactive and agent workloads.

### Memory map — 96GB

| Slot | Component | Quant | RAM | Always-on | Notes |
|---|---|---|---|---|---|
| — | OS + system | — | ~4GB | Always | — |
| — | Infrastructure | — | ~22GB | Always | LiteLLM, Postgres, Prometheus, Grafana, Lago, Keycloak, Mailserver, Classifier, Langflow |
| — | Translation sidecar | — | ~4GB | Always | IndicTrans2 ×2 + fastText LID + Opus-MT lazy |
| 1 | Qwen3-30B-A3B | Q4_K_M | ~19GB | Yes | reason, agent, chat |
| 2 | Qwen2.5-Coder-32B | Q4_K_M | ~22GB | Yes | code |
| 3 | Warm slot A (8B) | Q4_K_M | ~6GB | LRU | chat, extract, summarise |
| 4 | Warm slot B (11B) | Q4_K_M | ~9GB | LRU | vision, long_context |

**Three operating states:**

| State | What's loaded | RAM used | Headroom |
|---|---|---|---|
| Active (no warm slots) | Infra + translation + 2×32B | ~67GB | **~29GB** |
| Typical (one warm slot) | + 8B model | ~77GB | **~19GB** |
| Peak (both warm slots) | + 8B + 11B vision | **~82GB** | **~14GB** |

14GB headroom at peak is safe for normal operation. Risk events that cause spikes:
- Ollama model load (1.5× model size briefly during load)
- 128k context requests (KV cache: 4–6GB spike)
- Long document translation (IndicTrans2 chunked processing)

**Hard cap via docker mem_limit prevents OOM killing other services.**

---

### Ollama configuration

```yaml
  ollama:
    image: ollama/ollama:latest
    container_name: autonomyx-ollama
    restart: always
    networks:
      - coolify
    volumes:
      - ollama-data:/root/.ollama
      - ./ollama-pull.sh:/ollama-pull.sh:ro
    environment:
      - OLLAMA_MAX_LOADED_MODELS=4        # 2 always-on + 2 warm slots
      - OLLAMA_NUM_PARALLEL=4             # concurrent requests
      - OLLAMA_FLASH_ATTENTION=1          # ~30% RAM reduction on attention
      - OLLAMA_KEEP_ALIVE=24h             # always-on models stay loaded
      - GOMLX_FORCE_CPU_THREADS=16        # use 16 CPU threads
    entrypoint: ["/bin/sh", "-c", "ollama serve & sleep 8 && sh /ollama-pull.sh && wait"]
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

---

### `ollama-pull.sh` — final version

```bash
#!/bin/sh
# Autonomyx LLM Gateway — 96GB CPU-only VPS
# Always-on: Qwen3-30B-A3B (reason/agent) + Qwen2.5-Coder-32B (code)
# On-demand: 8B/11B models for other tasks

set -e

echo "============================================"
echo " Autonomyx LLM Gateway — Model Pull Script"
echo " VPS: 96GB RAM, CPU-only"
echo "============================================"
echo ""

# ── Always-on: reason + agent ──────────────────
echo "[1/6] Pulling Qwen3-30B-A3B (reason + agent) ~19GB..."
ollama pull qwen3:30b-a3b
echo "      Done."

# ── Always-on: code ───────────────────────────
echo "[2/6] Pulling Qwen2.5-Coder-32B (code) ~22GB..."
ollama pull qwen2.5-coder:32b
echo "      Done."

# ── On-demand: chat + extract ─────────────────
echo "[3/6] Pulling Llama 3.1 8B (chat + extract) ~4.7GB..."
ollama pull llama3.1:8b
echo "      Done."

# ── On-demand: summarise ──────────────────────
echo "[4/6] Pulling Mistral 7B (summarise) ~4.1GB..."
ollama pull mistral:7b-instruct
echo "      Done."

# ── On-demand: vision ─────────────────────────
echo "[5/6] Pulling Llama 3.2 11B Vision (vision) ~7.9GB..."
ollama pull llama3.2-vision:11b
echo "      Done."

# ── On-demand: long context ───────────────────
echo "[6/6] Pulling Gemma 3 9B (long_context) ~5.8GB..."
ollama pull gemma3:9b
echo "      Done."

echo ""
echo "============================================"
echo " Warming always-on models into RAM..."
echo "============================================"

# Load into RAM immediately — don't wait for first request
ollama run qwen3:30b-a3b "Respond with: Ready." --keepalive 24h &
PID1=$!
ollama run qwen2.5-coder:32b "Respond with: Ready." --keepalive 24h &
PID2=$!
wait $PID1 $PID2

echo ""
echo "============================================"
echo " Model stack ready. Memory summary:"
echo "   Qwen3-30B-A3B:      ~19GB (always-on)"
echo "   Qwen2.5-Coder-32B:  ~22GB (always-on)"
echo "   Warm slot A (8B):   ~6GB  (LRU)"
echo "   Warm slot B (11B):  ~9GB  (LRU)"
echo "   Infrastructure:     ~22GB"
echo "   Headroom:           ~18GB"
echo "   Total peak:         ~78GB / 96GB"
echo ""
echo " Monitor: docker exec autonomyx-ollama ollama ps"
echo ""
echo " Qwen3 thinking mode:"
echo "   /think    → enable chain-of-thought (complex tasks)"
echo "   /no_think → skip thinking (fast responses)"
echo "============================================"
```

---

### config.yaml model entries — final

```yaml
model_list:

  # ═══════════════════════════════════════════
  # ALWAYS-ON: Primary specialists (96GB VPS)
  # ═══════════════════════════════════════════

  # Reason + Agent: Qwen3-30B-A3B (MoE, 3B active)
  # 15–25 tok/s CPU | 128k context | thinking mode
  - model_name: ollama/qwen3:30b-a3b
    litellm_params:
      model: ollama/qwen3:30b-a3b
      api_base: "http://ollama:11434"

  # Code: Qwen2.5-Coder-32B — best open code model
  # 10–15 tok/s CPU | 128k context | HumanEval+ 92.7%
  - model_name: ollama/qwen2.5-coder:32b
    litellm_params:
      model: ollama/qwen2.5-coder:32b
      api_base: "http://ollama:11434"

  # ═══════════════════════════════════════════
  # ON-DEMAND: Task specialists (warm slot, LRU)
  # ═══════════════════════════════════════════

  # Chat + Extract: fast, real-time capable
  - model_name: ollama/llama3.1:8b
    litellm_params:
      model: ollama/llama3.1:8b
      api_base: "http://ollama:11434"

  # Summarise: clean instruction following, 32k context
  - model_name: ollama/mistral:7b-instruct
    litellm_params:
      model: ollama/mistral:7b-instruct
      api_base: "http://ollama:11434"

  # Vision: best open vision under 20GB
  - model_name: ollama/llama3.2-vision:11b
    litellm_params:
      model: ollama/llama3.2-vision:11b
      api_base: "http://ollama:11434"

  # Long context: 128k context, strong recall
  - model_name: ollama/gemma3:9b
    litellm_params:
      model: ollama/gemma3:9b
      api_base: "http://ollama:11434"
```

---

### model_registry.json — final local entries

```json
[
  {
    "alias": "ollama/qwen3:30b-a3b",
    "provider": "local",
    "task_default_for": ["reason", "agent", "chat"],
    "always_on": true,
    "tier": 1,
    "private": true,
    "quality_score": 5,
    "cost_per_1k_input": 0.0,
    "cost_per_1k_output": 0.0,
    "context_window": 131072,
    "capabilities": ["reason", "agent", "chat", "code", "summarise", "extract"],
    "latency_tier": "fast",
    "params_total": "30B",
    "params_active": "3B",
    "architecture": "MoE",
    "quantisation": "Q4_K_M",
    "ram_gb": 19,
    "cpu_tokens_per_sec": "15-25",
    "notes": "Qwen3 MoE. Use /think for complex reasoning, /no_think for fast responses."
  },
  {
    "alias": "ollama/qwen2.5-coder:32b",
    "provider": "local",
    "task_default_for": ["code"],
    "always_on": true,
    "tier": 1,
    "private": true,
    "quality_score": 5,
    "cost_per_1k_input": 0.0,
    "cost_per_1k_output": 0.0,
    "context_window": 131072,
    "capabilities": ["code", "reason", "extract"],
    "latency_tier": "medium",
    "params_total": "32B",
    "params_active": "32B",
    "architecture": "dense",
    "quantisation": "Q4_K_M",
    "ram_gb": 22,
    "cpu_tokens_per_sec": "10-15",
    "notes": "Best open code model. HumanEval+ 92.7%. Supports 80+ languages."
  },
  {
    "alias": "ollama/llama3.1:8b",
    "provider": "local",
    "task_default_for": ["chat", "extract"],
    "always_on": false,
    "tier": 1,
    "private": true,
    "quality_score": 3,
    "cost_per_1k_input": 0.0,
    "cost_per_1k_output": 0.0,
    "context_window": 8192,
    "capabilities": ["chat", "extract", "summarise"],
    "latency_tier": "fast",
    "params_total": "8B",
    "params_active": "8B",
    "architecture": "dense",
    "quantisation": "Q4_K_M",
    "ram_gb": 6,
    "cpu_tokens_per_sec": "40-60",
    "notes": "Fast real-time chat. Best for interactive responses where latency matters."
  },
  {
    "alias": "ollama/mistral:7b-instruct",
    "provider": "local",
    "task_default_for": ["summarise"],
    "always_on": false,
    "tier": 1,
    "private": true,
    "quality_score": 3,
    "cost_per_1k_input": 0.0,
    "cost_per_1k_output": 0.0,
    "context_window": 32768,
    "capabilities": ["summarise", "chat", "extract"],
    "latency_tier": "fast",
    "params_total": "7B",
    "params_active": "7B",
    "architecture": "dense",
    "quantisation": "Q4_K_M",
    "ram_gb": 5,
    "cpu_tokens_per_sec": "40-60",
    "notes": "Clean instruction following. 32k context good for medium-length documents."
  },
  {
    "alias": "ollama/llama3.2-vision:11b",
    "provider": "local",
    "task_default_for": ["vision"],
    "always_on": false,
    "tier": 1,
    "private": true,
    "quality_score": 4,
    "cost_per_1k_input": 0.0,
    "cost_per_1k_output": 0.0,
    "context_window": 131072,
    "capabilities": ["vision", "extract", "summarise"],
    "latency_tier": "medium",
    "params_total": "11B",
    "params_active": "11B",
    "architecture": "dense",
    "quantisation": "Q4_K_M",
    "ram_gb": 9,
    "cpu_tokens_per_sec": "25-35",
    "notes": "Best open vision model under 20GB. Image processing adds 1-3s to first token."
  },
  {
    "alias": "ollama/gemma3:9b",
    "provider": "local",
    "task_default_for": ["long_context"],
    "always_on": false,
    "tier": 1,
    "private": true,
    "quality_score": 4,
    "cost_per_1k_input": 0.0,
    "cost_per_1k_output": 0.0,
    "context_window": 131072,
    "capabilities": ["long_context", "summarise", "chat"],
    "latency_tier": "medium",
    "params_total": "9B",
    "params_active": "9B",
    "architecture": "dense",
    "quantisation": "Q4_K_M",
    "ram_gb": 6,
    "cpu_tokens_per_sec": "35-50",
    "notes": "128k context. Best recall on long documents among on-demand models."
  }
]
```

---

### Fallback chain — final

```yaml
router_settings:
  routing_strategy: usage-based-routing
  num_retries: 3
  request_timeout: 60
  allowed_fails: 2

  fallbacks:
    # reason + agent: MoE local → cloud reasoning
    - ollama/qwen3:30b-a3b:
        - claude-3-5-sonnet       # best cloud reasoning
        - gpt-4o                  # fallback cloud

    # code: local best → cloud fast → cloud flagship
    - ollama/qwen2.5-coder:32b:
        - groq/llama3-70b         # fast cloud, good code
        - gpt-4o                  # cloud flagship

    # chat: fast local → always-on local (overkill but available) → cloud cheap
    - ollama/llama3.1:8b:
        - ollama/qwen3:30b-a3b    # local upgrade
        - groq/llama3-70b         # cloud fast
        - gpt-4o-mini             # cloud cheap

    # summarise: local → always-on upgrade → cloud
    - ollama/mistral:7b-instruct:
        - ollama/qwen3:30b-a3b
        - groq/mixtral

    # vision: local only option → cloud vision
    - ollama/llama3.2-vision:11b:
        - gemini-1.5-flash        # cheapest cloud vision
        - gpt-4o                  # best cloud vision

    # long_context: local → gemini 2M → claude 200k
    - ollama/gemma3:9b:
        - gemini-1.5-pro          # 2M context window
        - claude-3-5-sonnet       # 200k context
```

---

### Qwen3-30B-A3B thinking mode — usage guide

Qwen3 supports switching between thinking (chain-of-thought) and non-thinking mode per request.

```python
# Thinking mode — complex reasoning, math, multi-step agent tasks
# Adds 2-5s latency but significantly improves accuracy
messages = [
    {"role": "user", "content": "/think Solve this step by step: ..."}
]

# Non-thinking mode — fast responses, chat, simple extraction
# Same speed as a standard 8B model at 3B active params
messages = [
    {"role": "user", "content": "/no_think Summarise this in 3 bullets: ..."}
]

# In LiteLLM config — set default per alias
# Add two aliases for same model, different modes:
```

```yaml
  # Qwen3-30B-A3B thinking mode (complex tasks)
  - model_name: ollama/qwen3:30b-a3b-think
    litellm_params:
      model: ollama/qwen3:30b-a3b
      api_base: "http://ollama:11434"
      system_prompt: "You are a careful reasoning assistant. Always think step by step."

  # Qwen3-30B-A3B non-thinking mode (fast tasks)
  - model_name: ollama/qwen3:30b-a3b-fast
    litellm_params:
      model: ollama/qwen3:30b-a3b
      api_base: "http://ollama:11434"
      system_prompt: "/no_think"
```

---

### CPU optimisation — final flags

```bash
# Set on host before starting Docker stack
# Performance governor (maximises CPU clock)
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Transparent Hugepages — helps llama.cpp memory bandwidth
echo always | sudo tee /sys/kernel/mm/transparent_hugepage/enabled

# NUMA — if VPS has multi-socket (check: numactl --hardware)
# If NUMA nodes > 1, bind Ollama to node 0:
numactl --membind=0 --cpunodebind=0 docker compose up ollama
```

```yaml
# In docker-compose, pin Ollama to physical CPUs
  ollama:
    cpuset: "0-15"              # use first 16 cores — adjust to your VPS CPU count
    mem_limit: 60g              # hard cap: 2 always-on (41GB) + headroom
    memswap_limit: 60g          # no swap — swap kills inference speed
```

---

### When to buy more RAM

Add RAM when Prometheus shows:

```bash
# Available memory < 10GB for >30 min
node_memory_MemAvailable_bytes / 1024^3 < 10

# Or Ollama starts evicting always-on models (check logs)
docker logs autonomyx-ollama 2>&1 | grep -i "unload"
```

**Monitor — add RAM when:**
```bash
# Available memory consistently below 8GB (danger zone)
watch -n10 'free -h | grep Mem'

# Ollama evicting always-on 32B models unexpectedly (means RAM is too tight)
docker logs autonomyx-ollama 2>&1 | grep -i "unloading"
```

**Next RAM tier: 128GB**
Adds ~50GB usable headroom. Run Qwen3-235B-A22B Q2_K (~65GB) as reasoning model
alongside Qwen2.5-Coder-32B (~22GB). Genuine frontier-class reasoning at zero API cost.

**At 192GB:**
Run Qwen3-235B Q4_K_M (~112GB) + Qwen2.5-Coder-32B (~22GB) simultaneously.
That is the best open-source stack available at any price.
