# Pangolin Tunnel Setup

Open-source, self-hosted alternative to Cloudflare Tunnel.
WireGuard-based encrypted tunnels. Let's Encrypt SSL. Built-in auth.
No proprietary dashboard. Full control.

GitHub: https://github.com/fosrl/pangolin
License: AGPL-3.0

---

## Architecture

```
Browser
  ↓ HTTPS (Pangolin + Traefik + Let's Encrypt)
Pangolin server (your VPS — public IP, ports 80+443+51820)
  ↓ WireGuard encrypted tunnel
Newt container (same VPS, Docker internal network)
  ↓ Docker service name resolution
dockge:5001 / grafana:3000 / glitchtip:8080 / langflow:7860
```

Pangolin and Newt run on the same VPS.
Newt connects outbound to Pangolin — no extra inbound ports beyond what
Pangolin needs (80, 443, 51820 UDP for WireGuard).

---

## Step 1: Install Pangolin on your VPS

Pangolin runs as a separate Docker Compose stack alongside the gateway.
Install it in its own directory:

```bash
mkdir -p /opt/pangolin && cd /opt/pangolin

# Download installer (handles Pangolin + Gerbil + Traefik + Let's Encrypt)
curl -fsSL https://raw.githubusercontent.com/fosrl/pangolin/main/installer.sh \
  | bash

# Follow prompts:
#   Domain: tunnel.openautonomyx.com
#   Email: chinmay@openautonomyx.com (for Let's Encrypt)
#   Admin password: set a strong one
```

DNS needed before running installer:
```
tunnel.openautonomyx.com  A  51.75.251.56
*.tunnel.openautonomyx.com  A  51.75.251.56   # wildcard for subdomains
```

Firewall: keep 80, 443, and 51820/UDP open for Pangolin.

---

## Step 2: Create a Site in Pangolin dashboard

1. Open `https://tunnel.openautonomyx.com`
2. Log in with admin credentials
3. Sites → **Add Site** → name: `autonomyx-gateway` → type: **Newt Tunnel**
4. Copy the three values shown:
   - **Pangolin Endpoint**: `https://tunnel.openautonomyx.com`
   - **Newt ID**: `xxxxxxxxxxxxx`
   - **Newt Secret**: `xxxxxxxxxxxxx`
5. Add all three as GitHub Secrets:

```bash
gh secret set PANGOLIN_ENDPOINT --repo OpenAutonomyx/autonomyx-model-gateway
gh secret set NEWT_ID           --repo OpenAutonomyx/autonomyx-model-gateway
gh secret set NEWT_SECRET       --repo OpenAutonomyx/autonomyx-model-gateway
```

6. Push to main — CI injects credentials and starts `newt` container

---

## Step 3: Add Resources in Pangolin dashboard

Once Newt shows **Online** in Pangolin:

Resources → Add Resource for each service:

| Resource name | Subdomain | Target (via Newt) | Auth |
|---|---|---|---|
| Dockge | `dockge.tunnel.openautonomyx.com` | `dockge:5001` | Password |
| Grafana | `metrics.tunnel.openautonomyx.com` | `grafana:3000` | Password |
| GlitchTip | `errors.tunnel.openautonomyx.com` | `glitchtip:8080` | Password |
| Langflow | `flows.tunnel.openautonomyx.com` | `langflow:7860` | Password |
| Trust Centre | `trust.tunnel.openautonomyx.com` | `trust:80` | None |

Pangolin handles SSL automatically for all subdomains via Let's Encrypt.

---

## Step 4: Add authentication policies

For each internal tool (Dockge, Grafana, GlitchTip, Langflow):

Resource → Auth → **Password** or **TOTP** → set credentials

Pangolin's auth sits at the reverse proxy level — the service itself
doesn't need to implement auth.

---

## Pangolin vs Cloudflare Tunnel

| | Pangolin | Cloudflare Tunnel |
|---|---|---|
| Self-hosted | ✅ Full control | ❌ Cloudflare infrastructure |
| Dashboard | ✅ Your VPS | ❌ Cloudflare SaaS |
| SSL | ✅ Let's Encrypt | ✅ Cloudflare |
| Auth | ✅ Built-in | ✅ Zero Trust |
| Encryption | ✅ WireGuard | ✅ Proprietary |
| Vendor lock-in | None | Cloudflare |
| Cost | Free (AGPL) | Free tier limited |
| License | AGPL-3.0 | Proprietary |

---

## Troubleshooting

```bash
# Check Newt tunnel status
docker logs autonomyx-newt

# Verify Newt connected to Pangolin
# Should show: "Tunnel connection to server established successfully"

# Test internal service reachability from Newt
docker exec autonomyx-newt wget -qO- http://dockge:5001
docker exec autonomyx-newt wget -qO- http://grafana:3000

# Check Pangolin logs
cd /opt/pangolin && docker compose logs pangolin --tail 50
```
