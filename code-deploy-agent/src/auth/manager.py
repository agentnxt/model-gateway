import os
from infisical import InfisicalClient

class InfisicalAuthManager:
    """
    Manages secrets and credentials by fetching them from an Infisical instance.
    """
    def __init__(self, token: str = None, site: str = None):
        """
        Initializes the manager and connects to Infisical.
        Credentials can be passed directly or loaded from environment variables.
        """
        self.token = token or os.getenv("INFISICAL_TOKEN")
        self.site = site or os.getenv("INFISICAL_SITE", "https://app.infisical.com")
        
        if not self.token:
            raise ValueError("INFISICAL_TOKEN is not set. Cannot connect to Infisical.")

        self.client = InfisicalClient(token=self.token, site=self.site)
        self.secrets = {}
        print("[*] InfisicalAuthManager initialized.")

    def get_secret(self, secret_name: str, environment: str, path: str = "/"):
        """
        Retrieves a specific secret from Infisical.
        Caches secrets after the first retrieval to reduce API calls.
        """
        cache_key = f"{environment}:{path}:{secret_name}"
        if cache_key in self.secrets:
            return self.secrets[cache_key]

        try:
            secret = self.client.get_secret(
                project_id=os.getenv("INFISICAL_PROJECT_ID"), # Assumes project ID is in env
                environment=environment,
                secret_name=secret_name,
                path=path
            )
            
            if secret and secret.secret_value:
                self.secrets[cache_key] = secret.secret_value
                return secret.secret_value
            return None
        except Exception as e:
            print(f"[!] Error fetching secret '{secret_name}' from Infisical: {e}")
            return None

    def get_provider_token(self, provider_name: str):
        """
        A helper method to get a common provider token like 'VERCEL_TOKEN'.
        Assumes secrets are stored with uppercase names in the 'production' env.
        """
        secret_name = f"{provider_name.upper()}_TOKEN"
        return self.get_secret(secret_name, environment="production")
