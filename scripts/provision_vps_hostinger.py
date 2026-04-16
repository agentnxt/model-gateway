#!/usr/bin/env python3
"""
scripts/provision_vps_hostinger.py
Automates Hostinger VPS provisioning after purchase:
  1. Generate SSH key pair (or use existing)
  2. Register public key to Hostinger account via API
  3. Attach SSH key to VPS
  4. Recreate VPS with Ubuntu 24.04 + SSH key
  5. Set up firewall rules (SSH + HTTP + HTTPS)
  6. Wait for VPS to become ready
  7. Print next steps

Hostinger API docs: https://developers.hostinger.com
API token: hPanel → Account → API → Generate token

Usage:
  pip install requests
  export HOSTINGER_API_TOKEN=...
  export HOSTINGER_VM_ID=...         # from hPanel URL: /vps/{VM_ID}/overview
  python3 scripts/provision_vps_hostinger.py

After this script:
  Add SSH_PRIVATE_KEY to GitHub Secrets, then push to main.
  CI handles everything from there.

Alternatively — skip SSH entirely and use the Hostinger GitHub Action:
  uses: hostinger/deploy-on-vps@v2
  with:
    api-key: ${{ secrets.HOSTINGER_API_KEY }}
    virtual-machine: ${{ vars.HOSTINGER_VM_ID }}
"""

import os, sys, time, subprocess, json
from pathlib import Path

try:
    import requests
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "--quiet"], check=True)
    import requests

# ── Config ────────────────────────────────────────────────────────────────────
API_TOKEN   = os.environ.get("HOSTINGER_API_TOKEN", "")
VM_ID       = os.environ.get("HOSTINGER_VM_ID",     "")
KEY_NAME    = os.environ.get("HOSTINGER_SSH_KEY_NAME", "autonomyx-ci")
KEY_PATH    = Path(os.environ.get("HOSTINGER_SSH_KEY_PATH",
                                  str(Path.home() / ".ssh" / "autonomyx_ci")))

BASE_URL    = "https://api.hostinger.com/v1"
POLL_INTERVAL = 10
POLL_TIMEOUT  = 600


def api(method: str, path: str, data: dict = None) -> dict:
    r = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers={
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        },
        json=data,
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text}")
    return r.json() if r.content else {}


def validate_env():
    missing = [v for v in ["HOSTINGER_API_TOKEN", "HOSTINGER_VM_ID"]
               if not os.environ.get(v)]
    if missing:
        print("❌ Missing environment variables:")
        for v in missing:
            print(f"   export {v}=...")
        print("\nHostinger API token: hPanel → Account → API → Generate token")
        print("VM ID: from hPanel URL → /vps/{VM_ID}/overview")
        sys.exit(1)


def ensure_ssh_key() -> str:
    """Generate ed25519 key pair if missing. Returns public key string."""
    priv = KEY_PATH
    pub  = KEY_PATH.with_suffix(".pub")
    if not priv.exists():
        print(f"  Generating SSH key pair at {priv}...")
        priv.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            "ssh-keygen", "-t", "ed25519",
            "-C", f"{KEY_NAME}@openautonomyx.com",
            "-f", str(priv), "-N", ""
        ], check=True, capture_output=True)
        print("  ✅ Key pair generated")
    else:
        print(f"  ⏭  Key already exists at {priv}")
    return pub.read_text().strip()


def register_ssh_key(public_key: str) -> int:
    """Register public key with Hostinger. Returns key ID."""
    # Check existing keys
    keys = api("GET", "/vps/ssh-keys")
    for k in keys.get("data", []):
        if k.get("name") == KEY_NAME:
            if k.get("key") == public_key:
                print(f"  ⏭  SSH key '{KEY_NAME}' already registered (id={k['id']})")
                return k["id"]
            else:
                print(f"  Deleting outdated key '{KEY_NAME}'...")
                api("DELETE", f"/vps/ssh-keys/{k['id']}")

    print(f"  Registering SSH key '{KEY_NAME}'...")
    result = api("POST", "/vps/ssh-keys", {
        "name": KEY_NAME,
        "key":  public_key,
    })
    key_id = result["data"]["id"]
    print(f"  ✅ SSH key registered (id={key_id})")
    return key_id


def attach_ssh_key(key_id: int):
    """Attach registered key to VPS."""
    print(f"  Attaching SSH key {key_id} to VM {VM_ID}...")
    api("POST", f"/vps/virtual-machines/{VM_ID}/ssh-keys", {
        "ids": [key_id]
    })
    print("  ✅ SSH key attached")


def get_ubuntu_template() -> int:
    """Find Ubuntu 24.04 OS template ID."""
    templates = api("GET", "/vps/templates")
    for t in templates.get("data", []):
        name = t.get("name", "").lower()
        if "ubuntu" in name and "24" in name:
            print(f"  Found: {t['name']} → id={t['id']}")
            return t["id"]

    print("  Available templates:")
    for t in templates.get("data", [])[:10]:
        print(f"    {t['id']}: {t['name']}")
    print("\n  Set HOSTINGER_TEMPLATE_ID and re-run")
    sys.exit(1)


def recreate_vps(template_id: int, key_id: int):
    """Recreate VPS with Ubuntu 24.04 and SSH key."""
    print(f"  ⚠️  Recreating VPS {VM_ID} with Ubuntu 24.04")
    print("  This will WIPE all existing data.")
    confirm = input("  Type 'yes' to confirm: ").strip().lower()
    if confirm != "yes":
        print("  Cancelled.")
        sys.exit(0)

    api("POST", f"/vps/virtual-machines/{VM_ID}/recreate", {
        "templateId": template_id,
        "sshKeyIds":  [key_id],
    })
    print("  ✅ Recreate initiated")


def setup_firewall():
    """Create firewall with SSH + HTTP + HTTPS and attach to VM."""
    print("  Creating firewall (SSH + HTTP + HTTPS)...")
    try:
        fw = api("POST", "/vps/firewalls", {"name": "autonomyx-gateway"})
        fw_id = fw["data"]["id"]

        for rule in [
            {"protocol": "TCP", "port": "22",  "source": "0.0.0.0/0"},
            {"protocol": "TCP", "port": "80",  "source": "0.0.0.0/0"},
            {"protocol": "TCP", "port": "443", "source": "0.0.0.0/0"},
        ]:
            api("POST", f"/vps/firewalls/{fw_id}/rules", rule)

        api("POST", f"/vps/virtual-machines/{VM_ID}/firewalls", {"firewallId": fw_id})
        print(f"  ✅ Firewall created and attached (id={fw_id})")
    except Exception as e:
        print(f"  ⚠️  Firewall setup failed (non-fatal): {e}")


def wait_for_ready() -> str:
    """Poll until VM state == running. Returns IPv4."""
    print(f"\n  Waiting for VM to be ready (up to {POLL_TIMEOUT//60} min)...")
    start = time.time()
    last_state = None

    while time.time() - start < POLL_TIMEOUT:
        try:
            vm = api("GET", f"/vps/virtual-machines/{VM_ID}")
            data  = vm.get("data", {})
            state = data.get("state", "unknown")
            ipv4  = next(
                (ip["ip"] for ip in data.get("ipAddresses", []) if ip.get("version") == 4),
                "unknown"
            )
            if state != last_state:
                elapsed = int(time.time() - start)
                print(f"  [{elapsed:3d}s] State: {state}")
                last_state = state
            if state == "running":
                print("  ✅ VPS ready")
                return ipv4
        except Exception as e:
            print(f"  API error: {e}")
        time.sleep(POLL_INTERVAL)

    print("  ❌ Timeout")
    sys.exit(1)


def print_next_steps(ip: str):
    priv = str(KEY_PATH)
    print(f"""
══════════════════════════════════════════════════════════
  Hostinger VPS provisioned
══════════════════════════════════════════════════════════
  IP:   {ip}
  SSH:  ssh -i {priv} root@{ip}

  Next steps:
  1. Add SSH_PRIVATE_KEY to GitHub Secrets:
     gh secret set SSH_PRIVATE_KEY \\
       --repo OpenAutonomyx/autonomyx-model-gateway \\
       < {priv}

  2. Add HOSTINGER_API_KEY + HOSTINGER_VM_ID secrets
     (optional — only needed if using hostinger/deploy-on-vps action)

  3. Add all API key secrets (see docs/github-secrets.md)

  4. Push to main:
     git commit --allow-empty -m "trigger: initial deploy"
     git push origin main
══════════════════════════════════════════════════════════

  Alternative: skip SSH-based CI entirely and use:
  hostinger/deploy-on-vps@v2 GitHub Action
  (requires only HOSTINGER_API_KEY + HOSTINGER_VM_ID)
""")


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     Autonomyx — Hostinger VPS Provisioning               ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    validate_env()

    # Verify token
    try:
        me = api("GET", "/profile")
        print(f"✅ Authenticated as: {me.get('data', {}).get('email', '?')}\n")
    except Exception as e:
        print(f"❌ Authentication failed: {e}\n")
        sys.exit(1)

    print("── Step 1/5: SSH key ────────────────────────────────────")
    public_key = ensure_ssh_key()
    key_id = register_ssh_key(public_key)
    print()

    print("── Step 2/5: Attach key to VPS ──────────────────────────")
    attach_ssh_key(key_id)
    print()

    print("── Step 3/5: Ubuntu 24.04 template ──────────────────────")
    template_id = get_ubuntu_template()
    print()

    print("── Step 4/5: Recreate VPS ───────────────────────────────")
    recreate_vps(template_id, key_id)
    print()

    print("── Step 5/5: Firewall + wait ─────────────────────────────")
    setup_firewall()
    ip = wait_for_ready()
    print()

    print_next_steps(ip)


if __name__ == "__main__":
    main()
