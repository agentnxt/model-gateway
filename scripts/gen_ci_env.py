#!/usr/bin/env python3
"""scripts/gen_ci_env.py
Generates .env.ci with placeholder values for all keys in .env.example.
Used by CI to run docker compose config --quiet without real secrets.
"""
import pathlib, sys

root = pathlib.Path(__file__).parent.parent
example = root / ".env.example"
output = root / ".env.ci"

if not example.exists():
    print(f"❌ {example} not found")
    sys.exit(1)

lines = []
for line in example.read_text().splitlines():
    if line.startswith("#") or "=" not in line:
        lines.append(line)
    else:
        key = line.split("=")[0]
        lines.append(f"{key}=ci_placeholder")

output.write_text("\n".join(lines))
print(f"✅ Generated {output} ({len([l for l in lines if '=' in l and not l.startswith('#')])} vars)")
