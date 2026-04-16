# Segment-Specific Model Improvement — Autonomyx LLM Gateway

## Principle

> Improve models for specific customer segments using consented trace data.
> Always opt-in. Never assume consent. Improvement compounds over time.

Four techniques, applied in order of complexity:

```
Week 1–2:  Prompt optimisation     (no GPU, immediate wins)
Week 3–4:  Routing optimisation    (no GPU, cost + quality wins)
Month 2:   RAG                     (no fine-tuning, domain knowledge)
Month 3+:  Fine-tuning (LoRA)      (GPU required, permanent improvement)
```

---

## Opt-in consent mechanism

### ToS language (shared SaaS)

```
Model Improvement Programme (Optional)

You may opt in to allow Autonomyx to use anonymised traces from your 
account to improve local model performance for your customer segment.

What this means:
- Your prompt inputs and model outputs are anonymised (PII stripped)
- Used only to fine-tune models for your industry segment
- Never shared with other customers or third parties
- You can withdraw consent at any time — historical traces deleted within 30 days
- Opting in does not affect your service or pricing

To opt in: Settings → Model Improvement → Enable
```

### Implementation in Langfuse callback

```python
# In lago_callback.py — check opt-in flag before logging to improvement dataset

IMPROVEMENT_OPT_IN_KEYS = set(
    os.environ.get("IMPROVEMENT_OPT_IN_KEYS", "").split(",")
)  # populated from DB or env as customers opt in

class LagoCallback(CustomLogger):
    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        key_alias = kwargs.get("metadata", {}).get("user_api_key_alias", "default")

        # Standard Langfuse trace (always — for customer's own observability)
        self._log_to_langfuse(key_alias, kwargs, response_obj, start_time, end_time)

        # Improvement dataset (opt-in only)
        if key_alias in IMPROVEMENT_OPT_IN_KEYS:
            self._log_to_improvement_dataset(key_alias, kwargs, response_obj)

    def _log_to_improvement_dataset(self, key_alias, kwargs, response_obj):
        """
        Anonymise and store trace for fine-tuning dataset.
        PII stripping must run before storage.
        """
        from improvement.anonymiser import strip_pii
        messages = kwargs.get("messages", [])
        output = (response_obj.get("choices", [{}])[0]
                  .get("message", {}).get("content", ""))

        clean_input  = strip_pii(messages)
        clean_output = strip_pii(output)

        # Store in improvement DB (separate from operational Postgres)
        # Keyed by segment, not by customer — customer identity not stored
        segment = self._get_segment(key_alias)
        store_improvement_trace(
            segment=segment,
            task_type=kwargs.get("metadata", {}).get("task_type", "unknown"),
            messages=clean_input,
            output=clean_output,
            model=response_obj.get("model", "unknown"),
            quality_score=None,  # filled later by eval pipeline
        )

    def _get_segment(self, key_alias: str) -> str:
        """Map key alias to industry segment. Loaded from config."""
        segment_map = {
            k: v for k, v in (
                e.split(":") for e in
                os.environ.get("TENANT_SEGMENTS", "").split(",")
                if ":" in e
            )
        }
        return segment_map.get(key_alias, "general")
```

### Env vars for improvement pipeline

```
# Opt-in tenant keys (comma-separated key aliases)
IMPROVEMENT_OPT_IN_KEYS=langflow-prod,acme-legal,globex-fintech

# Segment mapping (alias:segment)
TENANT_SEGMENTS=langflow-prod:code,acme-legal:legal,globex-fintech:bfsi

# Improvement dataset DB (separate from operational DB)
IMPROVEMENT_DB_URL=postgresql://improvement:pass@improvement-db:5432/improvement
```

---

## Technique 1 — Prompt optimisation (Week 1–2)

**No GPU. No fine-tuning. Immediate quality wins.**

### How it works

Langfuse captures every prompt + response. You score them (LLM-as-judge or human).
Find which system prompt variants produce highest scores. Bake winners into LiteLLM config
per tenant.

### LLM-as-judge eval in Langfuse

```python
# Run weekly — scores all unscored traces for a segment
import langfuse
from anthropic import Anthropic

lf = langfuse.Langfuse(...)
anthropic_client = Anthropic()

def score_trace(trace_id: str, input: str, output: str, task_type: str) -> float:
    """Score output quality 0-1 using Claude Haiku as judge."""
    prompt = f"""Rate the quality of this AI response on a scale of 0.0 to 1.0.

Task type: {task_type}
User input: {input[:500]}
AI output: {output[:500]}

Score criteria:
- 1.0: Correct, complete, well-formatted
- 0.7: Correct but incomplete or poorly formatted  
- 0.4: Partially correct
- 0.1: Incorrect or unhelpful

Respond with ONLY a decimal number between 0.0 and 1.0."""

    resp = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        score = float(resp.content[0].text.strip())
        lf.score(trace_id=trace_id, name="quality", value=score)
        return score
    except:
        return 0.5
```

### A/B testing system prompts in LiteLLM config

```yaml
# Test two system prompt variants for the same model
# LiteLLM routes 50/50 via load_balancing_group
model_list:
  - model_name: qwen3-code-v1
    litellm_params:
      model: ollama/qwen3:30b-a3b
      api_base: "http://ollama:11434"
      system_prompt: "You are a Python expert. Always add type hints."

  - model_name: qwen3-code-v2  
    litellm_params:
      model: ollama/qwen3:30b-a3b
      api_base: "http://ollama:11434"
      system_prompt: "You are a Python expert. Always add type hints and docstrings. Follow PEP 8."

router_settings:
  # A/B test: route 50/50 between variants
  model_group_alias:
    qwen3-code-ab: ["qwen3-code-v1", "qwen3-code-v2"]
```

After 7 days: query Langfuse for average quality score per variant. Winner becomes default.

---

## Technique 2 — Routing optimisation (Week 3–4)

**No GPU. Uses existing recommender.py. Cost + quality wins simultaneously.**

### How it works

After 30 days of traces, Langfuse data shows which model actually wins on which task
for which customer. Update `model_registry.json` quality scores per segment based on
real observed data — not benchmark data.

### Segment-specific quality scores

Extend `model_registry.json` with per-segment overrides:

```json
{
  "alias": "ollama/qwen3:30b-a3b",
  "quality_score": 4,
  "segment_quality_scores": {
    "code": 5,
    "legal": 3,
    "bfsi": 4,
    "general": 4
  }
}
```

Extend `recommender.py` to use segment score when available:

```python
def get_quality_score(model: dict, segment: str) -> int:
    segment_scores = model.get("segment_quality_scores", {})
    return segment_scores.get(segment, model.get("quality_score", 3))
```

### Routing insight query (run monthly from Langfuse)

```python
# Which model wins per task type per segment?
# Run this monthly to update model_registry.json

import langfuse

lf = langfuse.Langfuse(...)

def get_model_win_rates(segment: str, task_type: str) -> dict:
    traces = lf.get_traces(
        tags=[f"segment:{segment}", f"task:{task_type}"],
        limit=1000,
    )
    scores_by_model = {}
    for trace in traces.data:
        model = trace.metadata.get("model")
        score = next((s.value for s in trace.scores if s.name == "quality"), None)
        if model and score is not None:
            scores_by_model.setdefault(model, []).append(score)

    return {
        model: sum(scores) / len(scores)
        for model, scores in scores_by_model.items()
        if len(scores) >= 50  # minimum sample size
    }
```

---

## Technique 3 — RAG (Month 2)

**No fine-tuning. Domain knowledge injected at inference. Works for any segment.**

### Architecture

```
Customer prompt
  → embedding model (local: nomic-embed-text via Ollama)
  → SurrealDB vector search (already in your stack)
  → top-k relevant chunks retrieved
  → chunks prepended to prompt context
  → LiteLLM routes to model with enriched context
```

### Per-segment vector collections in SurrealDB

```sql
-- Legal segment
DEFINE TABLE legal_docs SCHEMAFULL;
DEFINE FIELD content ON legal_docs TYPE string;
DEFINE FIELD embedding ON legal_docs TYPE array;
DEFINE FIELD source ON legal_docs TYPE string;
DEFINE FIELD tenant_id ON legal_docs TYPE string;  -- per-tenant isolation
DEFINE INDEX legal_embedding ON legal_docs FIELDS embedding MTREE DIMENSION 768;

-- BFSI segment  
DEFINE TABLE bfsi_docs SCHEMAFULL;
DEFINE FIELD content ON bfsi_docs TYPE string;
DEFINE FIELD embedding ON bfsi_docs TYPE array;
DEFINE FIELD source ON bfsi_docs TYPE string;
DEFINE FIELD tenant_id ON bfsi_docs TYPE string;
DEFINE INDEX bfsi_embedding ON bfsi_docs FIELDS embedding MTREE DIMENSION 768;
```

### RAG middleware in LiteLLM custom router

```python
# rag_middleware.py — injected before routing

import httpx
import ollama

SURREAL_URL = os.environ["SURREAL_DB_URL"]
EMBED_MODEL = "nomic-embed-text"  # pulled via Ollama, 274MB
SEGMENT_COLLECTIONS = {
    "legal": "legal_docs",
    "bfsi": "bfsi_docs",
    "code": "code_docs",
}

async def enrich_with_rag(messages: list, segment: str, tenant_id: str) -> list:
    """Prepend relevant context chunks to the last user message."""
    if segment not in SEGMENT_COLLECTIONS:
        return messages

    # Get last user message
    user_msg = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"),
        None
    )
    if not user_msg:
        return messages

    # Embed query
    emb_resp = ollama.embed(model=EMBED_MODEL, input=user_msg[:512])
    query_embedding = emb_resp["embeddings"][0]

    # Vector search in SurrealDB (tenant-scoped)
    collection = SEGMENT_COLLECTIONS[segment]
    result = await surreal_vector_search(
        collection=collection,
        embedding=query_embedding,
        tenant_id=tenant_id,
        top_k=3,
    )

    if not result:
        return messages

    # Prepend context to last user message
    context = "\n\n".join(
        f"[Reference {i+1}]: {chunk['content']}"
        for i, chunk in enumerate(result)
    )
    enriched_content = f"Use the following references if relevant:\n\n{context}\n\n---\n\n{user_msg}"

    return [
        m if m["role"] != "user" or m["content"] != user_msg
        else {**m, "content": enriched_content}
        for m in messages
    ]
```

### Segment document ingestion pipeline

```python
# ingest.py — run to load domain docs per segment

import ollama
from pathlib import Path

async def ingest_documents(
    folder: str,
    segment: str,
    tenant_id: str,
    chunk_size: int = 512,
):
    """
    Chunk PDFs/text files, embed, store in SurrealDB.
    Run once per document batch. Re-run to update.
    """
    collection = SEGMENT_COLLECTIONS[segment]
    files = list(Path(folder).glob("**/*.txt")) + list(Path(folder).glob("**/*.md"))

    for file in files:
        text = file.read_text()
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

        for chunk in chunks:
            emb = ollama.embed(model=EMBED_MODEL, input=chunk)["embeddings"][0]
            await surreal_insert(
                collection=collection,
                content=chunk,
                embedding=emb,
                source=str(file),
                tenant_id=tenant_id,
            )
    print(f"Ingested {len(files)} files into {collection} for tenant {tenant_id}")
```

### Per-segment RAG document sources

| Segment | Document sources | Who provides them |
|---|---|---|
| Legal | Indian Bare Acts, court judgments, client contract templates | Customer uploads |
| BFSI | RBI circulars, SEBI guidelines, product manuals, rate sheets | Customer uploads |
| Healthcare | Clinical protocols, drug formulary, ICD-10 codes | Customer uploads |
| Code | Customer's own codebase, internal API docs, style guides | Customer uploads |
| General | None by default | — |

**Note:** Customer provides their own documents. You ingest and embed them.
Their documents are stored in their tenant-scoped collection — not shared with others.

---

## Technique 4 — Fine-tuning with LoRA (Month 3+)

**GPU required. Permanent weight update. Highest quality ceiling.**

### When to trigger fine-tuning

Only worthwhile when:
- Segment has 1,000+ opt-in traces with quality scores
- Average quality score on that segment < 0.75 (room for improvement)
- Routing optimisation has already been done (eliminate easy wins first)
- You have GPU available (RunPod A100 for training run)

### Stack: Unsloth + QLoRA

```python
# finetune.py — run on GPU node (not on VPS)

from unsloth import FastLanguageModel
from datasets import Dataset
import torch

MODEL_BASE = "Qwen/Qwen3-8B"   # fine-tune 8B, deploy 8B — fast inference
MAX_SEQ_LEN = 4096
LORA_RANK = 16

def load_segment_dataset(segment: str) -> Dataset:
    """Load opt-in traces for this segment from improvement DB."""
    # Query improvement_db for segment, quality_score >= 0.7
    # Format as instruction-following dataset
    records = query_improvement_db(segment=segment, min_quality=0.7, limit=5000)
    return Dataset.from_list([
        {
            "instruction": format_messages(r["messages"]),
            "output": r["output"],
        }
        for r in records
    ])

def finetune_for_segment(segment: str):
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_BASE,
        max_seq_length=MAX_SEQ_LEN,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_RANK,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
    )

    dataset = load_segment_dataset(segment)

    from trl import SFTTrainer
    from transformers import TrainingArguments

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="instruction",
        max_seq_length=MAX_SEQ_LEN,
        args=TrainingArguments(
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            num_train_epochs=3,
            learning_rate=2e-4,
            fp16=True,
            output_dir=f"./models/{segment}-adapter",
        ),
    )
    trainer.train()

    # Save LoRA adapter (small — ~50-200MB, not the full model)
    model.save_pretrained(f"./models/{segment}-adapter")
    tokenizer.save_pretrained(f"./models/{segment}-adapter")
    print(f"Fine-tuned adapter saved for segment: {segment}")
```

### Deploying the fine-tuned adapter via Ollama

```bash
# Create Modelfile for segment-specific model
cat > Modelfile-legal << 'EOF'
FROM qwen3:8b
ADAPTER ./models/legal-adapter
SYSTEM "You are a legal document analysis assistant specialised in Indian law."
EOF

ollama create qwen3-legal:v1 -f Modelfile-legal

# Add to config.yaml
# - model_name: ollama/qwen3-legal:v1
#   litellm_params:
#     model: ollama/qwen3-legal:v1
#     api_base: "http://ollama:11434"
```

### Routing fine-tuned models to their segment

In `recommender.py`, extend scoring to prefer segment-specific fine-tuned models:

```python
def score_model(model, task_type, segment, ...):
    score = base_score(...)

    # Bonus for segment-specific fine-tuned model
    model_segments = model.get("fine_tuned_for", [])
    if segment in model_segments:
        score += 20  # strong preference for fine-tuned variant
        reasons.append(f"fine-tuned for {segment} segment")

    return score, reasons
```

Add to `model_registry.json`:
```json
{
  "alias": "ollama/qwen3-legal:v1",
  "provider": "local",
  "task_default_for": ["extract", "reason"],
  "fine_tuned_for": ["legal"],
  "always_on": false,
  "quality_score": 5,
  "notes": "Fine-tuned on Indian legal document traces. Deploy only when legal segment active."
}
```

---

## Improvement timeline per segment

```
Week 1:  Enable Langfuse tracing
         Collect baseline quality scores
         Identify lowest-scoring task types per segment

Week 2:  Prompt A/B testing
         System prompt optimisation per segment
         Expected: 10–20% quality improvement, zero cost

Week 3:  Routing optimisation
         Update model_registry.json segment scores from real data
         Expected: 15–30% cost reduction, same quality

Month 2: RAG deployment
         Customer uploads domain docs → ingested into SurrealDB
         Expected: 20–40% quality improvement on domain-specific queries

Month 3: First fine-tuning run (if opt-in traces >= 1,000)
         Start with code or legal (cleanest traces, clearest correctness signal)
         Expected: 15–25% quality improvement on that segment vs base model

Month 6: Segment-specific models deployed
         qwen3-legal:v1, qwen3-code:v1, qwen3-bfsi:v1
         Routing sends each tenant to their optimal model automatically
         Expected: Local model matches or beats cloud on segment-specific tasks
```

---

## PII anonymisation (required before any training)

```python
# improvement/anonymiser.py

import re

PII_PATTERNS = [
    (r'\b[A-Z]{5}\d{4}[A-Z]\b', '[PAN]'),                    # PAN card
    (r'\b\d{12}\b', '[AADHAAR]'),                              # Aadhaar
    (r'\b[6-9]\d{9}\b', '[PHONE]'),                           # Indian mobile
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
    (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CARD]'),  # credit card
    (r'(?i)\b(mr|mrs|ms|dr)\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b', '[NAME]'),
]

def strip_pii(text: str | list) -> str | list:
    if isinstance(text, list):
        return [strip_pii(m) for m in text]
    if isinstance(text, dict):
        return {k: strip_pii(v) for k, v in text.items()}
    for pattern, replacement in PII_PATTERNS:
        text = re.sub(pattern, replacement, str(text))
    return text
```

---

## Env vars (add to .env.example)

```
# Model Improvement Pipeline
IMPROVEMENT_OPT_IN_KEYS=           # comma-separated key aliases
TENANT_SEGMENTS=                    # alias:segment pairs
IMPROVEMENT_DB_URL=postgresql://improvement:pass@improvement-db:5432/improvement

# RAG
RAG_EMBED_MODEL=nomic-embed-text   # pulled via Ollama automatically
RAG_TOP_K=3
RAG_CHUNK_SIZE=512
```
