# Profitability & Pricing Strategy — Autonomyx LLM Gateway

## Core thesis


> ⚠️ **India Data Residency** — planned future SKU, not currently live.
> Current VPS is not India-hosted. Do not use data residency as a selling point
> until the India-hosted infrastructure is deployed and verified.
> When launched: position as a premium add-on for DPDP enterprise compliance.

**Structural cost advantage is real but temporary.**
Cloud GPU prices are falling ~10x per year. Your moat must be:
1. Price below market NOW (capture customers)
2. Privacy + India data residency (DPDP lock-in — switching cost)
3. Benchmark-backed quality claims (trust)
4. Managed infrastructure (operational value > raw compute)

Lead with: **"Same accuracy. Half the price."**

> **India data residency** is a planned future offering — do NOT use it in current
> customer-facing positioning or sales materials until the India-hosted infrastructure
> is live and verified. It will be a separate SKU at that point.

---

## Phase 1: Current VPS (CPU-only, 96GB RAM)

### Cost structure — fixed, not variable

**The VPS cost is a fixed monthly commitment regardless of usage.**
This fundamentally changes the economics vs. cloud-variable pricing:

- Every token served above zero costs you ₹0 in marginal infra
- Break-even is not about tokens — it's about covering the fixed VPS line
- Marginal cost of serving one more customer = ₹0 (until you hit CPU saturation)
- All revenue above fixed cost is gross profit

| Component | Monthly cost | Variable? |
|---|---|---|
| VPS (96GB RAM, dedicated) | Fixed — your actual contract amount | ❌ No |
| Electricity | Included in VPS | ❌ No |
| Bandwidth | Included or fixed cap | ❌ No |
| Domain + SSL + Coolify | ~₹500 | ❌ No |
| **Marginal cost per token** | **₹0.00** | — |

**Implication:** Your break-even is simply "generate enough revenue to cover the VPS bill."
Every rupee above that is profit. You are not paying per token. OpenAI is.

### Throughput capacity and revenue ceiling

At CPU-only throughput (conservative, single request queue):

| Model | Tok/s avg | Tokens/month (50% util) | At ₹2/1M | At ₹5/1M | At ₹10/1M |
|---|---|---|---|---|---|
| Qwen3-30B-A3B | 18 | ~23B | ₹46,000 | ₹1,15,000 | ₹2,30,000 |
| Qwen2.5-Coder-32B | 12 | ~15B | ₹30,000 | ₹75,000 | ₹1,50,000 |
| 8B warm slot | 45 | ~5B | ₹10,000 | ₹25,000 | ₹50,000 |
| **Total** | | **~43B** | **₹86,000** | **₹2,15,000** | **₹4,30,000** |

**50% utilisation is conservative** — batch workloads (document processing, code review
pipelines, background analysis) can run at night and weekends, lifting effective utilisation
to 70%+ without affecting interactive response times.

**Honest Phase 1 range:**
- Low (light traffic, mostly free tier): ₹5,000–20,000/month
- Mid (10–20 paying customers, mixed usage): ₹50,000–1,50,000/month
- High (CPU saturated, queue building): ₹2,00,000+/month → upgrade trigger

**CPU saturation signal:** average queue depth > 3 concurrent requests for > 2 hours/day.
At that point, add GPU — don't raise prices.

---

## Phase 2: GPU cloud (the real business)

### Cost per million tokens — your infra vs. competitors

Based on market data (H100 at $1.49–3.90/hr, April 2026):

**Your cost to serve (self-managed GPU cloud):**

| Setup | GPU | $/hr | Tok/s (32B Q4) | Cost/1M tokens |
|---|---|---|---|---|
| RunPod/Vast.ai spot | RTX 4090 (24GB) | $0.35–0.55 | ~80 tok/s | ~$0.0012–0.0019 |
| RunPod/Vast.ai reserved | A100 80GB | $0.89–1.20 | ~200 tok/s | ~$0.0012–0.0017 |
| Hyperbolic | H100 80GB | $1.49 | ~400 tok/s | ~$0.0010 |
| Lambda Labs reserved | H100 | $1.85 | ~400 tok/s | ~$0.0013 |
| AWS spot (ap-south-1) | A100 | ~$1.50 | ~200 tok/s | ~$0.0021 |

**Your floor cost: ~$0.001–0.002 per 1M tokens for 32B models on GPU.**

**Competitor pricing (April 2026):**

| Provider | Model equivalent | Price/1M tokens (blended) |
|---|---|---|
| OpenAI | GPT-4o | $7.50 |
| OpenAI | GPT-4o-mini | $0.30 |
| Anthropic | Claude Sonnet 4.5 | $4.50 |
| Anthropic | Claude Haiku 4.5 | $0.40 |
| Groq | Llama 3.3 70B | $0.59 |
| Together AI | Qwen2.5-72B | $1.20 |
| Fireworks | Qwen2.5-Coder-32B | $0.90 |
| DeepInfra | Qwen3-30B | $0.35 |

**Your viable price range: $0.10–0.50/1M tokens** — 60–80% below market,
90%+ gross margin even at the low end.

---

## Pricing architecture — three-tier GTM

### Tier 1: Developer (API access)

Target: Indie developers, startups, small teams
Billing: Pay-per-token via Lago (metered)

```
Free tier:        10M tokens/month free (no credit card)
                  Qwen3-30B-A3B + Qwen2.5-Coder-32B
                  Rate limit: 10 req/min
                  Purpose: acquisition, trust-building

Starter:          ₹999/month
                  100M tokens included
                  All local models
                  Rate limit: 60 req/min
                  Overage: ₹8/1M tokens

Growth:           ₹4,999/month
                  1B tokens included
                  Local + cloud fallback (OpenRouter pass-through)
                  Rate limit: 300 req/min
                  Overage: ₹4/1M tokens
                  SLA: 99.5% uptime
```

**Why free tier works:** Local models cost you ~₹0.08/1M tokens in electricity.
10M free tokens = ₹0.80 cost. Acquisition cost = ₹0.80 per developer. Cheapest CAC possible.

---

### Tier 2: SaaS (embed in their product)

Target: SaaS companies using your gateway as their AI backend
Billing: Hybrid — monthly base + metered overage

```
SaaS Basic:       ₹14,999/month
                  5B tokens included
                  White-label endpoint (their domain)
                  Dedicated Keycloak tenant
                  Lago billing sub-accounts per their customers
                  Rate limit: 1,000 req/min
                  Overage: ₹3/1M tokens
                  SLA: 99.9% uptime

SaaS Pro:         ₹39,999/month
                  20B tokens included
                  Priority queue (always-on model slot reserved)
                  Custom model fine-tuning (on request)
                  DPDP DPA included
                  Overage: ₹2/1M tokens
                  SLA: 99.95% uptime, 4hr support response
```

**Key differentiator for SaaS:** Lago gives them metered billing for their own customers
out of the box. They don't have to build billing. You're not just an LLM provider — you're
an AI infrastructure + billing platform. That's the real value.

---

### Tier 3: Enterprise (private deployment)

Target: Enterprises with data sovereignty requirements, DPDP compliance needs
Billing: Annual contract, custom

```
Enterprise:       ₹5L–25L/year ($6,000–30,000)
                  Dedicated GPU node (provisioned on Hetzner/AWS/Azure)
                  Data never shared between tenants
                  DPDP-compliant DPA + audit trail
                  Keycloak SSO integration with their IdP
                  Custom model selection
                  99.99% SLA
                  Dedicated support
                  Annual security review
```

**DPDP angle:** Enterprise Indian companies need a vendor who signs a Data Processing
Agreement under DPDP Act 2023. Most foreign providers don't. You do. This is a
hard lock-in that price cannot compete with.

---

## Quality without compromise — how to deliver it

### The hybrid routing engine (core product mechanism)

Never serve a request that will return worse results than the customer expects.
Route intelligently based on task complexity, not just cost.

```
Every request
  │
  ├─ Task classifier → task_type + complexity_score (0-1)
  │
  ├─ complexity < 0.6 → local model (always cheaper, good enough)
  │
  ├─ complexity 0.6–0.8 → local 32B (Qwen3-30B or Coder-32B)
  │
  └─ complexity > 0.8 → cloud fallback (charge cloud pass-through + 20% margin)
         OR → local 32B with /think mode enabled
```

**Complexity scoring signals:**
- Prompt length > 2000 tokens → +0.3
- Contains math notation (∑, ∫, equations) → +0.3
- Contains "step by step", "prove", "derive" → +0.2
- Multi-file code context > 500 lines → +0.2
- Vision + reasoning combined → +0.3
- Conversational / short → -0.2

Add `complexity_score` field to model_registry and recommender scoring.

### Quality guarantee mechanism

**Benchmark-backed claims — publish these:**

| Your model | Task | Benchmark | Score | vs. competitor |
|---|---|---|---|---|
| Qwen2.5-Coder-32B | Code | HumanEval+ | 92.7% | GPT-4o: 90.2% ✅ |
| Qwen3-30B-A3B | Reasoning | MATH-500 | 87.3% | GPT-4o-mini: 70.2% ✅ |
| Qwen3-30B-A3B | Reasoning | MATH-500 | 87.3% | Claude Haiku: 71.5% ✅ |
| Llama3.2-Vision-11B | Vision | MMBench | 72.6% | GPT-4o-mini-vision: 74% ≈ |

**Where you honestly lose (document this too — builds trust):**
- vs GPT-4o on hard reasoning: ~10% gap → route to cloud, charge pass-through
- vs Claude Sonnet on long-form writing: ~8% gap → acceptable for most use cases
- Real-time < 500ms latency: CPU 32B can't do it → route to 8B or cloud

Publishing honest benchmarks builds more trust than hiding gaps.

---

## Cost optimisation levers (GPU phase)

### 1. Spot instances — 60–70% cost reduction

Use RunPod/Vast.ai spot for batch workloads. On-demand for real-time.

```python
# In LiteLLM config — route by latency requirement
# Real-time (< 3s): on-demand GPU
# Batch (async): spot GPU

router_settings:
  routing_strategy: latency-based-routing
  # tag requests with X-Latency-Tier: realtime|batch
```

Spot saves 60–70% on batch workloads. Batch = background analysis, document processing,
code review pipelines. Most SaaS and enterprise workloads are >50% batch.

### 2. Continuous batching — 3–5x throughput improvement

vLLM PagedAttention + continuous batching turns 400 tok/s into effective
1,200–2,000 tok/s at batch size 8–32. Same GPU, 3–5x more revenue capacity.

Switch from Ollama to vLLM when moving to GPU. Ollama is single-request optimised.
vLLM is throughput optimised. At scale, vLLM wins decisively.

```bash
# vLLM with continuous batching (GPU phase)
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-Coder-32B-Instruct \
  --tensor-parallel-size 1 \
  --max-num-seqs 256 \          # batch up to 256 requests
  --enable-chunked-prefill \
  --gpu-memory-utilization 0.90
```

### 3. Speculative decoding — 2–3x latency reduction

Pair a small draft model (3B) with the large target model (32B).
Draft model proposes tokens, large model verifies in parallel.
Net: 2–3x lower latency, same quality, same GPU cost.

```yaml
# vLLM speculative decoding config
speculative_model: Qwen/Qwen3-3B   # draft model
num_speculative_tokens: 5
```

### 4. KV cache sharing — 40–60% memory reduction

For SaaS customers sending repeated system prompts (very common), cache the KV
computation for the system prompt. First request pays full cost; subsequent requests
are 40–60% cheaper.

```yaml
# vLLM prefix caching
enable_prefix_caching: true
```

### 5. Quantisation strategy by tier

| Customer tier | Model | Quantisation | Quality loss | Cost saving |
|---|---|---|---|---|
| Free / Starter | Qwen3-30B-A3B | Q4_K_M | ~1% | 50% vs FP16 |
| Growth / SaaS | Qwen3-30B-A3B | Q6_K | ~0.3% | 35% vs FP16 |
| Enterprise | Qwen3-30B-A3B | FP16 / BF16 | 0% | — |

Offer quality tiers explicitly. Charge more for FP16.

---

## Profitability model — GPU phase projections

Assumptions: Single H100 at $1.85/hr (Lambda reserved), 70% utilisation,
Qwen3-30B-A3B at 400 tok/s with continuous batching, batch size 16.

```
Monthly GPU cost:     $1.85 × 24 × 30 = $1,332/month (~₹111,000)
Tokens/month at 70%:  400 tok/s × 0.70 × 86,400 × 30 = ~730B tokens/month

Revenue at blended ₹4/1M tokens (mix of tiers):
  730B × ₹4/1M = ₹2,920,000/month (~₹29 lakhs)

Gross margin:
  Revenue:    ₹29,00,000
  GPU cost:   ₹1,11,000
  Other:      ₹20,000
  Gross profit: ₹27,69,000 (~95% gross margin)
```

**At 95% gross margin, you can price at ₹4/1M and still be 85–95% cheaper than OpenAI.**
This is the structural advantage — not temporary, because you own the model weights.

---

## Go-to-market sequence

### Month 1–2: Current VPS (validation)
- Launch free tier + Starter plan
- VPS cost is fixed — revenue target is to cover that fixed line
- Target: 10 paying developers at ₹999/month = ₹9,990/month
- If VPS bill < ₹9,990 → profitable from day 10 paying customers
- Goal: validate pricing, collect benchmark feedback, fix reliability issues
- Secondary goal: identify which task types dominate → informs GPU model selection later

### Month 3–4: First GPU (growth)
- Add 1× H100 on RunPod reserved ($1.85/hr)
- Launch SaaS Basic tier
- Target: 3–5 SaaS companies embedding the gateway
- Revenue target: ₹5–10 lakhs/month

### Month 5–6: India enterprise
- DPDP DPA ready, Keycloak SSO tested, audit trail via Prometheus + Lago
- Target: 1–2 enterprise pilots
- Revenue target: ₹15–25 lakhs/month

### Month 7+: Scale GPU nodes
- Add nodes based on demand, not speculation
- Each H100 node at 70% utilisation = ~₹27L/month gross profit
- Buy vs. rent decision: at 3+ nodes for 12+ months → buy bare metal

---

## Pricing page copy (benchmark-backed)

```
Autonomyx LLM Gateway

Same accuracy as GPT-4o on code.
Half the price.
Benchmark-verified. No lock-in.

────────────────────────────────────────
Proof:
  Code:      Qwen2.5-Coder-32B → HumanEval+ 92.7% (GPT-4o: 90.2%)
  Reasoning: Qwen3-30B-A3B    → MATH-500 87.3%   (GPT-4o-mini: 70.2%)
  Vision:    Llama3.2-Vision  → MMBench 72.6%     (GPT-4o-mini: 74%)
────────────────────────────────────────

SHARED SAAS (prompts not stored, billing isolated)
  Developer      ₹999/mo       100M tokens
  Growth         ₹4,999/mo     1B tokens
  SaaS Basic     ₹14,999/mo    5B tokens + white-label + Lago sub-billing

PRIVATE DEPLOYMENT (dedicated node, full isolation, DPDP DPA)
  Private Node   ₹50,000+/mo  Your stack. Your data. Managed by us.
  India region available on private tier.

Start free → 10M tokens, no credit card.
```

---

## What to add to the skill

When generating pricing config, the skill should:

1. **Generate Lago plans** matching the three tiers above
2. **Wire complexity_score** into recommender.py routing logic
3. **Generate pricing page** as HTML artifact
4. **Document DPDP DPA** positioning in enterprise pitch

Read `references/profitability.md` (this file) before generating any billing,
pricing, or Lago plan configuration.
