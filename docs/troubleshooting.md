# Troubleshooting

## Gateway

**`401 Unauthorized`**
Your virtual key is wrong or expired.
```bash
# Verify key exists
curl https://llm.openautonomyx.com/key/info \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -G -d "key=sk-autonomyx-your-key"
```

**`429 Budget exceeded`**
You've hit your monthly budget. Check spend:
```bash
curl https://llm.openautonomyx.com/spend/logs \
  -H "Authorization: Bearer sk-autonomyx-your-key"
```
Contact support to increase your limit or upgrade your plan.

**`503 Model unavailable`**
The local model isn't loaded. Check Ollama:
```bash
docker exec autonomyx-ollama ollama ps
# If empty — model unloaded. Warm it up:
docker exec autonomyx-ollama ollama run qwen3:30b-a3b "ping" --keepalive 24h
```

**Slow first response on a model**
Model was unloaded from RAM (LRU eviction). First call reloads it — takes 30–60 seconds for 30B+ models. Subsequent calls are fast. Always-on models (Qwen3-30B, Coder-32B, Qwen2.5-14B) should not have this issue.

---

## Ollama

**Models not loading — out of memory**
Check available RAM vs loaded models:
```bash
docker exec autonomyx-ollama ollama ps
free -h
```
Reduce `OLLAMA_MAX_LOADED_MODELS` in `.env` or unload unused models:
```bash
docker exec autonomyx-ollama ollama stop llama3.1:8b
```

**`OLLAMA_KEEP_ALIVE` not working**
Ensure it's set in the Ollama container environment, not just `.env`:
```bash
docker exec autonomyx-ollama env | grep KEEP_ALIVE
```

---

## Playwright scraper

**Chrome crashes immediately**
Missing `shm_size: 256m` in docker-compose. Docker defaults `/dev/shm` to 64MB — Chrome needs 256MB minimum.

**Jobs stuck in `running` state**
Check sidecar logs:
```bash
docker logs autonomyx-playwright --tail 50
```

**`nomic-embed-text` embedding failures**
Model not pulled yet:
```bash
docker exec autonomyx-ollama ollama pull nomic-embed-text
```

**SurrealDB connection refused**
Check `SURREAL_URL`, `SURREAL_USER`, `SURREAL_PASS` in `.env`. Verify Cloud instance is reachable:
```bash
curl -H "NS: autonomyx" -H "DB: scrapes" \
  --user "root:$SURREAL_PASS" \
  "$SURREAL_URL/health"
```

---

## Langflow

**Flows not appearing after import**
Langflow doesn't auto-import from `./flows/` on startup — import manually via API or UI:
```bash
curl -X POST https://flows.openautonomyx.com/api/v1/flows/ \
  -H "Authorization: Bearer $LANGFLOW_API_KEY" \
  -d @flows/code-review.json
```

**`OpenAI API error` in flows**
The `OPENAI_API_BASE` in Langflow's env must point to `http://litellm:4000/v1`. Check:
```bash
docker exec autonomyx-langflow env | grep OPENAI_API_BASE
```

---

## Langfuse

**Traces not appearing**
Check `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` in LiteLLM's env match the Langfuse project keys.

**Wrong tenant's traces mixed together**
Each tenant must have their own Langfuse organisation. Check `kc_lago_sync.py` created the org correctly.

---

## Keycloak

**`kc_lago_sync.py` not triggering**
Check the sync container is running:
```bash
docker logs autonomyx-keycloak-lago-sync --tail 50
```

**Tenant not getting a LiteLLM virtual key**
The sync polls Keycloak every 30 seconds for group changes. Wait 30 seconds then re-check:
```bash
curl https://llm.openautonomyx.com/key/list \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY"
```

---

## Docker Hub images

**Old image cached on VPS**
```bash
docker pull thefractionalpm/autonomyx-playwright:latest
docker pull thefractionalpm/autonomyx-classifier:latest
docker pull thefractionalpm/autonomyx-translator:latest
docker compose up -d --force-recreate
```

---

## Getting help

- GitHub Issues: github.com/openautonomyx/autonomyx-model-gateway/issues
- Email: chinmay@openautonomyx.com
- Book a call: cal.com/thefractionalpm
