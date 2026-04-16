# Quick Start

Make your first API call in 5 minutes.

## What you need

- Your gateway endpoint: `https://llm.openautonomyx.com/v1`
- Your virtual key: `sk-autonomyx-xxxx` (provided during onboarding)

---

## Option A — Direct API (OpenAI-compatible)

Works with any OpenAI SDK. Just change the base URL and API key.

**Python:**
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://llm.openautonomyx.com/v1",
    api_key="sk-autonomyx-your-key",
)

response = client.chat.completions.create(
    model="ollama/qwen3:30b-a3b",  # or let the gateway recommend
    messages=[{"role": "user", "content": "Summarise this contract for risk clauses"}],
)
print(response.choices[0].message.content)
```

**JavaScript:**
```javascript
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://llm.openautonomyx.com/v1",
  apiKey: "sk-autonomyx-your-key",
});

const response = await client.chat.completions.create({
  model: "ollama/qwen3:30b-a3b",
  messages: [{ role: "user", content: "Review this code for bugs" }],
});
console.log(response.choices[0].message.content);
```

**curl:**
```bash
curl https://llm.openautonomyx.com/v1/chat/completions \
  -H "Authorization: Bearer sk-autonomyx-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama/qwen3:30b-a3b",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

---

## Option B — Let the gateway pick the model

Use the `/recommend` endpoint — the gateway selects the best model for your prompt based on task type and your budget:

```bash
# Get recommendation
curl https://llm.openautonomyx.com/recommend \
  -H "Authorization: Bearer sk-autonomyx-your-key" \
  -d '{"prompt": "Write a Python function to validate GST numbers", "top_n": 1}'

# Response
{
  "task_type": "code",
  "recommendations": [
    {"alias": "ollama/qwen2.5-coder:32b", "fit_score": 97, "reason": "Best code model"}
  ]
}
```

---

## Option C — Call a pre-built workflow

Your Langflow API key: `lf-acme-xxxx` (provided during onboarding)

```bash
# Code review — returns structured JSON
curl https://flows.openautonomyx.com/api/v1/run/code-review \
  -H "Authorization: Bearer lf-acme-your-key" \
  -d '{
    "input_value": "def get_user(id):\n    return db.execute(f\"SELECT * FROM users WHERE id={id}\")",
    "language": "python",
    "context": "production API"
  }'
```

See [Flows Reference](./flows-reference.md) for all 12 pre-built workflows.

---

## Available models

| Alias | Best for | Notes |
|---|---|---|
| `ollama/qwen3:30b-a3b` | Reasoning, chat, analysis, policy | Always-on |
| `ollama/qwen2.5-coder:32b` | Code review, generation, debugging | Always-on |
| `ollama/qwen2.5:14b` | Data extraction, structured output | Always-on |
| `ollama/llama3.2-vision:11b` | Image analysis | Warm slot |
| `ollama/llama3.1:8b` | Fast chat, simple tasks | Warm slot |
| `ollama/gemma3:9b` | Long documents | Warm slot |
| `gpt-4o` | Complex reasoning (cloud fallback) | Billed at cost |
| `claude-3-5-sonnet` | Writing, analysis (cloud fallback) | Billed at cost |
| `groq/llama3-70b` | Fast cloud inference | Billed at cost |

---

## Check your budget

```bash
curl https://llm.openautonomyx.com/key/info \
  -H "Authorization: Bearer sk-autonomyx-your-key" \
  -G -d "key=sk-autonomyx-your-key"

# Response
{
  "spend": 0.42,
  "max_budget": 5.00,
  "remaining": 4.58,
  "budget_duration": "30d",
  "reset_at": "2026-05-01T00:00:00Z"
}
```

---

## Submit feedback

Help improve the models — rate any response:

```bash
curl https://llm.openautonomyx.com/feedback \
  -H "Authorization: Bearer sk-autonomyx-your-key" \
  -d '{
    "trace_id": "response-id-from-completion",
    "score": 1,
    "comment": "Accurate and well-structured"
  }'
```

`score: 1` = good, `score: 0` = bad.
