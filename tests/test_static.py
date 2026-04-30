"""tests/test_static.py
Static validation tests — catch CI failures locally before pushing.
No external tools required (pure Python + stdlib).
Covers: compose references, frp config, secrets, env vars, workflow branches.
"""
import re
import tomllib
import pytest
import yaml
from pathlib import Path

ROOT = Path(__file__).parent.parent


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_compose(filename="docker-compose.yml"):
    path = ROOT / filename
    if not path.exists():
        pytest.skip(f"{filename} not found")
    return yaml.safe_load(path.read_text())


def load_all_workflows():
    return list((ROOT / ".github" / "workflows").glob("*.yml"))


# ── Compose: service + volume reference integrity ─────────────────────────────

def test_compose_depends_on_targets_exist():
    """Every depends_on target must be a defined service."""
    c = load_compose()
    services = set(c["services"].keys())
    errors = []
    for svc_name, svc in c["services"].items():
        deps = svc.get("depends_on", {})
        if isinstance(deps, list):
            deps = {d: {} for d in deps}
        for dep in deps:
            if dep not in services:
                errors.append(f"services[{svc_name}].depends_on: '{dep}' not defined")
    assert not errors, "\n".join(errors)


def test_compose_volume_refs_exist():
    """Every volume reference in services must be declared in the top-level volumes."""
    c = load_compose()
    declared = set((c.get("volumes") or {}).keys())
    errors = []
    for svc_name, svc in c["services"].items():
        for vol in svc.get("volumes", []):
            if isinstance(vol, str) and ":" in vol:
                ref = vol.split(":")[0]
                # Named volume (not a bind mount — bind mounts start with . or /)
                if not ref.startswith(".") and not ref.startswith("/"):
                    if ref not in declared:
                        errors.append(
                            f"services[{svc_name}].volumes: '{ref}' not in top-level volumes"
                        )
    assert not errors, "\n".join(errors)


def test_compose_unique_container_names():
    """No two services should share the same container_name."""
    c = load_compose()
    names = {}
    errors = []
    for svc_name, svc in c["services"].items():
        cn = svc.get("container_name")
        if cn:
            if cn in names:
                errors.append(
                    f"Duplicate container_name '{cn}': "
                    f"services[{names[cn]}] and services[{svc_name}]"
                )
            names[cn] = svc_name
    assert not errors, "\n".join(errors)


def test_compose_env_vars_in_example():
    """.env.example should document every ${VAR} referenced in docker-compose.yml.
    Variables with inline defaults (${VAR:-default}) are excluded — they work without .env.
    """
    compose_text = (ROOT / "docker-compose.yml").read_text()
    example_text = (ROOT / ".env.example").read_text()

    # Extract vars used in compose WITHOUT defaults
    used_no_default = set(re.findall(r'\$\{([A-Z_]+)\}', compose_text))
    # Extract vars WITH defaults (these don't need to be in .env)
    used_with_default = set(re.findall(r'\$\{([A-Z_]+):-[^}]+\}', compose_text))
    # Extract keys documented in .env.example
    documented = set(re.findall(r'^([A-Z_]+)=', example_text, re.MULTILINE))

    missing = used_no_default - used_with_default - documented
    # Exclude CI/system vars that don't need to be in .env.example
    system_vars = {"ORG", "GITHUB_SHA", "GITHUB_TOKEN"}
    missing -= system_vars

    assert not missing, (
        f"Variables used in docker-compose.yml but not documented in .env.example:\n"
        + "\n".join(f"  ${{{v}}}" for v in sorted(missing))
    )


# ── frp config: TOML syntax + subdomain uniqueness ───────────────────────────

@pytest.mark.parametrize("toml_file", [
    "frp/frps.toml",
    "frp/frpc.toml",
])
def test_frp_toml_valid(toml_file):
    """frp config files must be valid TOML."""
    path = ROOT / toml_file
    if not path.exists():
        pytest.skip(f"{toml_file} not found")
    try:
        # Replace template placeholders before parsing
        content = path.read_text().replace("{{ FRP_TOKEN }}", "placeholder")
        tomllib.loads(content)
    except tomllib.TOMLDecodeError as e:
        pytest.fail(f"Invalid TOML in {toml_file}: {e}")


def test_frpc_unique_subdomains():
    """frpc.toml must not have duplicate subdomain registrations."""
    path = ROOT / "frp" / "frpc.toml"
    if not path.exists():
        pytest.skip("frp/frpc.toml not found")
    content = path.read_text().replace("{{ FRP_TOKEN }}", "placeholder")
    data = tomllib.loads(content)
    subdomains = [p.get("subdomain") for p in data.get("proxies", []) if p.get("subdomain")]
    dupes = [s for s in subdomains if subdomains.count(s) > 1]
    assert not dupes, f"Duplicate subdomains in frpc.toml: {set(dupes)}"


def test_frpc_unique_proxy_names():
    """frpc.toml proxy names must be unique."""
    path = ROOT / "frp" / "frpc.toml"
    if not path.exists():
        pytest.skip("frp/frpc.toml not found")
    content = path.read_text().replace("{{ FRP_TOKEN }}", "placeholder")
    data = tomllib.loads(content)
    names = [p.get("name") for p in data.get("proxies", []) if p.get("name")]
    dupes = [n for n in names if names.count(n) > 1]
    assert not dupes, f"Duplicate proxy names in frpc.toml: {set(dupes)}"


# ── Secrets: every secrets.X referenced in workflows must be documented ──────

DOCUMENTED_SECRETS = {
    # Secrets we know are set via set_secrets.sh / GitHub UI
    "SSH_PRIVATE_KEY", "DOCKERHUB_USERNAME", "DOCKERHUB_TOKEN",
    "FRP_TOKEN", "LITELLM_MASTER_KEY",
    "GROQ_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
    "VERTEX_PROJECT_ID", "VERTEX_LOCATION",
    "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET",
    "STRIPE_SECRET_KEY",
    "GLITCHTIP_AUTH_TOKEN",
    "CLOUDFLARE_TUNNEL_TOKEN",
    "OVH_APPLICATION_KEY", "OVH_APPLICATION_SECRET", "OVH_CONSUMER_KEY",
    "VPS_HOST", "VPS_USERNAME", "VPS_SSH_KEY", "VPS_PORT",
    "GITHUB_TOKEN",   # Built-in GitHub secret — always available
}


def test_workflow_secrets_documented():
    """Every secrets.X referenced in workflows must be in DOCUMENTED_SECRETS."""
    errors = []
    for wf in load_all_workflows():
        content = wf.read_text()
        used = set(re.findall(r'secrets\.([A-Z_]+)', content))
        unknown = used - DOCUMENTED_SECRETS
        if unknown:
            errors.append(f"{wf.name}: undocumented secrets: {unknown}")
    assert not errors, "\n".join(errors)


# ── Workflow: branch references ────────────────────────────────────────────────

def test_workflow_branch_references():
    """Workflows triggered on push/PR should reference 'main' (our default branch)."""
    errors = []
    for wf in load_all_workflows():
        data = yaml.safe_load(wf.read_text())
        if not data:
            continue
        on = data.get("on", {})
        if isinstance(on, str):
            continue
        for trigger in ["push", "pull_request"]:
            branches = (on.get(trigger) or {}).get("branches", [])
            for branch in branches:
                if branch not in ("main", "**", "*"):
                    errors.append(
                        f"{wf.name}: trigger '{trigger}' references "
                        f"branch '{branch}' — expected 'main'"
                    )
    assert not errors, "\n".join(errors)


# ── Jaeger config: valid YAML ─────────────────────────────────────────────────

def test_jaeger_config_valid():
    """jaeger/config.yaml must be valid YAML."""
    path = ROOT / "jaeger" / "config.yaml"
    if not path.exists():
        pytest.skip("jaeger/config.yaml not found")
    try:
        data = yaml.safe_load(path.read_text())
        assert data is not None
        assert "service" in data, "Jaeger config missing 'service' key"
    except yaml.YAMLError as e:
        pytest.fail(f"Invalid YAML in jaeger/config.yaml: {e}")


# ── OPA policy: Rego syntax check (if opa CLI available) ─────────────────────

def test_opa_policy_syntax():
    """Check OPA Rego syntax if opa CLI is available."""
    import shutil, subprocess
    if not shutil.which("opa"):
        pytest.skip("opa CLI not installed")
    path = ROOT / "opa" / "policy.rego"
    if not path.exists():
        pytest.skip("opa/policy.rego not found")
    result = subprocess.run(
        ["opa", "check", str(path)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"OPA policy syntax error:\n{result.stderr}"
