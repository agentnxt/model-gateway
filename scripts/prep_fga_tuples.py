#!/usr/bin/env python3
"""
scripts/prep_fga_tuples.py
Strips JSON comments from bootstrap_tuples.json and writes
a clean payload to /tmp/fga_tuples.json for the OpenFGA write API.
Called by CI/CD deploy pipeline during OpenFGA bootstrap.
"""
import re, json, sys, os

src = os.path.join(os.path.dirname(os.path.dirname(__file__)), "openfga", "bootstrap_tuples.json")
raw   = open(src).read()
clean = re.sub(r'//.*', '', raw)
data  = json.loads(clean)

writes  = [{"tuple_key": t} for t in data["tuples"]]
payload = json.dumps({"writes": writes})

open("/tmp/fga_tuples.json", "w").write(payload)
print(f"Prepared {len(writes)} tuples → /tmp/fga_tuples.json")
