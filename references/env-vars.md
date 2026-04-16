# .env Variables Reference — All Providers

Generate .env.example from this. Never emit real keys.

## Gateway Core
```
LITELLM_MASTER_KEY=sk-autonomyx-YOUR_MASTER_KEY_HERE
LITELLM_UI_USERNAME=admin
LITELLM_UI_PASSWORD=YOUR_UI_PASSWORD_HERE
DATABASE_URL=postgresql://litellm:litellm_pass@litellm-db:5432/litellm
STORE_MODEL_IN_DB=True
```

## Postgres
```
POSTGRES_USER=litellm
POSTGRES_PASSWORD=YOUR_DB_PASSWORD_HERE
POSTGRES_DB=litellm
```

## Grafana
```
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=YOUR_GRAFANA_PASSWORD_HERE
```

## Local Models (no key needed, just host)
```
# Ollama — running on the Docker host
# Default: http://host.docker.internal:11434
# No key required

# vLLM — running on the Docker host
# Default: http://host.docker.internal:8000/v1
# No key required

# HuggingFace TGI
HF_TOKEN=hf_YOUR_TOKEN_HERE
```

## OpenAI
```
OPENAI_API_KEY=sk-YOUR_OPENAI_KEY_HERE
```

## Anthropic / Claude
```
ANTHROPIC_API_KEY=sk-ant-YOUR_ANTHROPIC_KEY_HERE
```

## Google Gemini
```
GEMINI_API_KEY=YOUR_GEMINI_KEY_HERE
```

## Microsoft Azure OpenAI
```
AZURE_API_KEY=YOUR_AZURE_KEY_HERE
AZURE_API_BASE=https://YOUR_RESOURCE.openai.azure.com
AZURE_API_VERSION=2024-02-15-preview
```

## AWS Bedrock
```
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_HERE
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_HERE
AWS_REGION=ap-south-1
```

## Mistral AI
```
MISTRAL_API_KEY=YOUR_MISTRAL_KEY_HERE
```

## Groq
```
GROQ_API_KEY=gsk_YOUR_GROQ_KEY_HERE
```

## Fireworks AI
```
FIREWORKS_API_KEY=fw_YOUR_FIREWORKS_KEY_HERE
```

## Together AI
```
TOGETHER_API_KEY=YOUR_TOGETHER_KEY_HERE
```

## OpenRouter
```
OPENROUTER_API_KEY=sk-or-YOUR_OPENROUTER_KEY_HERE
```

## Lago Billing
```
LAGO_API_URL=https://billing.openautonomyx.com
LAGO_API_KEY=YOUR_LAGO_API_KEY_HERE
LAGO_SECRET_KEY_BASE=YOUR_64_CHAR_SECRET_HERE
LAGO_ENCRYPTION_PRIMARY_KEY=YOUR_32_CHAR_KEY_HERE
LAGO_ENCRYPTION_DETERMINISTIC_KEY=YOUR_32_CHAR_KEY_HERE
LAGO_ENCRYPTION_KEY_DERIVATION_SALT=YOUR_32_CHAR_SALT_HERE
LAGO_DB_PASSWORD=YOUR_LAGO_DB_PASSWORD_HERE
# Generate secrets: openssl rand -hex 32
```

## Docker Mailserver
```
MAIL_PASSWORD=YOUR_MAIL_PASSWORD_HERE
SMTP_HOST=mailserver
SMTP_PORT=587
SMTP_USERNAME=billing@openautonomyx.com
SMTP_PASSWORD=YOUR_MAIL_PASSWORD_HERE
SMTP_FROM=billing@openautonomyx.com
```

## Keycloak
```
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=YOUR_KC_ADMIN_PASSWORD_HERE
KEYCLOAK_DB_PASSWORD=YOUR_KC_DB_PASSWORD_HERE
KC_REALM=autonomyx
```

## Pre-flight Guard
```
DEFAULT_TPM_LIMIT=100000    # tokens per minute per key per model
```

## Model Recommender
```
RECOMMENDER_INFERENCE_MODEL=claude-haiku-4-5-20251001
PROMETHEUS_URL=http://prometheus:9090
```

## Local Classifier
```
CLASSIFIER_URL=http://classifier:8100
CONFIDENCE_THRESHOLD=0.80
AUTO_RETRAIN_ON_STARTUP=true
# local = fully offline, auto = cloud upgrade on low confidence (if key present)
RECOMMENDER_MODE=local
```

## Langfuse Observability
```
LANGFUSE_DB_PASSWORD=YOUR_LANGFUSE_DB_PASSWORD
LANGFUSE_NEXTAUTH_SECRET=YOUR_NEXTAUTH_SECRET   # openssl rand -base64 32
LANGFUSE_SALT=YOUR_SALT                          # openssl rand -base64 32
LANGFUSE_ENCRYPTION_KEY=YOUR_HEX_KEY            # openssl rand -hex 32
LANGFUSE_ADMIN_EMAIL=admin@openautonomyx.com
LANGFUSE_ADMIN_PASSWORD=YOUR_ADMIN_PASSWORD
LANGFUSE_ADMIN_KEY=YOUR_LANGFUSE_ADMIN_KEY
LANGFUSE_KC_CLIENT_ID=langfuse
LANGFUSE_KC_CLIENT_SECRET=YOUR_KC_CLIENT_SECRET
LANGFUSE_INIT_ORG_ID=autonomyx-platform
LANGFUSE_INIT_PROJECT_ID=platform-default
LANGFUSE_DEFAULT_PUBLIC_KEY=pk-lf-YOUR_KEY
LANGFUSE_DEFAULT_SECRET_KEY=sk-lf-YOUR_KEY
# Populated automatically by kc_lago_sync.py as tenants are created:
LANGFUSE_TENANT_KEYS=
```

## Model Improvement Pipeline
```
IMPROVEMENT_OPT_IN_KEYS=           # comma-separated LiteLLM key aliases
TENANT_SEGMENTS=                    # alias:segment e.g. acme:legal,globex:bfsi
IMPROVEMENT_DB_URL=postgresql://improvement:pass@improvement-db:5432/improvement
RAG_EMBED_MODEL=nomic-embed-text
RAG_TOP_K=3
RAG_CHUNK_SIZE=512
```

## Human Feedback
```
# No new vars — reuses LANGFUSE_TENANT_KEYS for routing
# CORS origins for feedback widget (customer browser requests)
FEEDBACK_ALLOWED_ORIGINS=*
```

## Translation Sidecar
```
TRANSLATOR_URL=http://translator:8200
INDICTRANS2_DEVICE=cpu
OPUS_MT_CACHE=/models/opus
```

## Two-Node Setup (96GB node, after migration)
```
# Secondary node service endpoints
# Use private network IPs if nodes are co-located (recommended)
LANGFUSE_URL=https://traces.openautonomyx.com
LAGO_API_URL=https://billing.openautonomyx.com
KC_BASE_URL=https://auth.openautonomyx.com
# Private network alternative:
# LANGFUSE_URL=http://10.0.0.2:3000
# LAGO_API_URL=http://10.0.0.2:3001
# KC_BASE_URL=http://10.0.0.2:8080
```

## Langflow
```
LANGFLOW_DB_PASSWORD=YOUR_LANGFLOW_DB_PASSWORD
LANGFLOW_SECRET_KEY=YOUR_32_CHAR_SECRET        # openssl rand -hex 32
LANGFLOW_ADMIN_EMAIL=admin@openautonomyx.com
LANGFLOW_ADMIN_PASSWORD=YOUR_LANGFLOW_PASSWORD
# Virtual key scoped for Langflow — create via /key/generate
LANGFLOW_VIRTUAL_KEY=sk-autonomyx-langflow-prod
```

## Playwright Scraper
```
# SurrealDB connection (already set if using SurrealDB Cloud)
SURREAL_URL=https://schemadb-06ehsj292ppah8kbsk9pmnjjbc.aws-aps1.surreal.cloud
SURREAL_USER=root
SURREAL_PASS=YOUR_SURREAL_PASS
# Models (already set from Ollama + LiteLLM)
EXTRACT_MODEL=ollama/qwen3:30b-a3b
EMBED_MODEL=nomic-embed-text
CHUNK_SIZE=512
CHUNK_OVERLAP=64
MAX_PAGES=200
```
