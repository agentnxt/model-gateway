"""
tests/test_feedback.py
Unit tests for the feedback capture router.
"""

import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


class TestFeedbackRouter:

    def test_endpoint_exists(self):
        from feedback import router
        routes = [r.path for r in router.routes]
        assert "/feedback" in routes

    def test_request_model_valid_score(self):
        from feedback import FeedbackRequest
        req = FeedbackRequest(trace_id="abc123", score=1, virtual_key="sk-test")
        assert req.score == 1
        assert req.trace_id == "abc123"

    def test_request_model_bad_score_zero(self):
        from feedback import FeedbackRequest
        req = FeedbackRequest(trace_id="abc123", score=0)
        assert req.score == 0

    def test_request_model_defaults(self):
        from feedback import FeedbackRequest
        req = FeedbackRequest(trace_id="abc123", score=1)
        assert req.comment == ""
        assert req.source == "api"
        assert req.virtual_key is None

    def test_response_model(self):
        from feedback import FeedbackResponse
        resp = FeedbackResponse(
            status="received",
            trace_id="abc123",
            score=1,
            langfuse_score_id="score-xyz",
        )
        assert resp.status == "received"
        assert resp.langfuse_score_id == "score-xyz"

    def test_response_model_optional_score_id(self):
        from feedback import FeedbackResponse
        resp = FeedbackResponse(status="received", trace_id="abc", score=0)
        assert resp.langfuse_score_id is None
