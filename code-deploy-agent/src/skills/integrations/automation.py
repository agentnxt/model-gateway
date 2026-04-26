import requests
import json

class WebhookSkills:
    @staticmethod
    def send_webhook(url: str, method: str, headers: dict = None, payload: dict = None) -> dict:
        """
        Sends a generic webhook and returns the JSON response or an error.
        
        :param url: The target URL for the webhook.
        :param method: HTTP method (e.g., 'POST', 'GET', 'PUT').
        :param headers: Optional dictionary of request headers.
        :param payload: Optional dictionary of the JSON payload for POST/PUT requests.
        :return: A dictionary containing the response or an error message.
        """
        try:
            if headers is None:
                headers = {'Content-Type': 'application/json'}

            response = requests.request(
                method.upper(),
                url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            
            # Try to parse JSON, fall back to raw text if it fails
            try:
                return {"status": "success", "statusCode": response.status_code, "data": response.json()}
            except json.JSONDecodeError:
                return {"status": "success", "statusCode": response.status_code, "data": response.text}

        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

class N8nSkills:
    @staticmethod
    def trigger_webhook(webhook_url: str, payload: dict):
        """Triggers a specific n8n webhook workflow."""
        return WebhookSkills.send_webhook(url=webhook_url, method="POST", payload=payload)

class LangflowSkills:
    @staticmethod
    def trigger_flow(flow_url: str, api_key: str, payload: dict):
        """Triggers a Langflow API endpoint."""
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key
        }
        return WebhookSkills.send_webhook(url=flow_url, method="POST", headers=headers, payload=payload)
