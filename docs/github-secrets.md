# GitHub Secrets Setup

All sensitive API keys are stored as GitHub secrets and injected into the
server `.env` automatically on every deploy. Nothing sensitive is stored
in any repository or on disk in plaintext beyond the server's `.env`.

There are now two layers of GitHub-managed configuration:

- Repository secrets: base CI/CD and image build secrets
- `production` environment secrets: shared SSO, SMTP, and reporting values used at deploy time

## How it works

```
GitHub Secrets / Environment Secrets (encrypted at rest)
  ↓ injected via appleboy/ssh-action envs:
Server .env (written/updated on deploy)
  ↓ read by
docker compose (passed to containers)
```

The "Inject secrets" step in `.github/workflows/deploy.yml` runs before
`docker compose up -d` and writes each non-empty secret to `.env`.
Existing values are overwritten. Missing GitHub Secrets are skipped
(the key stays as whatever value was previously in `.env`).

---

## Required GitHub Secrets

Go to: `github.com/OpenAutonomyx/autonomyx-model-gateway/settings/secrets/actions`

## Required Production Environment Secrets

Go to:

- `Settings → Environments → production → Environment secrets`

These shared secrets are designed to be reused across multiple services.

### Shared SSO / OIDC

| Secret | Description |
|---|---|
| `LOGTO_ISSUER` | Logto issuer URL |
| `LOGTO_CLIENT_ID` | Logto app client ID |
| `LOGTO_CLIENT_SECRET` | Logto app client secret |
| `LOGTO_REDIRECT_URL` | Logto redirect URL |
| `LOGTO_POST_LOGOUT_REDIRECT_URL` | Logto post-logout redirect URL |
| `SSO_ENABLED` | Enable shared SSO contract, usually `true` |
| `SSO_PROVIDER` | Identity provider label, e.g. `logto` |
| `SSO_ISSUER` | Generic OIDC issuer URL |
| `SSO_CLIENT_ID` | Generic OIDC client ID |
| `SSO_CLIENT_SECRET` | Generic OIDC client secret |
| `SSO_REDIRECT_URL` | Generic app/proxy callback URL |
| `SSO_POST_LOGOUT_REDIRECT_URL` | Generic logout redirect URL |
| `SSO_SCOPES` | Usually `openid profile email offline_access` |
| `SSO_CLAIM_EMAIL` | Email claim, usually `email` |
| `SSO_CLAIM_NAME` | Name claim, usually `name` |
| `SSO_CLAIM_GROUPS` | Optional groups claim |
| `SSO_ALLOWED_DOMAINS` | Optional domain allowlist |
| `SSO_SESSION_SECRET` | Shared proxy/session secret |
| `SSO_PROXY_URL` | Shared auth proxy URL if used |

### Shared SMTP / Notifications

| Secret | Description |
|---|---|
| `SMTP_HOST` | SMTP hostname |
| `SMTP_PORT` | SMTP port, usually `587` |
| `SMTP_USERNAME` | SMTP username |
| `SMTP_PASSWORD` | SMTP password or API key |
| `SMTP_FROM_ADDRESS` | Default sender address |
| `SMTP_FROM_NAME` | Default sender label |
| `SMTP_USE_TLS` | Usually `True` |
| `SMTP_USE_SSL` | Usually `False` |
| `SMTP_SKIP_VERIFY` | Only `true` for exceptional cases |
| `SMTP_CONNECTION_URL` | Full SMTP connection URL for apps that need one string |

### Shared Reporting Sinks

| Secret | Description |
|---|---|
| `REPORTING_DEFAULT_FROM` | Shared reporting from address |
| `REPORTING_REPLY_TO` | Shared reply-to |
| `REPORTING_EMAIL_ENABLED` | Toggle email reporting |
| `REPORTING_EMAIL_TO` | Comma-separated email recipients |
| `REPORTING_EMAIL_CC` | Optional CC |
| `REPORTING_EMAIL_BCC` | Optional BCC |
| `REPORTING_SLACK_ENABLED` | Toggle Slack reporting |
| `REPORTING_SLACK_WEBHOOK_URL` | Slack incoming webhook |
| `REPORTING_SLACK_CHANNEL` | Default Slack channel |
| `REPORTING_SLACK_USERNAME` | Display username |
| `REPORTING_WEBHOOK_ENABLED` | Toggle generic webhook reporting |
| `REPORTING_WEBHOOK_URL` | Generic webhook target |
| `REPORTING_WEBHOOK_AUTH_HEADER` | Optional auth header name |
| `REPORTING_WEBHOOK_AUTH_TOKEN` | Optional auth token |
| `REPORTING_GLITCHTIP_ENABLED` | Toggle GlitchTip reporting integration |
| `REPORTING_GLITCHTIP_URL` | GlitchTip base URL |
| `REPORTING_GLITCHTIP_AUTH_TOKEN` | GlitchTip API token |
| `REPORTING_LANGFUSE_ENABLED` | Toggle Langfuse reporting integration |
| `REPORTING_LANGFUSE_HOST` | Langfuse host URL |
| `REPORTING_LANGFUSE_PUBLIC_KEY` | Langfuse public key |
| `REPORTING_LANGFUSE_SECRET_KEY` | Langfuse secret key |

### Health / Observability

| Secret | Description |
|---|---|
| `UPTIME_KUMA_ENABLED` | Toggle Uptime Kuma deployment path, usually `true` |
| `UPTIME_KUMA_URL` | Public Uptime Kuma URL used by monitors |
| `UPTIME_KUMA_INTERNAL_URL` | Internal Uptime Kuma URL for service wiring |
| `SIGNOZ_ENABLED` | Enable SigNoz Cloud dual-export collector config |
| `SIGNOZ_URL` | Public SigNoz URL for monitor links |
| `SIGNOZ_REGION` | SigNoz Cloud region slug, e.g. `us` or `in` |
| `SIGNOZ_INGESTION_KEY` | SigNoz Cloud ingestion key |

### Infrastructure (CI/CD)

| Secret | Description |
|---|---|
| `SSH_PRIVATE_KEY` | Private key for SSH access to VPS (`ssh-keygen -t ed25519`) |
| `DOCKERHUB_USERNAME` | Docker Hub username for pushing custom images |
| `DOCKERHUB_TOKEN` | Docker Hub access token (not password) |

### LiteLLM

| Secret | Description |
|---|---|
| `LITELLM_MASTER_KEY` | Gateway master key — prefix with `sk-` e.g. `sk-autonomyx-...` |

### AI Model Providers

| Secret | Description | Where to get |
|---|---|---|
| `GROQ_API_KEY` | Groq cloud LLM (fallback) | console.groq.com/keys |
| `ANTHROPIC_API_KEY` | Anthropic Claude (fallback) | console.anthropic.com/keys |
| `OPENAI_API_KEY` | OpenAI GPT (fallback) | platform.openai.com/api-keys |
| `VERTEX_PROJECT_ID` | Google Cloud project ID | console.cloud.google.com |
| `VERTEX_LOCATION` | Vertex AI region e.g. `us-central1` | console.cloud.google.com |

### Payments

| Secret | Description | Where to get |
|---|---|---|
| `RAZORPAY_KEY_ID` | Razorpay API key ID | dashboard.razorpay.com/app/keys |
| `RAZORPAY_KEY_SECRET` | Razorpay API secret | dashboard.razorpay.com/app/keys |
| `STRIPE_SECRET_KEY` | Stripe secret key | dashboard.stripe.com/apikeys |

### Monitoring

| Secret | Description | Where to get |
|---|---|---|
| `GLITCHTIP_AUTH_TOKEN` | GlitchTip API token for monitor bootstrap | errors.openautonomyx.com/profile/auth-tokens/ |

---

## Setting a secret

```bash
# Via GitHub CLI (fastest)
gh secret set GROQ_API_KEY --repo OpenAutonomyx/autonomyx-model-gateway

# Or paste in the GitHub UI:
# Settings → Secrets and variables → Actions → New repository secret
```

---

## Rotation

To rotate a key:

1. Generate new key from the provider
2. Update the GitHub Secret
3. Push any commit to `main` (or use `workflow_dispatch`) to trigger deploy
4. CI injects the new key to server `.env` and restarts services automatically

No SSH access required. No manual `.env` editing.

For shared SSO / SMTP / reporting values, update the `production`
environment secret and trigger a deploy. The workflow writes only
non-empty values, so unset secrets do not blank existing server config.

---

## What is NOT in GitHub Secrets

These are auto-generated by `scripts/bootstrap_env.sh` on first deploy
and stored only in server `.env`:

- `LITELLM_UI_PASSWORD`
- `POSTGRES_PASSWORD`
- `LANGFLOW_SECRET_KEY`, `LANGFLOW_DB_PASSWORD`, `LANGFLOW_ADMIN_PASSWORD`
- `GLITCHTIP_SECRET_KEY`, `GLITCHTIP_DB_PASSWORD`
- `OPENFGA_DB_PASSWORD`, `OPENFGA_PRESHARED_KEY`
- `SURREAL_PASS`

These are infrastructure passwords for internal services — they never
leave the VPS and don't need to be in GitHub Secrets.

### OVH API (for automated VPS provisioning)

| Secret | Description | Where to get |
|---|---|---|
| `OVH_APPLICATION_KEY` | OVH API application key | eu.api.ovh.com/createToken/ |
| `OVH_APPLICATION_SECRET` | OVH API application secret | eu.api.ovh.com/createToken/ |
| `OVH_CONSUMER_KEY` | OVH API consumer key | eu.api.ovh.com/createToken/ |
| `OVH_VPS_NAME` | VPS service name e.g. `vps-abc123.vps.ovh.net` | OVH control panel |

Required API rights when generating the token:
```
GET  /me/sshKey
GET  /me/sshKey/*
POST /me/sshKey
DELETE /me/sshKey/*
GET  /vps
GET  /vps/*
POST /vps/*/reinstall
```

Usage: `python3 scripts/provision_vps.py`

### Hostinger API (alternative to OVH)

| Secret | Description | Where to get |
|---|---|---|
| `HOSTINGER_API_TOKEN` | Hostinger API token | hPanel → Account → API → Generate token |
| `HOSTINGER_VM_ID` | VM ID (numeric) | hPanel URL: `/vps/{VM_ID}/overview` |

Usage: `python3 scripts/provision_vps_hostinger.py`

**Hostinger advantage over OVH:** Hostinger also provides a first-party
GitHub Action that deploys Docker Compose apps with just an API key —
no SSH key management needed in CI at all:

```yaml
- uses: hostinger/deploy-on-vps@v2
  with:
    api-key: ${{ secrets.HOSTINGER_API_TOKEN }}
    virtual-machine: ${{ vars.HOSTINGER_VM_ID }}
    docker-compose-path: docker-compose.yml
```

### frp Tunnel (Apache 2.0 — no cloud, no vendor lock-in)

| Secret | Description | Notes |
|---|---|---|
| `FRP_TOKEN` | Shared auth token between frps and frpc | Auto-generated by `bootstrap_server.sh` if not set. Add here to persist across rebuilds. `openssl rand -hex 32` |
