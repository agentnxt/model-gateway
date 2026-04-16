# config.yaml — Annotated Template
# Copy this, remove providers you don't use, fill in env var names

# ─────────────────────────────────────────────
# MODEL LIST
# model_name  = alias exposed to clients
# litellm_params.model = provider/model string
# ─────────────────────────────────────────────

model_list:

  # ── LOCAL: Ollama ──────────────────────────
  - model_name: ollama/llama3
    litellm_params:
      model: ollama/llama3
      api_base: "http://host.docker.internal:11434"

  - model_name: ollama/mistral
    litellm_params:
      model: ollama/mistral
      api_base: "http://host.docker.internal:11434"

  # ── LOCAL: vLLM ───────────────────────────
  - model_name: vllm/llama3-70b
    litellm_params:
      model: openai/meta-llama/Meta-Llama-3-70B-Instruct
      api_base: "http://host.docker.internal:8000/v1"
      api_key: "EMPTY"

  # ── LOCAL: HuggingFace TGI ────────────────
  - model_name: tgi/mistral-7b
    litellm_params:
      model: huggingface/mistralai/Mistral-7B-Instruct-v0.2
      api_base: "http://host.docker.internal:8080"
      api_key: os.environ/HF_TOKEN

  # ── OpenAI ────────────────────────────────
  - model_name: gpt-4o
    litellm_params:
      model: gpt-4o
      api_key: os.environ/OPENAI_API_KEY

  - model_name: gpt-4o-mini
    litellm_params:
      model: gpt-4o-mini
      api_key: os.environ/OPENAI_API_KEY

  # ── Anthropic / Claude ────────────────────
  - model_name: claude-3-5-sonnet
    litellm_params:
      model: anthropic/claude-sonnet-4-5
      api_key: os.environ/ANTHROPIC_API_KEY

  - model_name: claude-3-haiku
    litellm_params:
      model: anthropic/claude-haiku-4-5-20251001
      api_key: os.environ/ANTHROPIC_API_KEY

  # ── Google Gemini ─────────────────────────
  - model_name: gemini-1.5-pro
    litellm_params:
      model: gemini/gemini-1.5-pro
      api_key: os.environ/GEMINI_API_KEY

  - model_name: gemini-1.5-flash
    litellm_params:
      model: gemini/gemini-1.5-flash
      api_key: os.environ/GEMINI_API_KEY

  # ── Microsoft Azure OpenAI ────────────────
  - model_name: azure-gpt-4o
    litellm_params:
      model: azure/gpt-4o
      api_base: os.environ/AZURE_API_BASE
      api_key: os.environ/AZURE_API_KEY
      api_version: "2024-02-15-preview"

  # ── AWS Bedrock ───────────────────────────
  - model_name: bedrock-claude-3
    litellm_params:
      model: bedrock/anthropic.claude-3-sonnet-20240229-v1:0
      aws_access_key_id: os.environ/AWS_ACCESS_KEY_ID
      aws_secret_access_key: os.environ/AWS_SECRET_ACCESS_KEY
      aws_region_name: os.environ/AWS_REGION

  # ── Mistral AI ────────────────────────────
  - model_name: mistral-large
    litellm_params:
      model: mistral/mistral-large-latest
      api_key: os.environ/MISTRAL_API_KEY

  - model_name: mistral-small
    litellm_params:
      model: mistral/mistral-small-latest
      api_key: os.environ/MISTRAL_API_KEY

  # ── Groq ──────────────────────────────────
  - model_name: groq/llama3-70b
    litellm_params:
      model: groq/llama3-70b-8192
      api_key: os.environ/GROQ_API_KEY

  - model_name: groq/mixtral
    litellm_params:
      model: groq/mixtral-8x7b-32768
      api_key: os.environ/GROQ_API_KEY

  # ── Fireworks AI ──────────────────────────
  - model_name: fireworks/llama3-70b
    litellm_params:
      model: fireworks_ai/accounts/fireworks/models/llama-v3-70b-instruct
      api_key: os.environ/FIREWORKS_API_KEY

  # ── Together AI ───────────────────────────
  - model_name: together/llama3-70b
    litellm_params:
      model: together_ai/togethercomputer/llama-3-70b-instruct
      api_key: os.environ/TOGETHER_API_KEY

  # ── OpenRouter ────────────────────────────
  - model_name: openrouter/auto
    litellm_params:
      model: openrouter/auto
      api_key: os.environ/OPENROUTER_API_KEY

  - model_name: openrouter/claude-3-opus
    litellm_params:
      model: openrouter/anthropic/claude-3-opus
      api_key: os.environ/OPENROUTER_API_KEY

# ─────────────────────────────────────────────
# ROUTER SETTINGS
# ─────────────────────────────────────────────
router_settings:
  routing_strategy: usage-based-routing
  num_retries: 3
  request_timeout: 60
  allowed_fails: 2
  retry_after: 5

  # Fallback chain: local → fast cloud → flagship
  fallbacks:
    - ollama/llama3:
        - groq/llama3-70b
        - together/llama3-70b
        - gpt-4o-mini
    - vllm/llama3-70b:
        - groq/llama3-70b
        - gpt-4o
    - tgi/mistral-7b:
        - mistral-small
        - groq/mixtral

# ─────────────────────────────────────────────
# LITELLM SETTINGS (proxy-level)
# ─────────────────────────────────────────────
litellm_settings:
  # Token counting
  drop_params: true           # silently drop unsupported params per model
  success_callback: ["langfuse"]   # optional: remove if not using Langfuse
  
  # Cost / budget tracking
  max_budget: 10.0            # USD — global hard limit
  budget_duration: 30d
  soft_budget: 8.0            # USD — triggers warning callback

  # Postgres-backed spend tracking
  store_model_in_db: true

# ─────────────────────────────────────────────
# GENERAL SETTINGS (proxy server)
# ─────────────────────────────────────────────
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL
  store_model_in_db: true
  
  # UI dashboard (LiteLLM has a built-in admin UI at /ui)
  ui_username: os.environ/LITELLM_UI_USERNAME
  ui_password: os.environ/LITELLM_UI_PASSWORD
