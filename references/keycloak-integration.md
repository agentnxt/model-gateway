# Keycloak — Tenant & User Account Management

## Role

Replaces Logto. Single Keycloak instance, single realm (`autonomyx`).

| Concept | Keycloak mapping |
|---|---|
| Tenant | Group (e.g. `tenant-acme`) |
| User | User, member of one or more groups |
| Lago customer | Synced from Keycloak group via event listener |
| LiteLLM virtual key | `key_alias` = Keycloak group ID |
| App login | OIDC → Keycloak (`auth.openautonomyx.com`) |

---

## docker-compose addition (append to Coolify stack)

```yaml
  keycloak:
    image: quay.io/keycloak/keycloak:24.0
    container_name: autonomyx-keycloak
    restart: always
    networks:
      - coolify
    command: start
    environment:
      - KC_DB=postgres
      - KC_DB_URL=jdbc:postgresql://keycloak-db:5432/keycloak
      - KC_DB_USERNAME=keycloak
      - KC_DB_PASSWORD=${KEYCLOAK_DB_PASSWORD:-keycloak_pass}
      - KC_HOSTNAME=auth.openautonomyx.com
      - KC_HOSTNAME_STRICT=true
      - KC_HTTP_ENABLED=false
      - KC_PROXY=edge
      - KEYCLOAK_ADMIN=${KEYCLOAK_ADMIN_USER:-admin}
      - KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD}
      - KC_FEATURES=token-exchange,admin-fine-grained-authz
    depends_on:
      keycloak-db:
        condition: service_healthy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.keycloak.rule=Host(`auth.openautonomyx.com`)"
      - "traefik.http.routers.keycloak.entrypoints=https"
      - "traefik.http.routers.keycloak.tls.certresolver=letsencrypt"
      - "traefik.http.services.keycloak.loadbalancer.server.port=8080"

  keycloak-db:
    image: postgres:15-alpine
    container_name: autonomyx-keycloak-db
    restart: always
    networks:
      - coolify
    environment:
      - POSTGRES_USER=keycloak
      - POSTGRES_PASSWORD=${KEYCLOAK_DB_PASSWORD:-keycloak_pass}
      - POSTGRES_DB=keycloak
    volumes:
      - keycloak-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U keycloak"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Keycloak → Lago sync service (event-driven)
  keycloak-lago-sync:
    image: python:3.12-slim
    container_name: autonomyx-kc-lago-sync
    restart: always
    networks:
      - coolify
    environment:
      - KC_BASE_URL=https://auth.openautonomyx.com
      - KC_REALM=autonomyx
      - KC_ADMIN_USER=${KEYCLOAK_ADMIN_USER:-admin}
      - KC_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD}
      - LAGO_API_URL=https://billing.openautonomyx.com
      - LAGO_API_KEY=${LAGO_API_KEY}
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}
      - LITELLM_BASE_URL=http://litellm:4000
    volumes:
      - ./kc_lago_sync.py:/app/kc_lago_sync.py:ro
    command: ["python", "/app/kc_lago_sync.py"]
    depends_on:
      - keycloak
```

Add to `volumes:` block:
```yaml
  keycloak-db-data:
```

---

## Keycloak env vars (add to .env.example)

```
# Keycloak
KEYCLOAK_ADMIN_USER=admin
KEYCLOAK_ADMIN_PASSWORD=YOUR_KC_ADMIN_PASSWORD_HERE
KEYCLOAK_DB_PASSWORD=YOUR_KC_DB_PASSWORD_HERE
KC_REALM=autonomyx
```

---

## Initial Realm Setup (run once)

```bash
# 1. Get admin token
KC_TOKEN=$(curl -s -X POST \
  https://auth.openautonomyx.com/realms/master/protocol/openid-connect/token \
  -d "client_id=admin-cli&grant_type=password&username=$KEYCLOAK_ADMIN_USER&password=$KEYCLOAK_ADMIN_PASSWORD" \
  | jq -r '.access_token')

# 2. Create autonomyx realm
curl -X POST https://auth.openautonomyx.com/admin/realms \
  -H "Authorization: Bearer $KC_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "realm": "autonomyx",
    "enabled": true,
    "displayName": "Autonomyx Platform",
    "registrationAllowed": false,
    "resetPasswordAllowed": true,
    "loginWithEmailAllowed": true,
    "duplicateEmailsAllowed": false,
    "sslRequired": "external"
  }'

# 3. Create OIDC client for LiteLLM/Langflow
curl -X POST https://auth.openautonomyx.com/admin/realms/autonomyx/clients \
  -H "Authorization: Bearer $KC_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "autonomyx-gateway",
    "enabled": true,
    "protocol": "openid-connect",
    "publicClient": false,
    "redirectUris": ["https://llm.openautonomyx.com/*"],
    "webOrigins": ["https://llm.openautonomyx.com"],
    "standardFlowEnabled": true,
    "directAccessGrantsEnabled": false
  }'
```

---

## `kc_lago_sync.py` — Event-driven Keycloak → Lago + LiteLLM sync

```python
"""
Polls Keycloak Admin Events API.
On GROUP_CREATE → create Lago customer + LiteLLM virtual key.
On GROUP_DELETE → archive Lago customer + delete LiteLLM key.
"""
import os, time, httpx, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("kc-lago-sync")

KC_BASE        = os.environ["KC_BASE_URL"]
KC_REALM       = os.environ["KC_REALM"]
KC_ADMIN_USER  = os.environ["KC_ADMIN_USER"]
KC_ADMIN_PASS  = os.environ["KC_ADMIN_PASSWORD"]
LAGO_URL       = os.environ["LAGO_API_URL"]
LAGO_KEY       = os.environ["LAGO_API_KEY"]
LITELLM_URL    = os.environ["LITELLM_BASE_URL"]
LITELLM_KEY    = os.environ["LITELLM_MASTER_KEY"]
POLL_INTERVAL  = 10   # seconds


def get_kc_token():
    r = httpx.post(
        f"{KC_BASE}/realms/master/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "grant_type": "password",
            "username": KC_ADMIN_USER,
            "password": KC_ADMIN_PASS,
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def get_admin_events(token, after_ts=None):
    params = {"resourceTypes": "GROUP", "max": 50}
    if after_ts:
        params["dateFrom"] = after_ts
    r = httpx.get(
        f"{KC_BASE}/admin/realms/{KC_REALM}/admin-events",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def create_lago_customer(group_id, group_name):
    r = httpx.post(
        f"{LAGO_URL}/api/v1/customers",
        headers={"Authorization": f"Bearer {LAGO_KEY}"},
        json={"customer": {
            "external_id": group_id,
            "name": group_name,
            "email": f"billing+{group_id}@openautonomyx.com",
            "billing_configuration": {
                "invoice_grace_period": 3,
                "payment_provider": "none",
            },
        }},
        timeout=10,
    )
    log.info(f"Lago customer create: {group_id} → {r.status_code}")


def archive_lago_customer(group_id):
    r = httpx.delete(
        f"{LAGO_URL}/api/v1/customers/{group_id}",
        headers={"Authorization": f"Bearer {LAGO_KEY}"},
        timeout=10,
    )
    log.info(f"Lago customer archive: {group_id} → {r.status_code}")


def create_litellm_key(group_id, group_name):
    r = httpx.post(
        f"{LITELLM_URL}/key/generate",
        headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        json={
            "key_alias": group_id,
            "max_budget": 10.0,
            "budget_duration": "30d",
            "metadata": {"tenant": group_name, "lago_customer_id": group_id},
        },
        timeout=10,
    )
    log.info(f"LiteLLM key create: {group_id} → {r.status_code}")
    return r.json().get("key")


def delete_litellm_key(group_id):
    # List keys to find by alias
    r = httpx.get(
        f"{LITELLM_URL}/key/list",
        headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        timeout=10,
    )
    keys = r.json().get("keys", [])
    for k in keys:
        if k.get("key_alias") == group_id:
            httpx.post(
                f"{LITELLM_URL}/key/delete",
                headers={"Authorization": f"Bearer {LITELLM_KEY}"},
                json={"keys": [k["key"]]},
                timeout=10,
            )
            log.info(f"LiteLLM key deleted: {group_id}")
            return


def main():
    log.info("Keycloak → Lago sync starting")
    last_ts = None
    processed = set()

    while True:
        try:
            token = get_kc_token()
            events = get_admin_events(token, last_ts)

            for ev in events:
                ev_id = ev.get("id") or str(ev.get("time", ""))
                if ev_id in processed:
                    continue
                processed.add(ev_id)

                op = ev.get("operationType")           # CREATE or DELETE
                resource = ev.get("resourcePath", "")  # groups/{id}

                if "groups" not in resource:
                    continue

                group_id = resource.split("/")[-1]

                # Fetch group details
                gr = httpx.get(
                    f"{KC_BASE}/admin/realms/{KC_REALM}/groups/{group_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
                group_name = gr.json().get("name", group_id) if gr.status_code == 200 else group_id

                if op == "CREATE":
                    log.info(f"Group created: {group_name} ({group_id})")
                    create_lago_customer(group_id, group_name)
                    create_litellm_key(group_id, group_name)

                elif op == "DELETE":
                    log.info(f"Group deleted: {group_id}")
                    archive_lago_customer(group_id)
                    delete_litellm_key(group_id)

                if ev.get("time"):
                    last_ts = ev["time"]

        except Exception as e:
            log.error(f"Sync error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
```

---

## Tenant lifecycle

```
New tenant signup
  → Admin creates Keycloak group "tenant-{name}"
  → kc-lago-sync detects GROUP_CREATE event
  → Creates Lago customer (external_id = group_id)
  → Creates LiteLLM virtual key (alias = group_id)
  → Assign Lago plan to customer in Lago UI
  → Share LiteLLM key with tenant

Tenant offboarded
  → Admin deletes Keycloak group
  → kc-lago-sync detects GROUP_DELETE event
  → Archives Lago customer (preserves invoice history)
  → Deletes LiteLLM virtual key (stops spend)
```

---

## User management

```bash
# Create user in realm
curl -X POST https://auth.openautonomyx.com/admin/realms/autonomyx/users \
  -H "Authorization: Bearer $KC_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice@acme.com",
    "email": "alice@acme.com",
    "enabled": true,
    "emailVerified": false,
    "credentials": [{"type": "password", "value": "TempPass123!", "temporary": true}]
  }'

# Add user to tenant group
USER_ID=$(curl -s "https://auth.openautonomyx.com/admin/realms/autonomyx/users?email=alice@acme.com" \
  -H "Authorization: Bearer $KC_TOKEN" | jq -r '.[0].id')

curl -X PUT "https://auth.openautonomyx.com/admin/realms/autonomyx/users/$USER_ID/groups/$GROUP_ID" \
  -H "Authorization: Bearer $KC_TOKEN"
```

---

## OIDC endpoints (for Langflow / LiteLLM UI / app integrations)

```
Discovery:   https://auth.openautonomyx.com/realms/autonomyx/.well-known/openid-configuration
Auth:        https://auth.openautonomyx.com/realms/autonomyx/protocol/openid-connect/auth
Token:       https://auth.openautonomyx.com/realms/autonomyx/protocol/openid-connect/token
UserInfo:    https://auth.openautonomyx.com/realms/autonomyx/protocol/openid-connect/userinfo
JWKS:        https://auth.openautonomyx.com/realms/autonomyx/protocol/openid-connect/certs
Admin UI:    https://auth.openautonomyx.com/admin/autonomyx/console
```
