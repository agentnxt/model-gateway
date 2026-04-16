"""
tests/test_config.py
Validate config.yaml and docker-compose.yml structure.
No external dependencies — just file parsing.
"""

import pytest
import yaml
import os

ROOT = os.path.dirname(os.path.dirname(__file__))


class TestConfigYaml:

    def setup_method(self):
        with open(os.path.join(ROOT, "config.yaml")) as f:
            self.config = yaml.safe_load(f)

    def test_model_list_exists(self):
        assert "model_list" in self.config
        assert len(self.config["model_list"]) > 0

    def test_all_models_have_required_fields(self):
        for model in self.config["model_list"]:
            assert "model_name" in model, f"Missing model_name: {model}"
            assert "litellm_params" in model, f"Missing litellm_params: {model}"
            assert "model" in model["litellm_params"], f"Missing model in litellm_params: {model}"

    def test_local_ollama_models_present(self):
        aliases = [m["model_name"] for m in self.config["model_list"]]
        assert any("qwen3" in a for a in aliases), "Qwen3-30B-A3B missing"
        assert any("coder" in a for a in aliases), "Qwen2.5-Coder missing"
        assert any("qwen2.5:14b" in a or "qwen2.5-14b" in a.lower() for a in aliases), "Qwen2.5-14B missing"

    def test_cloud_fallback_models_present(self):
        aliases = [m["model_name"] for m in self.config["model_list"]]
        assert any("groq" in a for a in aliases), "Groq fallback missing"

    def test_no_hardcoded_api_keys(self):
        """API keys must use os.environ/ references, never hardcoded."""
        for model in self.config["model_list"]:
            params = model.get("litellm_params", {})
            api_key = params.get("api_key", "")
            if api_key:
                assert api_key.startswith("os.environ/"), \
                    f"Hardcoded API key in {model['model_name']}: {api_key}"

    def test_router_settings_present(self):
        assert "router_settings" in self.config
        rs = self.config["router_settings"]
        assert rs.get("routing_strategy") == "usage-based-routing"
        assert "fallbacks" in rs
        assert len(rs["fallbacks"]) > 0

    def test_litellm_settings_present(self):
        assert "litellm_settings" in self.config

    def test_general_settings_has_master_key(self):
        gs = self.config.get("general_settings", {})
        assert gs.get("master_key") == "os.environ/LITELLM_MASTER_KEY"

    def test_vertex_models_have_project(self):
        vertex_models = [
            m for m in self.config["model_list"]
            if "vertex" in m["model_name"]
        ]
        for m in vertex_models:
            params = m["litellm_params"]
            assert "vertex_project" in params, f"Missing vertex_project: {m['model_name']}"

    def test_no_nllb_or_seamless(self):
        """NLLB and SeamlessM4T are CC-BY-NC — must never appear."""
        config_str = yaml.dump(self.config).lower()
        assert "nllb" not in config_str, "NLLB-200 (CC-BY-NC) detected in config"
        assert "seamless" not in config_str, "SeamlessM4T (CC-BY-NC) detected in config"


class TestDockerCompose:

    def setup_method(self):
        with open(os.path.join(ROOT, "docker-compose.yml")) as f:
            self.compose = yaml.safe_load(f)

    def test_required_services_present(self):
        services = self.compose.get("services", {})
        required = ["litellm", "litellm-db", "ollama", "prometheus", "grafana", "langflow"]
        for svc in required:
            assert svc in services, f"Required service missing: {svc}"

    def test_all_services_have_container_names(self):
        services = self.compose.get("services", {})
        for name, svc in services.items():
            assert "container_name" in svc, f"Missing container_name: {name}"

    def test_all_services_have_restart_policy(self):
        services = self.compose.get("services", {})
        for name, svc in services.items():
            assert "restart" in svc, f"Missing restart policy: {name}"

    def test_litellm_has_traefik_labels(self):
        litellm = self.compose["services"]["litellm"]
        labels = litellm.get("labels", [])
        label_str = " ".join(str(l) for l in labels)
        assert "llm.openautonomyx.com" in label_str

    def test_no_version_attribute(self):
        """version attribute is obsolete — should not be present."""
        assert "version" not in self.compose, \
            "Remove 'version:' attribute — it is obsolete in Docker Compose v2+"

    def test_coolify_network_external(self):
        networks = self.compose.get("networks", {})
        assert "coolify" in networks
        assert networks["coolify"].get("external") is True

    def test_volumes_defined(self):
        volumes = self.compose.get("volumes", {})
        assert "ollama-data" in volumes
        assert "litellm-db-data" in volumes
        assert "langflow-data" in volumes


class TestEnvExample:

    def test_env_example_exists(self):
        path = os.path.join(ROOT, ".env.example")
        assert os.path.exists(path), ".env.example missing"

    def test_required_vars_present(self):
        path = os.path.join(ROOT, ".env.example")
        with open(path) as f:
            content = f.read()
        required = [
            "LITELLM_MASTER_KEY",
            "POSTGRES_PASSWORD",
            "GROQ_API_KEY",
            "LANGFLOW_SECRET_KEY",
            "VERTEX_PROJECT",
        ]
        for var in required:
            assert var in content, f"Required var missing from .env.example: {var}"

    def test_no_real_secrets_in_example(self):
        """Ensure .env.example never contains real secrets."""
        path = os.path.join(ROOT, ".env.example")
        with open(path) as f:
            content = f.read()
        # Should never contain real-looking keys
        assert "sk-" not in content or "YOUR" in content, \
            "Possible real API key in .env.example"
