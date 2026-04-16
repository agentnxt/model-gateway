#!/usr/bin/env bash
# scripts/set_secrets.sh
# Sets all GitHub Secrets for the autonomyx-model-gateway repo.
# Run once from your local machine after generating SSH key.
#
# Usage:
#   chmod +x scripts/set_secrets.sh
#   ./scripts/set_secrets.sh
#
# Prerequisites:
#   - gh CLI installed and authenticated (gh auth login)
#   - SSH key generated at ~/.ssh/autonomyx_ci
#   - Docker Hub token ready (hub.docker.com → Account Settings → Personal Access Tokens)

set -euo pipefail

REPO="OpenAutonomyx/autonomyx-model-gateway"
SSH_KEY="$HOME/.ssh/autonomyx_ci"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     Autonomyx — GitHub Secrets Setup                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Preflight checks ──────────────────────────────────────────────────────────
if ! command -v gh &>/dev/null; then
  echo "❌ gh CLI not installed."
  echo "   Install: https://cli.github.com"
  echo "   Mac: brew install gh"
  echo "   Then: gh auth login"
  exit 1
fi

if ! gh auth status &>/dev/null; then
  echo "❌ gh CLI not authenticated. Run: gh auth login"
  exit 1
fi

if [ ! -f "$SSH_KEY" ]; then
  echo "❌ SSH key not found at $SSH_KEY"
  echo "   Generate: ssh-keygen -t ed25519 -C autonomyx-ci -f ~/.ssh/autonomyx_ci -N ''"
  exit 1
fi

echo "✅ gh CLI authenticated"
echo "✅ SSH key found at $SSH_KEY"
echo ""

# ── Helper ────────────────────────────────────────────────────────────────────
set_secret() {
  local name="$1"
  local value="$2"
  if [ -z "$value" ]; then
    echo "  ⏭  $name — skipped (empty)"
    return
  fi
  echo "$value" | gh secret set "$name" --repo "$REPO"
  echo "  ✅ $name"
}

prompt_secret() {
  local name="$1"
  local hint="$2"
  local value
  echo ""
  echo "  $name"
  echo "  $hint"
  read -rsp "  Value (paste, then Enter): " value
  echo ""
  set_secret "$name" "$value"
}

# ── Required secrets ──────────────────────────────────────────────────────────
echo "── Required secrets ─────────────────────────────────────"

# SSH key (from file — no prompt needed)
gh secret set SSH_PRIVATE_KEY --repo "$REPO" < "$SSH_KEY"
echo "  ✅ SSH_PRIVATE_KEY (from $SSH_KEY)"

# Docker Hub username (hardcoded)
set_secret "DOCKERHUB_USERNAME" "thefractionalpm"

# Docker Hub token (prompt)
prompt_secret "DOCKERHUB_TOKEN" \
  "Get at: hub.docker.com → Account Settings → Personal Access Tokens → New token (Read & Write)"

# Auto-generated secrets
FRP_TOKEN=$(openssl rand -hex 32)
LITELLM_MASTER_KEY=$(openssl rand -hex 32)
set_secret "FRP_TOKEN" "$FRP_TOKEN"
set_secret "LITELLM_MASTER_KEY" "$LITELLM_MASTER_KEY"

echo ""
echo "── AI provider keys ─────────────────────────────────────"

prompt_secret "ANTHROPIC_API_KEY" \
  "Get at: console.anthropic.com → API Keys"

prompt_secret "GROQ_API_KEY" \
  "Get at: console.groq.com → API Keys (free)"

echo ""
echo "── Optional — skip with Enter ───────────────────────────"

prompt_secret "OPENAI_API_KEY" \
  "Get at: platform.openai.com → API Keys (or skip)"

prompt_secret "VERTEX_PROJECT_ID" \
  "Google Cloud project ID (or skip)"

prompt_secret "RAZORPAY_KEY_ID" \
  "Razorpay key ID (or skip — needed for billing)"

prompt_secret "STRIPE_SECRET_KEY" \
  "Stripe secret key (or skip — needed for billing)"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "── All secrets set — verifying ──────────────────────────"
gh secret list --repo "$REPO"

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  Done. Trigger first deploy:"
echo ""
echo "  git commit --allow-empty -m 'chore: first deploy'"
echo "  git push origin main"
echo ""
echo "  Watch CI:"
echo "  gh run watch --repo $REPO"
echo "══════════════════════════════════════════════════════════"
