"""
tests/test_recommender.py
Unit tests for the model recommender router.
"""

import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestModelScoring:
    """Test model scoring logic directly."""

    def test_local_models_score_higher_than_cloud(self):
        from recommender import score_models
        scored = score_models("chat", require_local=False)
        local = [m for m in scored if m["local"]]
        cloud = [m for m in scored if not m["local"]]
        if local and cloud:
            # Best local should beat best cloud for basic chat
            assert local[0]["fit_score"] >= cloud[0]["fit_score"]

    def test_code_task_routes_to_coder_model(self):
        from recommender import score_models
        scored = score_models("code", require_local=True)
        assert len(scored) > 0
        assert "coder" in scored[0]["alias"].lower() or "code" in scored[0]["alias"].lower()

    def test_require_local_filters_cloud(self):
        from recommender import score_models
        scored = score_models("chat", require_local=True)
        assert all(m["local"] for m in scored)

    def test_all_tasks_return_results(self):
        from recommender import score_models
        tasks = ["chat", "code", "reason", "summarise", "extract", "vision", "agent"]
        for task in tasks:
            scored = score_models(task, require_local=False)
            assert len(scored) > 0, f"No models for task: {task}"

    def test_fit_score_bounded(self):
        from recommender import score_models
        scored = score_models("chat", require_local=False)
        for m in scored:
            assert 0 <= m["fit_score"] <= 110, f"Score out of range: {m}"

    def test_always_on_models_present(self):
        from recommender import score_models, MODEL_CATALOGUE
        always_on = [m for m in MODEL_CATALOGUE if m.get("always_on")]
        assert len(always_on) >= 3, "Expected at least 3 always-on models"

    def test_sorted_descending(self):
        from recommender import score_models
        scored = score_models("reason", require_local=False)
        scores = [m["fit_score"] for m in scored]
        assert scores == sorted(scores, reverse=True)


class TestRecommendEndpoint:
    """Test the FastAPI endpoint."""

    def test_endpoint_exists(self):
        from recommender import router
        routes = [r.path for r in router.routes]
        assert "/recommend" in routes

    def test_request_model_fields(self):
        from recommender import RecommendRequest
        req = RecommendRequest(prompt="write python code", top_n=3)
        assert req.prompt == "write python code"
        assert req.top_n == 3
        assert req.require_local is False

    def test_response_model_fields(self):
        from recommender import RecommendResponse
        resp = RecommendResponse(
            task_type="code",
            task_confidence=0.92,
            below_threshold=False,
            recommendations=[{"alias": "ollama/qwen2.5-coder:32b", "fit_score": 100}],
        )
        assert resp.task_type == "code"
        assert resp.task_confidence == 0.92
