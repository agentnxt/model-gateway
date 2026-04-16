# Tenant Onboarding

One command provisions a new tenant across all systems — Keycloak, Lago, LiteLLM, Langfuse, Langflow.

## Automated onboarding

```bash
# Create a Keycloak group — kc_lago_sync.py handles the rest
KC_TOKEN=$(curl -s -X POST https://auth.openautonomyx.com/realms/master/protocol/openid-connect/token \
  -d "grant_type=password&client_id=admin-cli&username=admin&password=$KEYCLOAK_ADMIN_PASSWORD" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -X POST https://auth.openautonomyx.com/admin/realms/autonomyx/groups \
  -H "Authorization: Bearer $KC_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "tenant-acme"}'
```

`kc_lago_sync.py` automatically:
1. Creates a Lago customer (`external_customer_id: tenant-acme`)
2. Generates a LiteLLM virtual key with budget limits matching their plan
3. Creates a Langfuse organisation for their traces
4. Creates a Langflow API key scoped to their tenant
5. Assigns them to the correct Lago plan

---

## What the customer receives

After onboarding, send the customer:

```
Gateway API endpoint:   https://llm.openautonomyx.com/v1
Virtual key:            sk-autonomyx-acme-xxxxxxxx
Langflow endpoint:      https://flows.openautonomyx.com
Langflow API key:       lf-acme-xxxxxxxx
Documentation:          https://github.com/openautonomyx/autonomyx-model-gateway/docs
```

---

## Plan limits

| Plan | Monthly budget | TPM limit | Models |
|---|---|---|---|
| Free | $2 (~10M tokens) | 10k | Local only |
| Developer ₹999 | $5 (~100M tokens) | 50k | Local + Groq |
| Growth ₹4,999 | $25 (~1B tokens) | 200k | All models |
| SaaS Basic ₹14,999 | $100 (~5B tokens) | 500k | All + white-label |
| Private Node ₹50,000+ | Unlimited | Unlimited | Dedicated |

---

## Private node customer

For Private Node tier customers, additionally:

1. Provision their VPS (or they bring their own)
2. Send them `docker-compose.private-node.yml` and `.env.private-node` with values filled in
3. Their Langfuse keys, LiteLLM virtual key, and Keycloak credentials are pre-filled

```bash
# They run this on their VPS
docker compose -f docker-compose.private-node.yml --env-file .env.private-node up -d
```

Models pull automatically based on their VPS RAM tier.

---

## Offboard a tenant

```bash
# Delete Keycloak group — kc_lago_sync.py handles the rest
curl -X DELETE https://auth.openautonomyx.com/admin/realms/autonomyx/groups/{group_id} \
  -H "Authorization: Bearer $KC_TOKEN"
```

This automatically:
- Archives the Lago customer (stops billing)
- Revokes the LiteLLM virtual key
- Disables the Langfuse organisation
