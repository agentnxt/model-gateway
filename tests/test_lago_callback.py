"""
tests/test_lago_callback.py
Unit tests for the Lago billing callback.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch


def make_response_obj(input_tokens=100, output_tokens=50):
    return {
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
        }
    }


def make_kwargs(key_alias="tenant-acme", model="ollama/qwen3:30b-a3b"):
    return {
        "model": model,
        "litellm_params": {
            "metadata": {
                "user_api_key_alias": key_alias,
            }
        }
    }


class TestLagoCallbackInit:
    def test_import(self):
        """LagoCallback can be imported without errors."""
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from lago_callback import LagoCallback
        cb = LagoCallback()
        assert cb is not None

    def test_inherits_custom_logger(self):
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from lago_callback import LagoCallback
        from litellm.integrations.custom_logger import CustomLogger
        assert issubclass(LagoCallback, CustomLogger)


class TestLagoCallbackEventBuilding:
    """Test that events are built correctly from kwargs."""

    def setup_method(self):
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    @patch("lago_callback.LAGO_API_KEY", "test-key")
    @patch("lago_callback.LAGO_API_URL", "http://lago.test")
    @patch("httpx.Client")
    def test_fires_three_events(self, mock_client):
        """Should fire exactly 3 events per LLM call."""
        from lago_callback import LagoCallback

        post_calls = []
        mock_post = MagicMock()
        mock_post.return_value = MagicMock(status_code=200)
        mock_client.return_value.__enter__ = MagicMock(return_value=MagicMock(post=mock_post))
        mock_client.return_value.__exit__ = MagicMock(return_value=False)

        cb = LagoCallback()
        cb.log_success_event(
            kwargs=make_kwargs(),
            response_obj=make_response_obj(),
            start_time=0,
            end_time=1,
        )

        assert mock_post.call_count == 3

    @patch("lago_callback.LAGO_API_KEY", "test-key")
    @patch("lago_callback.LAGO_API_URL", "http://lago.test")
    @patch("httpx.Client")
    def test_event_codes(self, mock_client):
        """Events should have correct Lago metric codes."""
        from lago_callback import LagoCallback

        captured = []
        def capture_post(url, **kwargs):
            captured.append(kwargs.get("json", {}).get("event", {}).get("code"))
            return MagicMock(status_code=200)

        mock_client.return_value.__enter__ = MagicMock(
            return_value=MagicMock(post=capture_post)
        )
        mock_client.return_value.__exit__ = MagicMock(return_value=False)

        cb = LagoCallback()
        cb.log_success_event(
            kwargs=make_kwargs(),
            response_obj=make_response_obj(100, 50),
            start_time=0, end_time=1,
        )

        assert "llm_input_tokens" in captured
        assert "llm_output_tokens" in captured
        assert "llm_requests" in captured

    @patch("lago_callback.LAGO_API_KEY", "test-key")
    @patch("lago_callback.LAGO_API_URL", "http://lago.test")
    @patch("httpx.Client")
    def test_external_customer_id_from_key_alias(self, mock_client):
        """external_customer_id should match the virtual key alias."""
        from lago_callback import LagoCallback

        captured_ids = []
        def capture_post(url, **kwargs):
            event = kwargs.get("json", {}).get("event", {})
            captured_ids.append(event.get("external_customer_id"))
            return MagicMock(status_code=200)

        mock_client.return_value.__enter__ = MagicMock(
            return_value=MagicMock(post=capture_post)
        )
        mock_client.return_value.__exit__ = MagicMock(return_value=False)

        cb = LagoCallback()
        cb.log_success_event(
            kwargs=make_kwargs(key_alias="tenant-acme"),
            response_obj=make_response_obj(),
            start_time=0, end_time=1,
        )

        assert all(cid == "tenant-acme" for cid in captured_ids)

    @patch("lago_callback.LAGO_API_KEY", "test-key")
    @patch("lago_callback.LAGO_API_URL", "http://lago.test")
    @patch("httpx.Client")
    def test_fallback_to_default_when_no_alias(self, mock_client):
        """Should use 'default' when key alias is missing."""
        from lago_callback import LagoCallback

        captured_ids = []
        def capture_post(url, **kwargs):
            event = kwargs.get("json", {}).get("event", {})
            captured_ids.append(event.get("external_customer_id"))
            return MagicMock(status_code=200)

        mock_client.return_value.__enter__ = MagicMock(
            return_value=MagicMock(post=capture_post)
        )
        mock_client.return_value.__exit__ = MagicMock(return_value=False)

        cb = LagoCallback()
        cb.log_success_event(
            kwargs={"model": "test", "litellm_params": {"metadata": {}}},
            response_obj=make_response_obj(),
            start_time=0, end_time=1,
        )

        assert all(cid == "default" for cid in captured_ids)

    @patch("lago_callback.LAGO_API_KEY", "test-key")
    @patch("lago_callback.LAGO_API_URL", "http://lago.test")
    @patch("httpx.Client")
    def test_does_not_raise_on_http_error(self, mock_client):
        """Callback should swallow errors — never crash LiteLLM."""
        from lago_callback import LagoCallback

        mock_client.return_value.__enter__ = MagicMock(
            return_value=MagicMock(post=MagicMock(side_effect=Exception("network error")))
        )
        mock_client.return_value.__exit__ = MagicMock(return_value=False)

        cb = LagoCallback()
        # Should not raise
        cb.log_success_event(
            kwargs=make_kwargs(),
            response_obj=make_response_obj(),
            start_time=0, end_time=1,
        )
