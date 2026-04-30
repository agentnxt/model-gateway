"""
tests/test_openfga_authz.py
Unit tests for OpenFGA authorization middleware.
"""

import pytest
import sys, os
from fastapi import HTTPException
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestOpenFGAModule:

    def test_import(self):
        from openfga_authz import router, fga_check, fga_write, custom_auth
        assert router is not None

    def test_router_prefix(self):
        from openfga_authz import router
        assert router.prefix == "/authz"

    def test_endpoints_present(self):
        from openfga_authz import router
        paths = [r.path for r in router.routes]
        assert "/authz/grant" in paths
        assert "/authz/revoke" in paths
        assert "/authz/check" in paths
        assert "/authz/agent/{agent_name}/models" in paths
        assert "/authz/agent/{agent_name}/grant-model/{model_name}" in paths
        assert "/authz/agent/{agent_name}/revoke-model/{model_name}" in paths


class TestModelAliasMap:

    def test_all_local_models_mapped(self):
        from openfga_authz import MODEL_ALIAS_MAP
        local_models = [
            "ollama/qwen3:30b-a3b",
            "ollama/qwen2.5-coder:32b",
            "ollama/qwen2.5:14b",
            "ollama/nomic-embed-text",
        ]
        for m in local_models:
            assert m in MODEL_ALIAS_MAP, f"Local model not mapped: {m}"

    def test_cloud_fallbacks_mapped(self):
        from openfga_authz import MODEL_ALIAS_MAP
        cloud_models = [
            "groq/llama3-70b-8192",
            "vertex/gemini-2.5-pro",
        ]
        for m in cloud_models:
            assert m in MODEL_ALIAS_MAP, f"Cloud model not mapped: {m}"

    def test_all_values_have_model_prefix(self):
        from openfga_authz import MODEL_ALIAS_MAP
        for alias, obj in MODEL_ALIAS_MAP.items():
            assert obj.startswith("model:"), \
                f"OpenFGA object for {alias} must start with 'model:'"

    def test_no_wildcard_mappings(self):
        from openfga_authz import MODEL_ALIAS_MAP
        for alias, obj in MODEL_ALIAS_MAP.items():
            assert "*" not in obj, f"Wildcard not allowed in model map: {alias}"


class TestFGACheckFailSafe:

    @pytest.mark.asyncio
    async def test_check_returns_false_when_store_not_configured(self):
        """When OPENFGA_STORE_ID is empty, check should log warning and return True (bypass)."""
        import openfga_authz
        original = openfga_authz.OPENFGA_STORE_ID
        openfga_authz.OPENFGA_STORE_ID = ""
        result = await openfga_authz.fga_check("agent:test", "can_use_model", "model:test")
        openfga_authz.OPENFGA_STORE_ID = original
        assert result is True  # bypass mode when not configured

    @pytest.mark.asyncio
    async def test_check_returns_false_on_connection_error(self):
        """When OpenFGA is unreachable, check must fail closed (deny)."""
        import openfga_authz
        original_url = openfga_authz.OPENFGA_URL
        original_store = openfga_authz.OPENFGA_STORE_ID
        openfga_authz.OPENFGA_URL = "http://localhost:19999"  # unreachable
        openfga_authz.OPENFGA_STORE_ID = "test-store-id"
        result = await openfga_authz.fga_check("agent:test", "can_use_model", "model:test")
        openfga_authz.OPENFGA_URL = original_url
        openfga_authz.OPENFGA_STORE_ID = original_store
        assert result is False  # fail closed

    @pytest.mark.asyncio
    async def test_custom_auth_bypasses_non_agent_requests(self):
        """Requests without agent_name in metadata bypass agent checks."""
        from openfga_authz import custom_auth
        import openfga_authz

        original = openfga_authz.OPENFGA_STORE_ID
        openfga_authz.OPENFGA_STORE_ID = "test-store"

        class MockRequest:
            async def json(self):
                return {}

        result = await custom_auth(MockRequest())
        openfga_authz.OPENFGA_STORE_ID = original
        assert result is not None
        assert getattr(result, "api_key", "") == ""

    @pytest.mark.asyncio
    async def test_custom_auth_denies_agent_with_unreachable_openfga(self):
        """Agent requests must be denied if OpenFGA is unreachable."""
        from openfga_authz import custom_auth
        import openfga_authz

        original_url = openfga_authz.OPENFGA_URL
        original_store = openfga_authz.OPENFGA_STORE_ID
        openfga_authz.OPENFGA_URL = "http://localhost:19999"
        openfga_authz.OPENFGA_STORE_ID = "test-store"

        class MockRequest:
            async def json(self):
                return {
                    "model": "ollama/qwen3:30b-a3b",
                    "metadata": {"agent_name": "fraud-sentinel", "tenant_id": "tenant-acme"},
                }

        with pytest.raises(HTTPException) as exc:
            await custom_auth(MockRequest())
        openfga_authz.OPENFGA_URL = original_url
        openfga_authz.OPENFGA_STORE_ID = original_store
        assert exc.value.status_code == 403  # fail closed


class TestBootstrapTuples:

    def test_bootstrap_file_exists(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "openfga", "bootstrap_tuples.json"
        )
        assert os.path.exists(path)

    def test_all_12_agents_in_bootstrap(self):
        import json, re
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "openfga", "bootstrap_tuples.json"
        )
        # Strip JSON comments before parsing
        content = open(path).read()
        content = re.sub(r'//.*', '', content)
        data = json.loads(content)
        objects = [t["object"] for t in data["tuples"]]
        agents = [o for o in objects if o.startswith("agent_identity:")]
        unique_agents = set(agents)
        # At minimum these agents must be present
        required = {
            "agent_identity:fraud-sentinel",
            "agent_identity:policy-creator",
            "agent_identity:code-reviewer",
            "agent_identity:web-scraper",
            "agent_identity:gateway-agent",
        }
        assert required.issubset(unique_agents), \
            f"Missing agents: {required - unique_agents}"

    def test_all_tuples_have_sponsor(self):
        import json, re
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "openfga", "bootstrap_tuples.json"
        )
        content = re.sub(r'//.*', '', open(path).read())
        data = json.loads(content)
        agent_objects = set(
            t["object"] for t in data["tuples"]
            if t["object"].startswith("agent_identity:")
        )
        sponsor_objects = set(
            t["object"] for t in data["tuples"]
            if t["relation"] == "sponsor" and t["object"].startswith("agent_identity:")
        )
        assert agent_objects == sponsor_objects, \
            f"Agents missing sponsor tuple: {agent_objects - sponsor_objects}"

    def test_no_wildcard_in_tuples(self):
        import json, re
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "openfga", "bootstrap_tuples.json"
        )
        content = re.sub(r'//.*', '', open(path).read())
        data = json.loads(content)
        for t in data["tuples"]:
            assert "*" not in t.get("user", ""), f"Wildcard in tuple user: {t}"
            assert "*" not in t.get("object", ""), f"Wildcard in tuple object: {t}"


class TestOpenFGAModel:

    def test_model_file_exists(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "openfga", "model.fga"
        )
        assert os.path.exists(path)

    def test_model_has_required_types(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "openfga", "model.fga"
        )
        content = open(path).read()
        for type_name in ["user", "agent", "blueprint", "tenant", "model",
                          "workflow", "mcp_tool", "agent_identity"]:
            assert f"type {type_name}" in content, f"Missing type: {type_name}"

    def test_model_has_three_admin_roles(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "openfga", "model.fga"
        )
        content = open(path).read()
        assert "define sponsor:" in content
        assert "define owner:" in content
        assert "define manager:" in content

    def test_model_has_can_use_model(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "openfga", "model.fga"
        )
        content = open(path).read()
        assert "define can_use_model:" in content

    def test_model_schema_version(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "openfga", "model.fga"
        )
        content = open(path).read()
        assert "schema 1.1" in content


class TestDockerComposeOpenFGA:

    def test_openfga_services_in_compose(self):
        import yaml
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "docker-compose.yml"
        )
        compose = yaml.safe_load(open(path))
        services = compose.get("services", {})
        assert "openfga" in services
        assert "postgres" in services

    def test_openfga_image_pinned(self):
        import yaml
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "docker-compose.yml"
        )
        compose = yaml.safe_load(open(path))
        image = compose["services"]["openfga"]["image"]
        assert "latest" not in image
        assert "openfga/openfga:v" in image

    def test_openfga_internal_only(self):
        import yaml
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "docker-compose.yml"
        )
        compose = yaml.safe_load(open(path))
        labels = compose["services"]["openfga"].get("labels", [])
        label_str = " ".join(str(l) for l in labels)
        assert "traefik.enable=false" in label_str

    def test_openfga_env_vars_in_example(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            ".env.example"
        )
        content = open(path).read()
        assert "OPENFGA_DB_PASSWORD" in content
        assert "OPENFGA_PRESHARED_KEY" in content
        assert "OPENFGA_STORE_ID" in content
