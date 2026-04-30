#!/usr/bin/env python3
"""
scripts/bootstrap_glitchtip_monitors.py
Configure GlitchTip uptime monitors via API after first deploy.
Idempotent — skips monitors that already exist by name.

Called by CI/CD deploy pipeline.
Requires GLITCHTIP_URL, GLITCHTIP_AUTH_TOKEN in environment.

GlitchTip uptime monitors poll each endpoint every 60s by default.
On failure: creates an Issue, sends email alert to project members.
"""

import os, sys, json
import urllib.request, urllib.error

GLITCHTIP_URL   = os.environ.get("GLITCHTIP_URL",        "http://glitchtip:8080")
AUTH_TOKEN      = os.environ.get("GLITCHTIP_AUTH_TOKEN", "")
ORG_SLUG        = os.environ.get("GLITCHTIP_ORG_SLUG",   "autonomyx")
PROJECT_SLUG    = os.environ.get("GLITCHTIP_PROJECT_SLUG","gateway")
UPTIME_KUMA_URL = os.environ.get("UPTIME_KUMA_URL", "https://uptime.openautonomyx.com")
SIGNOZ_ENABLED  = os.environ.get("SIGNOZ_ENABLED", "false").lower() == "true"
SIGNOZ_URL      = os.environ.get("SIGNOZ_URL", "")

# Endpoints to monitor — name, url, expected status code
MONITORS = [
    {
        "name":              "Gateway API — Health",
        "url":               "https://llm.openautonomyx.com/health",
        "expected_status":   200,
        "interval_seconds":  60,
        "monitor_type":      "GET",
    },
    {
        "name":              "Trust Centre",
        "url":               "https://trust.openautonomyx.com",
        "expected_status":   200,
        "interval_seconds":  60,
        "monitor_type":      "GET",
    },
    {
        "name":              "Langflow — Workflows",
        "url":               "https://flows.openautonomyx.com",
        "expected_status":   200,
        "interval_seconds":  120,
        "monitor_type":      "GET",
    },
    {
        "name":              "Grafana — Metrics",
        "url":               "https://metrics.openautonomyx.com",
        "expected_status":   200,
        "interval_seconds":  120,
        "monitor_type":      "GET",
    },
    {
        "name":              "GlitchTip — Error Tracking",
        "url":               "https://errors.openautonomyx.com",
        "expected_status":   200,
        "interval_seconds":  120,
        "monitor_type":      "GET",
    },
    {
        "name":              "Gateway API — Models",
        "url":               "https://llm.openautonomyx.com/v1/models",
        "expected_status":   200,
        "interval_seconds":  60,
        "monitor_type":      "GET",
    },
    {
        "name":              "Agent Discovery",
        "url":               "https://llm.openautonomyx.com/.well-known/agent-configuration",
        "expected_status":   200,
        "interval_seconds":  300,
        "monitor_type":      "GET",
    },
    {
        "name":              "Uptime Kuma",
        "url":               UPTIME_KUMA_URL,
        "expected_status":   200,
        "interval_seconds":  120,
        "monitor_type":      "GET",
    },
]

if SIGNOZ_ENABLED and SIGNOZ_URL:
    MONITORS.append({
        "name":              "SigNoz",
        "url":               SIGNOZ_URL,
        "expected_status":   200,
        "interval_seconds":  120,
        "monitor_type":      "GET",
    })


def api(method: str, path: str, data: dict = None) -> dict:
    url  = f"{GLITCHTIP_URL}/api/0{path}"
    body = json.dumps(data).encode() if data else None
    req  = urllib.request.Request(
        url, data=body, method=method,
        headers={
            "Authorization": f"Bearer {AUTH_TOKEN}",
            "Content-Type":  "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()) if r.length else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code}: {body}")


def main():
    if not AUTH_TOKEN:
        print("⚠️  GLITCHTIP_AUTH_TOKEN not set — skipping monitor bootstrap")
        print("   Set it in .env after creating a GlitchTip API token at:")
        print(f"   {GLITCHTIP_URL}/profile/auth-tokens/")
        sys.exit(0)

    print(f"Configuring GlitchTip uptime monitors ({GLITCHTIP_URL})...")

    # Fetch existing monitors
    try:
        existing = api("GET", f"/organizations/{ORG_SLUG}/monitors/")
    except RuntimeError as e:
        print(f"⚠️  Could not reach GlitchTip API: {e}")
        print("   GlitchTip may not be ready yet — monitors will be configured on next deploy")
        sys.exit(0)

    existing_names = {m["name"] for m in existing}

    created = 0
    skipped = 0

    for monitor in MONITORS:
        if monitor["name"] in existing_names:
            print(f"  ⏭  {monitor['name']} — already exists")
            skipped += 1
            continue

        try:
            api("POST", f"/organizations/{ORG_SLUG}/monitors/", {
                "name":             monitor["name"],
                "url":              monitor["url"],
                "expected_status":  monitor["expected_status"],
                "interval_seconds": monitor["interval_seconds"],
                "monitor_type":     monitor["monitor_type"],
                "project":          PROJECT_SLUG,
            })
            print(f"  ✅ {monitor['name']} — created ({monitor['interval_seconds']}s interval)")
            created += 1
        except RuntimeError as e:
            print(f"  ❌ {monitor['name']} — failed: {e}")

    print(f"\nDone: {created} created, {skipped} already existed")
    print(f"View monitors at: {GLITCHTIP_URL}/organizations/{ORG_SLUG}/uptime-monitors/")


if __name__ == "__main__":
    main()
