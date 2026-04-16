"""tests/test_opa_middleware.py — OPA middleware tests."""
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
ROOT = os.path.dirname(os.path.dirname(__file__))


class TestModule:
    def test_import(self):
        from opa_middleware import router, opa_evaluate, build_opa_input, OPACallback
        assert router is not None

    def test_router_prefix(self):
        from opa_middleware import router
        assert router.prefix == "/policy"

    def test_endpoints(self):
        from opa_middleware import router
        paths = [r.path for r in router.routes]
        assert "/policy/evaluate" in paths
        assert "/policy/health" in paths


class TestModelMetadata:
    def test_all_ollama_local(self):
        from opa_middleware import MODEL_METADATA
        for alias, meta in MODEL_METADATA.items():
            if alias.startswith("ollama/"):
                assert meta["location"] == "local"
                assert meta["provider"] == "ollama"

    def test_cloud_models_have_us_region(self):
        from opa_middleware import MODEL_METADATA
        for alias, meta in MODEL_METADATA.items():
            if meta["location"] == "cloud":
                assert meta["region"] != "local", f"{alias} cloud model has local region"

    def test_groq_us(self):
        from opa_middleware import MODEL_METADATA
        assert MODEL_METADATA["groq/llama3-70b-8192"]["region"] == "us"

    def test_vertex_us_central1(self):
        from opa_middleware import MODEL_METADATA
        assert MODEL_METADATA["vertex/gemini-2.5-pro"]["region"] == "us-central1"


class TestBuildOPAInput:
    def test_builds_valid_input(self):
        from opa_middleware import build_opa_input
        kwargs = {
            "model": "ollama/qwen3:30b-a3b",
            "messages": [{"role": "user", "content": "Hello world"}],
            "litellm_params": {"metadata": {
                "agent_name": "fraud-sentinel",
                "agent_type": "workflow",
                "tenant_id":  "tenant-acme",
            }}
        }
        r = build_opa_input(kwargs)
        assert r["agent"]["name"] == "fraud-sentinel"
        assert r["model"]["location"] == "local"
        assert r["model"]["provider"] == "ollama"
        assert "prompt_length" in r["request"]
        assert "local_models_healthy" in r["system"]

    def test_unknown_model(self):
        from opa_middleware import build_opa_input
        kwargs = {"model": "unknown-model", "messages": [], "litellm_params": {"metadata": {}}}
        r = build_opa_input(kwargs)
        assert r["model"]["location"] == "unknown"

    def test_no_agent_name(self):
        from opa_middleware import build_opa_input
        kwargs = {"model": "ollama/qwen3:30b-a3b", "messages": [], "litellm_params": {"metadata": {}}}
        r = build_opa_input(kwargs)
        assert r["agent"]["name"] == "unknown"


class TestFailSafe:
    @pytest.mark.asyncio
    async def test_unreachable_fails_closed(self):
        import opa_middleware
        orig = opa_middleware.OPA_URL
        opa_middleware.OPA_URL = "http://localhost:19998"
        r = await opa_middleware.opa_evaluate({"test": True})
        opa_middleware.OPA_URL = orig
        assert r["allow"] is False
        assert "opa_unreachable" in r["deny_reasons"]


class TestPolicyFile:
    def test_exists(self):
        assert os.path.exists(os.path.join(ROOT, "opa", "policy.rego"))

    def test_test_file_exists(self):
        assert os.path.exists(os.path.join(ROOT, "opa", "policy_test.rego"))

    def test_default_deny(self):
        content = open(os.path.join(ROOT, "opa", "policy.rego")).read()
        assert "default allow := false" in content

    def test_package(self):
        content = open(os.path.join(ROOT, "opa", "policy.rego")).read()
        assert "package autonomyx.gateway" in content

    def test_all_rules(self):
        content = open(os.path.join(ROOT, "opa", "policy.rego")).read()
        for rule in ["agent_not_active", "budget_exceeded", "tpm_limit_exceeded",
                     "local_model_available_use_local", "dpdp_pii_to_us_cloud_prohibited",
                     "prompt_too_large_for_model", "ephemeral_agent_cloud_not_allowed"]:
            assert rule in content, f"Missing rule: {rule}"

    def test_dpdp(self):
        content = open(os.path.join(ROOT, "opa", "policy.rego")).read()
        assert "dpdp" in content
        assert "contains_pii" in content


class TestDockerCompose:
    def test_opa_in_compose(self):
        import yaml
        c = yaml.safe_load(open(os.path.join(ROOT, "docker-compose.yml")))
        assert "opa" in c["services"]

    def test_image_pinned(self):
        import yaml
        c = yaml.safe_load(open(os.path.join(ROOT, "docker-compose.yml")))
        assert "latest" not in c["services"]["opa"]["image"]

    def test_internal_only(self):
        import yaml
        c = yaml.safe_load(open(os.path.join(ROOT, "docker-compose.yml")))
        labels = c["services"]["opa"].get("labels", [])
        assert any("traefik.enable=false" in str(l) for l in labels)

    def test_mounts_policy(self):
        import yaml
        c = yaml.safe_load(open(os.path.join(ROOT, "docker-compose.yml")))
        volumes = c["services"]["opa"].get("volumes", [])
        assert any("opa" in str(v) for v in volumes)
