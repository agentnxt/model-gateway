#!/bin/bash
# import-flows.sh — Import all Autonomyx pre-built flows into Langflow
# Run after Langflow is up and healthy.
#
# Usage:
#   LANGFLOW_URL=http://localhost:7860 LANGFLOW_TOKEN=lf-xxx ./import-flows.sh
#   OR against hosted instance:
#   LANGFLOW_URL=https://flows.openautonomyx.com LANGFLOW_TOKEN=lf-xxx ./import-flows.sh

set -e

LANGFLOW_URL="${LANGFLOW_URL:-http://langflow:7860}"
LANGFLOW_TOKEN="${LANGFLOW_TOKEN:-}"
FLOWS_DIR="${FLOWS_DIR:-./flows}"

if [ -z "$LANGFLOW_TOKEN" ]; then
  echo "Error: LANGFLOW_TOKEN not set."
  echo "Get it from Langflow UI → Settings → API Keys → New API Key"
  exit 1
fi

echo "============================================"
echo " Autonomyx Gateway — Flow Import"
echo " Target: $LANGFLOW_URL"
echo " Flows:  $FLOWS_DIR"
echo "============================================"
echo ""

# Wait for Langflow to be healthy
echo "Waiting for Langflow..."
until curl -sf "$LANGFLOW_URL/api/v1/version" > /dev/null 2>&1; do
  sleep 3
done
echo "Langflow is up."
echo ""

IMPORTED=0
FAILED=0

for flow_file in "$FLOWS_DIR"/*.json; do
  flow_name=$(basename "$flow_file" .json)

  echo -n "Importing $flow_name... "

  HTTP_STATUS=$(curl -s -o /tmp/flow_response.json -w "%{http_code}" \
    -X POST "$LANGFLOW_URL/api/v1/flows/" \
    -H "Authorization: Bearer $LANGFLOW_TOKEN" \
    -H "Content-Type: application/json" \
    -d @"$flow_file")

  if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "201" ]; then
    FLOW_ID=$(python3 -c "import json,sys; print(json.load(open('/tmp/flow_response.json')).get('id','unknown'))" 2>/dev/null || echo "unknown")
    echo "✅ (id: $FLOW_ID)"
    IMPORTED=$((IMPORTED + 1))
  else
    echo "❌ (HTTP $HTTP_STATUS)"
    cat /tmp/flow_response.json 2>/dev/null || true
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo "============================================"
echo " Import complete: $IMPORTED succeeded, $FAILED failed"
echo ""
echo " List flows:"
echo "   curl $LANGFLOW_URL/api/v1/flows/ \\"
echo "     -H 'Authorization: Bearer \$LANGFLOW_TOKEN'"
echo "============================================"
