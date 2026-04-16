#!/usr/bin/env bash
# scripts/bootstrap_env.sh — Generate all missing secrets in .env
#
# Safe: NEVER overwrites an existing non-empty, non-placeholder value.
# Run once on first deploy, or any time a new secret is added.
#
# Usage:
#   chmod +x scripts/bootstrap_env.sh
#   ./scripts/bootstrap_env.sh
#   ./scripts/bootstrap_env.sh --dry-run   # preview without writing

set -euo pipefail

ENV_FILE="${ENV_FILE:-.env}"
DRY_RUN=false

# ── Parse args ────────────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --env=*)   ENV_FILE="${arg#--env=}" ;;
  esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────

hex()    { openssl rand -hex "$1"; }
b64()    { openssl rand -base64 "$1" | tr -d '\n=/+' | head -c "$1"; }
django() { python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + '!@#%^&*(-_=+)') for _ in range(50)))"; }

# Returns current value of a key in .env (empty string if missing/placeholder)
current() {
  local key="$1"
  local val
  val=$(grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || echo "")
  # Treat placeholder values as empty
  if echo "$val" | grep -qE "^YOUR_|^CHANGE_ME|^<|^\s*$"; then
    echo ""
  else
    echo "$val"
  fi
}

# Write or update a key in .env
write_key() {
  local key="$1"
  local val="$2"
  local desc="$3"

  local existing
  existing=$(current "$key")

  if [ -n "$existing" ]; then
    echo "  ⏭  $key — already set"
    return
  fi

  if [ "$DRY_RUN" = true ]; then
    echo "  🔑 $key = [would generate: $desc]"
    return
  fi

  if grep -qE "^${key}=" "$ENV_FILE" 2>/dev/null; then
    # Key exists but is empty/placeholder — replace it
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    # Key doesn't exist — append
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
  echo "  ✅ $key — generated"
}

# ── Pre-flight ────────────────────────────────────────────────────────────────

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     Autonomyx — Secrets Bootstrap                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
[ "$DRY_RUN" = true ] && echo "  ⚠️  DRY RUN — nothing will be written" && echo ""

if [ ! -f "$ENV_FILE" ]; then
  if [ -f ".env.example" ]; then
    echo "  No .env found — copying from .env.example..."
    cp .env.example "$ENV_FILE"
  else
    echo "  No .env found — creating empty file"
    touch "$ENV_FILE"
  fi
fi

echo "  Target: $ENV_FILE"
echo ""

# ── LiteLLM ──────────────────────────────────────────────────────────────────
echo "── LiteLLM ──────────────────────────────────────────────"
write_key "LITELLM_MASTER_KEY"   "sk-$(hex 32)"        "sk- prefixed hex 64"
write_key "LITELLM_UI_USERNAME"  "admin"                "static: admin"
write_key "LITELLM_UI_PASSWORD"  "$(hex 16)"            "hex 32"
write_key "DATABASE_URL" \
  "postgresql://litellm:$(hex 16)@litellm-db:5432/litellm" \
  "postgres DSN with random password"

# ── Postgres (shared instance — superuser + per-app passwords) ──────────────
echo ""
echo "── Postgres (shared) ───────────────────────────────────"
write_key "POSTGRES_ROOT_PASSWORD" "$(hex 32)"           "hex 64 (superuser)"
write_key "POSTGRES_PASSWORD"      "$(hex 16)"           "hex 32 (litellm app)"

# ── Langflow ─────────────────────────────────────────────────────────────────
echo ""
echo "── Langflow ─────────────────────────────────────────────"
write_key "LANGFLOW_SECRET_KEY"      "$(hex 32)"        "hex 64"
write_key "LANGFLOW_DB_PASSWORD"     "$(hex 16)"        "hex 32"
write_key "LANGFLOW_ADMIN_PASSWORD"  "$(hex 16)"        "hex 32"
write_key "LANGFLOW_DATABASE_URL" \
  "postgresql://langflow:$(hex 16)@langflow-db:5432/langflow" \
  "postgres DSN"

# ── GlitchTip ────────────────────────────────────────────────────────────────
echo ""
echo "── GlitchTip ────────────────────────────────────────────"
write_key "GLITCHTIP_SECRET_KEY"   "$(django)"          "Django secret key (50 chars)"
write_key "GLITCHTIP_DB_PASSWORD"  "$(hex 16)"          "hex 32"
write_key "SECRET_KEY"             "$(django)"          "Django secret key (alias)"

# ── OpenFGA ───────────────────────────────────────────────────────────────────
echo ""
echo "── OpenFGA ──────────────────────────────────────────────"
write_key "OPENFGA_DB_PASSWORD"    "$(hex 16)"          "hex 32"
write_key "OPENFGA_PRESHARED_KEY"  "$(hex 32)"          "hex 64"
# OPENFGA_STORE_ID and OPENFGA_AUTH_MODEL_ID are set post-deploy by CI

# ── SurrealDB ────────────────────────────────────────────────────────────────
echo ""
echo "── SurrealDB ────────────────────────────────────────────"
write_key "SURREAL_USER"  "root"          "static: root"
write_key "SURREAL_PASS"  "$(hex 24)"     "hex 48"
write_key "SURREAL_URL"   "http://surrealdb:8000"  "internal container URL"

# ── External API keys — injected by CI from GitHub Secrets ──────────────────
echo ""
echo "── External API keys (injected by CI from GitHub Secrets) ──"
for key in GROQ_API_KEY ANTHROPIC_API_KEY OPENAI_API_KEY \
           VERTEX_PROJECT_ID VERTEX_LOCATION \
           RAZORPAY_KEY_ID RAZORPAY_KEY_SECRET STRIPE_SECRET_KEY \
           GLITCHTIP_AUTH_TOKEN LITELLM_MASTER_KEY; do
  val=$(current "$key")
  if [ -z "$val" ]; then
    echo "  ⏳ $key — not yet set (will be injected by next CI deploy)"
  else
    echo "  ✅ $key — present"
  fi
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════════"
if [ "$DRY_RUN" = true ]; then
  echo "  Dry run complete — no changes made."
else
  echo "  Bootstrap complete."
  echo ""
  echo "  Next steps:"
  echo "  1. Add missing external API keys to .env manually"
  echo "  2. Push to main — CI will deploy with these secrets"
  echo "  3. After first deploy, SurrealDB migration:"
  echo "     ./scripts/migrate_surrealdb.sh"
fi
echo "══════════════════════════════════════════════════════════"
# Infisical + pgAdmin (fix: was calling nonexistent generate_if_missing)
write_key "INFISICAL_ENCRYPTION_KEY" "$(openssl rand -hex 16)"         "hex 32"
write_key "INFISICAL_AUTH_SECRET"    "$(openssl rand -base64 32)"      "base64 32"
write_key "INFISICAL_DB_PASSWORD"    "$(openssl rand -hex 32)"         "hex 64"
write_key "PGADMIN_PASSWORD"         "$(openssl rand -hex 16)"         "hex 32"
