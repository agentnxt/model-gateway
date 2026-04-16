"""
lago_callback.py — LiteLLM custom success callback
Fires usage events to Lago per completed LLM request.
Maps LiteLLM virtual key alias → Lago external_customer_id.

Lago billable metrics required (create in Lago UI before first use):
  - llm_input_tokens  (SUM aggregation, field: input_tokens)
  - llm_output_tokens (SUM aggregation, field: output_tokens)
  - llm_requests      (COUNT aggregation)
"""

import os, time, httpx
from litellm.integrations.custom_logger import CustomLogger

LAGO_API_URL = os.environ.get("LAGO_API_URL", "https://billing.openautonomyx.com")
LAGO_API_KEY = os.environ.get("LAGO_API_KEY", "")


class LagoCallback(CustomLogger):

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            usage        = response_obj.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            model        = kwargs.get("model", "unknown")
            key_alias    = kwargs.get("litellm_params", {}).get("metadata", {}).get("user_api_key_alias", "default")

            # LiteLLM key alias → Lago external_customer_id
            # Convention: key_alias matches Keycloak group name (e.g. "tenant-acme")
            external_id = key_alias or "default"
            timestamp   = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            txn_id      = f"{external_id}-{int(time.time())}"

            events = [
                {
                    "transaction_id":    f"{txn_id}-input",
                    "external_customer_id": external_id,
                    "code":              "llm_input_tokens",
                    "timestamp":         timestamp,
                    "properties":        {"input_tokens": input_tokens, "model": model},
                },
                {
                    "transaction_id":    f"{txn_id}-output",
                    "external_customer_id": external_id,
                    "code":              "llm_output_tokens",
                    "timestamp":         timestamp,
                    "properties":        {"output_tokens": output_tokens, "model": model},
                },
                {
                    "transaction_id":    f"{txn_id}-req",
                    "external_customer_id": external_id,
                    "code":              "llm_requests",
                    "timestamp":         timestamp,
                    "properties":        {"model": model},
                },
            ]

            with httpx.Client(timeout=5) as client:
                for event in events:
                    client.post(
                        f"{LAGO_API_URL}/api/v1/events",
                        headers={
                            "Authorization": f"Bearer {LAGO_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={"event": event},
                    )

        except Exception as e:
            print(f"[LagoCallback] Error: {e}")

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        try:
            usage         = response_obj.get("usage", {})
            input_tokens  = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            model         = kwargs.get("model", "unknown")
            key_alias     = kwargs.get("litellm_params", {}).get("metadata", {}).get("user_api_key_alias", "default")
            external_id   = key_alias or "default"
            timestamp     = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            txn_id        = f"{external_id}-{int(time.time())}"

            events = [
                {"transaction_id": f"{txn_id}-input",  "external_customer_id": external_id, "code": "llm_input_tokens",  "timestamp": timestamp, "properties": {"input_tokens": input_tokens, "model": model}},
                {"transaction_id": f"{txn_id}-output", "external_customer_id": external_id, "code": "llm_output_tokens", "timestamp": timestamp, "properties": {"output_tokens": output_tokens, "model": model}},
                {"transaction_id": f"{txn_id}-req",    "external_customer_id": external_id, "code": "llm_requests",      "timestamp": timestamp, "properties": {"model": model}},
            ]

            async with httpx.AsyncClient(timeout=5) as client:
                for event in events:
                    await client.post(
                        f"{LAGO_API_URL}/api/v1/events",
                        headers={"Authorization": f"Bearer {LAGO_API_KEY}", "Content-Type": "application/json"},
                        json={"event": event},
                    )

        except Exception as e:
            print(f"[LagoCallback] Async error: {e}")
