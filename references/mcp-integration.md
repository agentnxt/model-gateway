# autonomyx-mcp Integration — Autonomyx LLM Gateway

## How it works

The FastMCP server uses the OpenAI Python SDK (or `litellm` library) to call models. By pointing `OPENAI_API_BASE` at the LiteLLM gateway, all MCP tool calls route through the gateway — inheriting tracking, fallbacks, and budget enforcement.

## Option A: Environment Variable Override (zero code change)

In the autonomyx-mcp docker-compose or Coolify service env:

```
OPENAI_API_BASE=http://litellm:4000/v1
OPENAI_API_KEY=sk-autonomyx-mcp-virtual-key
ANTHROPIC_API_KEY=sk-autonomyx-mcp-virtual-key  # if using anthropic SDK
ANTHROPIC_BASE_URL=http://litellm:4000
```

Any call using `openai.ChatCompletion.create(model="gpt-4o")` will route through LiteLLM transparently.

## Option B: Use litellm SDK directly in MCP tools

```python
import litellm

litellm.api_base = "http://litellm:4000/v1"
litellm.api_key = os.environ["LITELLM_VIRTUAL_KEY"]

response = litellm.completion(
    model="gpt-4o-mini",  # uses gateway alias
    messages=[{"role": "user", "content": prompt}]
)
```

## Creating a scoped Virtual Key for MCP

```bash
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "key_alias": "autonomyx-mcp-prod",
    "max_budget": 20.0,
    "budget_duration": "30d",
    "models": ["gpt-4o-mini", "claude-3-haiku", "ollama/llama3", "groq/llama3-70b"],
    "metadata": {"service": "autonomyx-mcp", "env": "prod"}
  }'
```

## Network

MCP server must be on the same Docker network as LiteLLM. On Coolify, add:
```yaml
networks:
  - coolify
```
to the autonomyx-mcp service definition.

## Verifying MCP spend

```bash
# Spend by key alias
curl http://localhost:4000/key/info?key=sk-autonomyx-mcp-virtual-key \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  | jq '{alias: .info.key_alias, spend: .info.spend, budget: .info.max_budget}'
```

## Model routing from MCP tools

MCP tools can select models by alias:
```python
# Cheap fast tool call
response = client.chat.completions.create(model="groq/llama3-70b", ...)

# High-quality reasoning tool call  
response = client.chat.completions.create(model="claude-3-5-sonnet", ...)

# Local/private data — never leaves the VPS
response = client.chat.completions.create(model="ollama/llama3", ...)
```

All three are tracked, costed, and rate-limited identically.
