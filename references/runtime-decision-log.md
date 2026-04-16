# Inference Runtime Decision Log — Ollama vs Docker Model Runner

## Decision

**Chosen: Ollama**
**Date: April 2025**
**Revisit trigger: See "When to migrate" section below**

---

## Context

Two viable runtimes evaluated for the Autonomyx LLM Gateway inference layer:
- **Ollama** — standalone LLM runtime, llama.cpp under the hood, 50k+ GitHub stars
- **Docker Model Runner (DMR)** — Docker's native LLM runtime, launched April 2025,
  also llama.cpp under the hood, OCI model packaging

Both expose an OpenAI-compatible API. Both integrate with LiteLLM natively.
Both use the same underlying inference engine — raw token throughput is a tie.

---

## Why Ollama was chosen

### 1. Linux CPU-only VPS — Ollama is the mature choice

DMR launched optimised for Apple Silicon (Metal API GPU acceleration).
Linux CPU support exists but is less tested in the community.
Our VPS is Linux, CPU-only. Ollama has years of production Linux CPU deployments.
Every Qwen3, Qwen2.5-Coder, Llama3.2, Gemma3 model we run has documented
Ollama + Linux CPU configurations with known RAM and throughput figures.

### 2. KEEP_ALIVE — critical for always-on 32B models

We pin Qwen3-30B-A3B and Qwen2.5-Coder-32B in RAM permanently:
```
OLLAMA_KEEP_ALIVE=24h
```
Docker Model Runner uses lazy loading by default — models unload when idle.
No equivalent always-on pinning mechanism exists in DMR today.
On a 32B model, cold-start from disk takes 30–60 seconds. Unacceptable for production.

### 3. Model library maturity

Ollama's community has tested our exact model stack:
- `qwen3:30b-a3b` — documented, community-benchmarked on Linux CPU
- `qwen2.5-coder:32b` — documented, known RAM figures
- `qwen2.5:14b` — documented
- `llama3.2-vision:11b` — documented
- `gemma3:9b` — documented

DMR's Docker Hub model library is growing but has fewer community-verified
configurations for large models on Linux CPU.

### 4. LiteLLM integration

LiteLLM has native Ollama provider support with specific handling for Ollama's
streaming, model management, and error formats. DMR's OpenAI-compatible API
also works with LiteLLM but as a generic OpenAI provider — less tested.

---

## Where Docker Model Runner is genuinely better

### 1. OCI model packaging — the killer feature for our roadmap

This is the most important advantage DMR has and Ollama does not:

```bash
# DMR — push fine-tuned model to private registry
docker model push registry.openautonomyx.com/models/qwen3-legal:v1

# Customer pulls to their private deployment node
docker model pull registry.openautonomyx.com/models/qwen3-legal:v1
```

When we produce segment-specific fine-tuned models (qwen3-legal:v1, qwen3-code:v1,
qwen3-bfsi:v1), distributing them to private deployment customers via OCI registry
is clean, versioned, auditable, and familiar to any DevOps team.

With Ollama, distributing fine-tuned models requires:
- Manual Modelfile distribution
- Custom scripting to pull base model + apply adapter
- No native registry support

DMR solves this natively. This is the primary reason to migrate later.

### 2. Docker-native workflow

DMR models are first-class Docker primitives:
```bash
docker model pull ai/qwen2.5:14b
docker model run ai/qwen2.5:14b
docker model ls
docker model rm ai/qwen2.5:14b
```
Fits Coolify's Docker-centric model perfectly. No separate Ollama service.
Models managed alongside containers in the same toolchain.

### 3. Multi-engine roadmap

DMR plans to support vLLM and MLX as additional inference engines.
When we add GPU, switching from llama.cpp to vLLM for throughput will be
a config change rather than a runtime migration.

### 4. Vulkan GPU support (since October 2025)

DMR supports Vulkan — enabling hardware acceleration on AMD, Intel, and
integrated GPUs. Relevant if we add a non-NVIDIA GPU later.

---

## Performance comparison (evidence)

Both use llama.cpp. Raw throughput is a tie.

| Metric | Ollama | Docker Model Runner | Source |
|---|---|---|---|
| Tokens/sec (mean) | 23.65 | ~similar | Spring AI benchmark, 50 runs |
| Standard deviation | 2.55 | 2.13 | — |
| Statistical significance | Not significant | — | Distributions overlap |
| First-token latency (pinned model) | Fast (loaded) | Slower (lazy load) | Architecture difference |
| First-token latency (cold start) | Slow (30-60s for 32B) | Same | Same llama.cpp |

Conclusion: identical throughput, Ollama wins on always-on latency due to KEEP_ALIVE.

---

## When to migrate from Ollama to Docker Model Runner

Migrate when ANY of the following are true:

### Trigger 1 — First fine-tuned model ready for distribution (most likely first)
When qwen3-legal:v1 or qwen3-code:v1 is ready to ship to private deployment customers.
OCI packaging makes this workflow clean. Migrate the private deployment stack to DMR first,
keep shared SaaS on Ollama during transition.

### Trigger 2 — GPU added to infrastructure
DMR's multi-engine support (vLLM) becomes relevant. GPU inference with vLLM via DMR
is a cleaner setup than Ollama + separate vLLM container.

### Trigger 3 — DMR adds KEEP_ALIVE equivalent on Linux
Watch the DMR changelog: https://docs.docker.com/model-runner/
When model pinning is supported on Linux, the last remaining Ollama advantage disappears.

### Trigger 4 — DMR Linux CPU community reaches parity
When Qwen3-30B-A3B, Qwen2.5-Coder-32B have documented DMR + Linux CPU configurations
with verified RAM figures — safe to migrate.

---

## Migration path (when trigger fires)

Migration is low-risk — both expose identical OpenAI-compatible APIs.
LiteLLM config changes are minimal.

```yaml
# Current (Ollama)
- model_name: ollama/qwen3:30b-a3b
  litellm_params:
    model: ollama/qwen3:30b-a3b
    api_base: "http://ollama:11434"

# After migration (Docker Model Runner)
- model_name: ollama/qwen3:30b-a3b   # alias unchanged — clients unaffected
  litellm_params:
    model: openai/qwen3:30b-a3b       # DMR uses openai provider in LiteLLM
    api_base: "http://localhost:12434/engines/llama.cpp/v1"
```

Steps:
1. Deploy DMR alongside Ollama (both can run simultaneously)
2. Route 5% of traffic to DMR, monitor quality and latency
3. Increase to 50%, then 100%
4. Remove Ollama service

Zero downtime. LiteLLM handles the routing. Clients see no change.

---

## Alternatives considered and rejected

### vLLM (standalone)
- Best throughput for GPU workloads — PagedAttention, continuous batching
- CPU mode: experimental, slower than llama.cpp on CPU
- No multi-model management (one model per process)
- Chosen for GPU phase (Phase 2) — not applicable today
- Will revisit when GPU is added

### HuggingFace TGI (Text Generation Inference)
- Strong for specific HuggingFace models
- More complex setup than Ollama
- Less flexible model format support (no GGUF natively)
- Rejected: complexity without advantage for our stack

### llama.cpp direct (no runtime wrapper)
- Maximum control, minimum overhead
- No model management, no API server out of the box
- Requires custom scripting for everything Ollama gives for free
- Rejected: not worth the ops burden at this stage

---

## Summary table

| Criterion | Ollama | Docker Model Runner | Winner |
|---|---|---|---|
| Linux CPU production maturity | ✅ | ⚠️ | Ollama |
| Always-on model pinning | ✅ KEEP_ALIVE | ❌ Lazy load only | Ollama |
| Raw inference throughput | ✅ Tied | ✅ Tied | Tie |
| LiteLLM integration | ✅ Native | ✅ OpenAI-compat | Tie |
| Model library (our models) | ✅ All documented | ⚠️ Growing | Ollama |
| OCI model distribution | ❌ Not supported | ✅ Native | DMR |
| Fine-tuned model shipping | ❌ Manual | ✅ Registry | DMR |
| Docker-native workflow | ⚠️ Separate service | ✅ Native | DMR |
| Multi-engine (vLLM) roadmap | ❌ | ✅ Planned | DMR |
| GPU Vulkan support | ❌ | ✅ | DMR |
| **Decision** | **✅ Use now** | **📅 Migrate later** | — |

---

## Owner

This decision should be reviewed by whoever manages inference infrastructure.
Check the DMR changelog quarterly: https://docs.docker.com/model-runner/changelog/
