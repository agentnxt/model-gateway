# Langflow Integration — Autonomyx LLM Gateway

## How it works

LiteLLM exposes an OpenAI-compatible `/v1` endpoint. Langflow's **OpenAI** and **Custom OpenAI** components can point directly at it — giving every Langflow flow automatic token tracking, cost logging, fallbacks, and budget enforcement.

## Setup (Langflow UI)

1. In your Langflow flow, add an **OpenAI** model component (or **Custom OpenAI**)
2. Set these fields:

| Field | Value |
|---|---|
| OpenAI API Base | `http://litellm:4000/v1` (if co-deployed in same Docker network) |
| OpenAI API Base | `http://vps.agnxxt.com:4000/v1` (if remote) |
| API Key | Your LiteLLM virtual key (create via `/key/generate`) |
| Model Name | Any alias from `config.yaml` e.g. `gpt-4o`, `ollama/llama3`, `groq/llama3-70b` |

3. All other Langflow settings work as normal — streaming, temperature, max_tokens etc.

## Creating a Virtual Key (scoped per flow or team)

```bash
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "key_alias": "langflow-prod",
    "max_budget": 5.0,
    "budget_duration": "30d",
    "models": ["gpt-4o-mini", "ollama/llama3", "groq/llama3-70b"],
    "metadata": {"team": "langflow", "env": "prod"}
  }'
```

Use the returned `key` value as the API Key in Langflow.

## Environment variable approach (Langflow env)

Add to Langflow's docker-compose or `.env`:
```
OPENAI_API_BASE=http://litellm:4000/v1
OPENAI_API_KEY=sk-autonomyx-langflow-virtual-key
```

Langflow picks these up automatically for all OpenAI components.

## Network (Coolify)

Both Langflow and LiteLLM must be on the `coolify` external network. Verify:
```bash
docker inspect autonomyx-litellm | grep Networks
```

## Verifying token tracking

After a Langflow flow run, check spend:
```bash
curl http://localhost:4000/spend/logs?limit=10 \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" | jq '.[] | {model, spend, total_tokens, request_id}'
```
