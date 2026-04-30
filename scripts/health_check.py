#!/usr/bin/env python3
"""
Minimal runtime health checks for the primary node stack.
Used by deploy workflow and can also be run manually.
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request


def check(name: str, url: str, expected: set[int], headers: dict[str, str] | None = None) -> bool:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok = resp.status in expected
            print(f"{'PASS' if ok else 'FAIL'}  {name}: {url} -> {resp.status}")
            return ok
    except urllib.error.HTTPError as exc:
        ok = exc.code in expected
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {url} -> {exc.code}")
        return ok
    except Exception as exc:
        print(f"FAIL  {name}: {url} -> {type(exc).__name__}: {exc}")
        return False


def main() -> int:
    litellm_key = os.environ.get("LITELLM_MASTER_KEY", "")
    checks = [
        ("LiteLLM health", "http://127.0.0.1:4000/health", {200}, {"Authorization": f"Bearer {litellm_key}"} if litellm_key else {}),
        ("Grafana", "http://127.0.0.1:3000/api/health", {200}),
        ("Langflow", "http://127.0.0.1:7860/", {200}),
        ("GlitchTip", "http://127.0.0.1:8080/", {200, 302}),
        ("Uptime Kuma", "http://127.0.0.1:3001/", {200, 302}),
        ("Trust", "http://127.0.0.1:8888/", {200}),
    ]

    passed = 0
    failed = 0
    for name, url, expected, *rest in checks:
        headers = rest[0] if rest else None
        if check(name, url, expected, headers):
            passed += 1
        else:
            failed += 1

    print(f"\nHealth summary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
