"""
kc_lago_sync.py — Keycloak group → Lago + LiteLLM + Langfuse tenant sync

Polls Keycloak for group changes every 30 seconds.
On GROUP_CREATE: provisions Lago customer + LiteLLM virtual key + Langfuse org
On GROUP_DELETE: archives Lago customer + revokes LiteLLM key

Run as a sidecar container alongside Keycloak.
"""

import os, time, json, secrets, httpx, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("kc-lago-sync")

# ── Config ─────────────────────────────────────────────────────────────────

KC_URL          = os.environ.get("KEYCLOAK_URL",          "http://keycloak:8080")
KC_REALM        = os.environ.get("KEYCLOAK_REALM",        "autonomyx")
KC_ADMIN        = os.environ.get("KEYCLOAK_ADMIN",        "admin")
KC_ADMIN_PASS   = os.environ.get("KEYCLOAK_ADMIN_PASSWORD","")

LAGO_URL        = os.environ.get("LAGO_API_URL",          "https://billing.openautonomyx.com")
LAGO_KEY        = os.environ.get("LAGO_API_KEY",          "")
LAGO_PLAN_CODE  = os.environ.get("LAGO_DEFAULT_PLAN",     "developer")  # default plan for new tenants

LITELLM_URL     = os.environ.get("LITELLM_URL",           "http://litellm:4000")
LITELLM_KEY     = os.environ.get("LITELLM_MASTER_KEY",    "")

LANGFUSE_HOST   = os.environ.get("LANGFUSE_HOST",         "https://traces.openautonomyx.com")
LANGFUSE_KEY    = os.environ.get("LANGFUSE_SECRET_KEY",   "")

POLL_INTERVAL   = int(os.environ.get("POLL_INTERVAL_SEC", "30"))

# Plan → budget mapping
PLAN_BUDGETS = {
    "free":        {"max_budget": 2.0,   "budget_duration": "30d", "tpm_limit": 10000},
    "developer":   {"max_budget": 5.0,   "budget_duration": "30d", "tpm_limit": 50000},
    "growth":      {"max_budget": 25.0,  "budget_duration": "30d", "tpm_limit": 200000},
    "saas_basic":  {"max_budget": 100.0, "budget_duration": "30d", "tpm_limit": 500000},
    "private_node":{"max_budget": 9999,  "budget_duration": "30d", "tpm_limit": 9999999},
}


# ── Keycloak auth ───────────────────────────────────────────────────────────

def get_kc_token() -> str:
    r = httpx.post(
        f"{KC_URL}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id":  "admin-cli",
            "username":   KC_ADMIN,
            "password":   KC_ADMIN_PASS,
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def list_kc_groups(token: str) -> list:
    r = httpx.get(
        f"{KC_URL}/admin/realms/{KC_REALM}/groups",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def get_kc_group_attrs(token: str, group_id: str) -> dict:
    r = httpx.get(
        f"{KC_URL}/admin/realms/{KC_REALM}/groups/{group_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("attributes", {})


def set_kc_group_attr(token: str, group_id: str, group_name: str, attrs: dict):
    r = httpx.put(
        f"{KC_URL}/admin/realms/{KC_REALM}/groups/{group_id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"name": group_name, "attributes": attrs},
        timeout=10,
    )
    r.raise_for_status()


# ── Lago ───────────────────────────────────────────────────────────────────

def create_lago_customer(external_id: str, name: str) -> dict:
    r = httpx.post(
        f"{LAGO_URL}/api/v1/customers",
        headers={"Authorization": f"Bearer {LAGO_KEY}", "Content-Type": "application/json"},
        json={"customer": {
            "external_id":   external_id,
            "name":          name,
            "billing_configuration": {"payment_provider": "stripe"},
        }},
        timeout=10,
    )
    r.raise_for_status()
    log.info(f"Lago customer created: {external_id}")
    return r.json()


def assign_lago_plan(external_id: str, plan_code: str):
    r = httpx.post(
        f"{LAGO_URL}/api/v1/subscriptions",
        headers={"Authorization": f"Bearer {LAGO_KEY}", "Content-Type": "application/json"},
        json={"subscription": {
            "external_customer_id": external_id,
            "plan_code":            plan_code,
            "external_id":          f"{external_id}-sub",
        }},
        timeout=10,
    )
    if r.status_code not in (200, 201):
        log.warning(f"Lago plan assignment failed: {r.text}")
    else:
        log.info(f"Lago plan {plan_code} assigned to {external_id}")


def archive_lago_customer(external_id: str):
    r = httpx.delete(
        f"{LAGO_URL}/api/v1/customers/{external_id}",
        headers={"Authorization": f"Bearer {LAGO_KEY}"},
        timeout=10,
    )
    log.info(f"Lago customer archived: {external_id} (status: {r.status_code})")


# ── LiteLLM ────────────────────────────────────────────────────────────────

def create_litellm_key(external_id: str, plan_code: str) -> str:
    budget = PLAN_BUDGETS.get(plan_code, PLAN_BUDGETS["developer"])
    r = httpx.post(
        f"{LITELLM_URL}/key/generate",
        headers={"Authorization": f"Bearer {LITELLM_KEY}", "Content-Type": "application/json"},
        json={
            "key_alias":       external_id,
            "max_budget":      budget["max_budget"],
            "budget_duration": budget["budget_duration"],
            "tpm_limit":       budget["tpm_limit"],
            "metadata":        {"tenant_id": external_id, "plan": plan_code},
        },
        timeout=10,
    )
    r.raise_for_status()
    key = r.json()["key"]
    log.info(f"LiteLLM key created for {external_id}")
    return key


def revoke_litellm_key(key_alias: str):
    # Get key value from alias first
    r = httpx.get(
        f"{LITELLM_URL}/key/list",
        headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        timeout=10,
    )
    if r.status_code != 200:
        return
    keys = r.json().get("keys", [])
    for k in keys:
        if k.get("key_alias") == key_alias:
            httpx.post(
                f"{LITELLM_URL}/key/delete",
                headers={"Authorization": f"Bearer {LITELLM_KEY}", "Content-Type": "application/json"},
                json={"keys": [k["key"]]},
                timeout=10,
            )
            log.info(f"LiteLLM key revoked for {key_alias}")
            return


# ── Langfuse ───────────────────────────────────────────────────────────────

def create_langfuse_org(external_id: str) -> Optional[str]:
    """Create a Langfuse organisation for the tenant."""
    try:
        r = httpx.post(
            f"{LANGFUSE_HOST}/api/admin/organizations",
            headers={"Authorization": f"Bearer {LANGFUSE_KEY}", "Content-Type": "application/json"},
            json={"name": external_id},
            timeout=10,
        )
        if r.status_code in (200, 201):
            org_id = r.json().get("id")
            log.info(f"Langfuse org created for {external_id}: {org_id}")
            return org_id
    except Exception as e:
        log.warning(f"Langfuse org creation failed for {external_id}: {e}")
    return None


# ── Main sync loop ──────────────────────────────────────────────────────────

def provision_tenant(token: str, group: dict):
    """Provision a new tenant across all systems."""
    group_id   = group["id"]
    group_name = group["name"]
    external_id = group_name  # e.g. "tenant-acme"

    log.info(f"Provisioning tenant: {external_id}")

    # Determine plan from group name suffix or default
    plan_code = LAGO_PLAN_CODE
    for plan in PLAN_BUDGETS:
        if plan in group_name.lower():
            plan_code = plan
            break

    try:
        # 1. Create Lago customer
        create_lago_customer(external_id, group_name)
        assign_lago_plan(external_id, plan_code)

        # 2. Create LiteLLM virtual key
        virtual_key = create_litellm_key(external_id, plan_code)

        # 3. Create Langfuse org
        langfuse_org_id = create_langfuse_org(external_id)

        # 4. Store provisioned state in Keycloak group attributes
        attrs = get_kc_group_attrs(token, group_id)
        attrs["provisioned"]       = ["true"]
        attrs["lago_customer_id"]  = [external_id]
        attrs["litellm_key_alias"] = [external_id]
        attrs["langfuse_org_id"]   = [langfuse_org_id or ""]
        attrs["plan"]              = [plan_code]
        set_kc_group_attr(token, group_id, group_name, attrs)

        log.info(f"Tenant {external_id} provisioned successfully. Key: {virtual_key[:20]}...")

    except Exception as e:
        log.error(f"Provisioning failed for {external_id}: {e}")


def deprovision_tenant(group_name: str):
    """Deprovision a tenant across all systems."""
    external_id = group_name
    log.info(f"Deprovisioning tenant: {external_id}")
    try:
        archive_lago_customer(external_id)
        revoke_litellm_key(external_id)
        log.info(f"Tenant {external_id} deprovisioned")
    except Exception as e:
        log.error(f"Deprovisioning failed for {external_id}: {e}")


def sync_loop():
    known_groups: dict[str, str] = {}  # group_id → group_name

    log.info("kc_lago_sync started. Polling every %ds", POLL_INTERVAL)

    while True:
        try:
            token  = get_kc_token()
            groups = list_kc_groups(token)
            current = {g["id"]: g["name"] for g in groups}

            # Detect new groups
            for gid, gname in current.items():
                if gid not in known_groups:
                    # Check if already provisioned (restart safety)
                    attrs = get_kc_group_attrs(token, gid)
                    if attrs.get("provisioned", ["false"])[0] != "true":
                        group = next((g for g in groups if g["id"] == gid), None)
                        if group:
                            provision_tenant(token, group)
                    known_groups[gid] = gname

            # Detect deleted groups
            for gid, gname in list(known_groups.items()):
                if gid not in current:
                    deprovision_tenant(gname)
                    del known_groups[gid]

        except Exception as e:
            log.error(f"Sync loop error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    sync_loop()
