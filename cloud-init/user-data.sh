#!/usr/bin/env bash
# cloud-init/user-data.sh
#
# Paste this into OVH VPS "User data" field at creation time.
# Runs automatically on first boot — no manual SSH needed.
#
# OVH: Order VPS → "Additional options" → "User data" → paste this script
# Hetzner: Create server → "User data" → paste this script
# DigitalOcean: Create Droplet → "User data" → paste this script
#
# After boot completes (~3-5 minutes):
#   1. Add SSH_PRIVATE_KEY to GitHub Secrets
#   2. Push to main — CI deploys everything

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

LOG="/var/log/autonomyx-bootstrap.log"
exec > >(tee -a "$LOG") 2>&1

echo "═══════════════════════════════════════════════════════════"
echo "Autonomyx cloud-init bootstrap — $(date)"
echo "═══════════════════════════════════════════════════════════"

# ── Apt wrapper: let apt wait for the lock itself ────────────────────────────
# DPkg::Lock::Timeout covers all 4 apt locks and avoids the fuser-check race.
# cloud-init runs as root (no sudo) but the shell alias still works.
APT="apt-get -o DPkg::Lock::Timeout=600"

# ── System update + upgrade ───────────────────────────────────────────────────
echo "→ Updating system packages..."
$APT update -qq
$APT upgrade -y -qq \
  -o Dpkg::Options::="--force-confdef" \
  -o Dpkg::Options::="--force-confold"
$APT autoremove -y -qq

# ── Core packages ─────────────────────────────────────────────────────────────
echo "→ Installing core packages..."
$APT install -y -qq \
  curl wget git ca-certificates gnupg \
  python3 python3-pip \
  openssl jq unzip \
  unattended-upgrades apt-listchanges \
  fail2ban

# ── Docker Engine ─────────────────────────────────────────────────────────────
echo "→ Installing Docker Engine..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu \
$(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list

$APT update -qq
$APT install -y -qq \
  docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker
echo "  Docker: $(docker --version)"

# ── ubuntu user ───────────────────────────────────────────────────────────────
echo "→ Configuring ubuntu user..."
if ! id ubuntu &>/dev/null; then
  useradd -m -s /bin/bash ubuntu
fi
usermod -aG docker ubuntu
mkdir -p /home/ubuntu/.ssh
chmod 700 /home/ubuntu/.ssh
# Copy root's authorized_keys so ubuntu user also has SSH access
if [ -f /root/.ssh/authorized_keys ]; then
  cp /root/.ssh/authorized_keys /home/ubuntu/.ssh/authorized_keys
  chmod 600 /home/ubuntu/.ssh/authorized_keys
  chown -R ubuntu:ubuntu /home/ubuntu/.ssh
fi
echo "  ubuntu user ready, added to docker group"

# ── Clone repo ────────────────────────────────────────────────────────────────
echo "→ Cloning autonomyx-model-gateway..."
DEPLOY_DIR="/home/ubuntu/autonomyx-model-gateway"
if [ ! -d "$DEPLOY_DIR/.git" ]; then
  git clone https://github.com/OpenAutonomyx/autonomyx-model-gateway.git "$DEPLOY_DIR"
fi
cp "$DEPLOY_DIR/.env.example" "$DEPLOY_DIR/.env" 2>/dev/null || true
chown -R ubuntu:ubuntu "$DEPLOY_DIR"
echo "  Repo cloned to $DEPLOY_DIR"

# ── Unattended security upgrades ─────────────────────────────────────────────
echo "→ Configuring unattended-upgrades..."
cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Download-Upgradeable-Packages "1";
EOF

cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOF'
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
EOF

systemctl enable unattended-upgrades
systemctl restart unattended-upgrades

# ── fail2ban (SSH brute-force protection) ─────────────────────────────────────
echo "→ Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << 'EOF'
[sshd]
enabled  = true
port     = ssh
maxretry = 5
bantime  = 3600
findtime = 600
EOF
systemctl enable fail2ban
systemctl restart fail2ban
echo "  fail2ban: SSH brute-force protection enabled"

# ── Firewall ──────────────────────────────────────────────────────────────────
echo "→ Configuring ufw firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh    comment "SSH"
ufw allow 80     comment "HTTP"
ufw allow 443    comment "HTTPS"
echo "  ufw: SSH + HTTP + HTTPS allowed, all else denied"

# ── Swap (useful for 2-4GB VPS) ───────────────────────────────────────────────
echo "→ Configuring swap..."
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -lt 8192 ] && [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo "/swapfile none swap sw 0 0" >> /etc/fstab
  echo "  2GB swap created (RAM: ${TOTAL_RAM}MB)"
else
  echo "  Swap: skipped (RAM ${TOTAL_RAM}MB >= 8GB or swap exists)"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Bootstrap complete — $(date)"
echo ""
echo "Server IP:  $(hostname -I | awk '{print $1}')"
echo "Docker:     $(docker --version)"
echo "Compose:    $(docker compose version)"
echo ""
echo "Next steps:"
echo "  1. Add SSH_PRIVATE_KEY to GitHub Secrets"
echo "     (use existing key from authorized_keys, or generate new)"
echo "  2. Add all API key GitHub Secrets (see docs/github-secrets.md)"
echo "  3. Push to main — CI deploys everything automatically"
echo ""
echo "Bootstrap log: $LOG"
echo "═══════════════════════════════════════════════════════════"

# Signal completion via a marker file
touch /var/lib/autonomyx-bootstrap-complete
