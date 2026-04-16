#!/usr/bin/env bash
# scripts/bootstrap_server.sh — One-time server setup
#
# Run this ONCE on a fresh Ubuntu 24.04 VPS before the first CI deploy.
# After this script, everything else is handled by CI/CD.
#
# Usage (from your local machine):
#   ssh root@vps.openautonomyx.com 'bash -s' < scripts/bootstrap_server.sh
#
# Or directly on the server:
#   curl -sSL https://raw.githubusercontent.com/OpenAutonomyx/autonomyx-model-gateway/main/scripts/bootstrap_server.sh | bash

set -euo pipefail

REPO_URL="https://github.com/OpenAutonomyx/autonomyx-model-gateway.git"
DEPLOY_DIR="/home/ubuntu/autonomyx-model-gateway"
DEPLOY_USER="ubuntu"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     Autonomyx — Server Bootstrap                         ║"
echo "║     Fresh Ubuntu 24.04 VPS setup                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── System update + upgrade ───────────────────────────────────────────────────
echo "── Step 1/7: System update + upgrade ────────────────────"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
echo "  Upgrading packages (this may take a few minutes)..."
apt-get upgrade -y -qq \
  -o Dpkg::Options::="--force-confdef" \
  -o Dpkg::Options::="--force-confold"
apt-get autoremove -y -qq
apt-get autoclean -qq
echo "  ✅ System upgraded"
echo ""

# ── System packages ───────────────────────────────────────────────────────────
echo "── Step 2/7: System packages ────────────────────────────"
apt-get install -y -qq \
  curl wget git ca-certificates gnupg \
  python3 python3-pip \
  openssl \
  jq \
  unzip \
  unattended-upgrades \
  apt-listchanges

# Configure unattended security upgrades
cat > /etc/apt/apt.conf.d/20auto-upgrades << 'APTEOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Download-Upgradeable-Packages "1";
APTEOF

cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'APTEOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};
Unattended-Upgrade::Package-Blacklist {
    "docker-ce";
    "docker-ce-cli";
    "containerd.io";
    "docker-buildx-plugin";
    "docker-compose-plugin";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Mail "chinmay@openautonomyx.com";
Unattended-Upgrade::MailReport "on-change";
APTEOF

systemctl enable unattended-upgrades
systemctl restart unattended-upgrades
echo "  ✅ System packages installed"
echo "  ✅ Unattended security upgrades configured (Docker pinned — updated via CI only)"
echo ""

# ── Docker ────────────────────────────────────────────────────────────────────
echo "── Step 3/7: Docker ─────────────────────────────────────"
if command -v docker &>/dev/null; then
  DOCKER_VER=$(docker --version)
  echo "  ⏭  Docker already installed: $DOCKER_VER"
else
  echo "  Installing Docker Engine..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc

  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu \
$(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list

  apt-get update -qq
  apt-get install -y -qq \
    docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

  systemctl enable docker
  systemctl start docker

  echo "  ✅ Docker installed: $(docker --version)"
fi

# Add ubuntu user to docker group
if id "$DEPLOY_USER" &>/dev/null; then
  usermod -aG docker "$DEPLOY_USER" 2>/dev/null || true
  echo "  ✅ $DEPLOY_USER added to docker group"
fi
echo ""

# ── SSH key for CI/CD ─────────────────────────────────────────────────────────
echo "── Step 4/7: SSH authorized_keys ────────────────────────"
mkdir -p /root/.ssh
chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

if [ ! -f /root/.ssh/authorized_keys ] || ! grep -q "autonomyx-ci" /root/.ssh/authorized_keys 2>/dev/null; then
  echo ""
  echo "  ⚠️  Add your CI deploy key to /root/.ssh/authorized_keys"
  echo "  Generate one with:"
  echo "    ssh-keygen -t ed25519 -C 'autonomyx-ci' -f ~/.ssh/autonomyx_ci"
  echo "  Then:"
  echo "    cat ~/.ssh/autonomyx_ci.pub >> /root/.ssh/authorized_keys"
  echo "    # Add ~/.ssh/autonomyx_ci (private key) as SSH_PRIVATE_KEY GitHub Secret"
  echo ""
else
  echo "  ✅ CI deploy key already in authorized_keys"
fi
echo ""

# ── Clone repo ────────────────────────────────────────────────────────────────
echo "── Step 5/7: Clone repository ───────────────────────────"
if [ -d "$DEPLOY_DIR/.git" ]; then
  echo "  ⏭  Repo already cloned at $DEPLOY_DIR"
else
  echo "  Cloning $REPO_URL..."
  git clone "$REPO_URL" "$DEPLOY_DIR"
  echo "  ✅ Cloned to $DEPLOY_DIR"
fi

# Set ownership
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR" 2>/dev/null || true
echo ""

# ── .env file ─────────────────────────────────────────────────────────────────
echo "── Step 6/7: Environment file ───────────────────────────"
if [ -f "$DEPLOY_DIR/.env" ]; then
  echo "  ⏭  .env already exists"
else
  cp "$DEPLOY_DIR/.env.example" "$DEPLOY_DIR/.env"
  echo "  ✅ .env created from .env.example"
  echo "  ⚠️  External API keys will be injected by first CI deploy"
fi
echo ""

# ── Firewall ──────────────────────────────────────────────────────────────────
echo "── Step 7/7: Firewall (ufw) ─────────────────────────────"
if command -v ufw &>/dev/null; then
  ufw --force enable || true
  ufw allow ssh    comment "SSH"    2>/dev/null || true
  ufw allow 80     comment "HTTP"   2>/dev/null || true
  ufw allow 443    comment "HTTPS"  2>/dev/null || true
  echo "  ✅ ufw enabled: SSH + HTTP + HTTPS allowed"
else
  echo "  ⏭  ufw not available — configure firewall manually"
fi
echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
echo "══════════════════════════════════════════════════════════"
echo "  Server bootstrap complete."
echo ""
echo "  Next steps:"
echo "  1. Add SSH deploy key to /root/.ssh/authorized_keys"
echo "  2. Add GitHub Secrets (see docs/github-secrets.md):"
echo "     SSH_PRIVATE_KEY, DOCKERHUB_USERNAME, DOCKERHUB_TOKEN"
echo "     GROQ_API_KEY, ANTHROPIC_API_KEY, ... (all API keys)"
echo "  3. Push to main — CI handles everything from here"
echo ""
echo "  Server: $(hostname -I | awk '{print $1}')"
echo "  Docker: $(docker --version)"
echo "  Git:    $(git --version)"
echo "══════════════════════════════════════════════════════════"
