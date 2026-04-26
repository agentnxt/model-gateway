import os
import json

class OPA_Skills:
    @staticmethod
    def check_deployment_policy(plan_details: dict):
        """
        Generates a curl command to check a deployment plan against an OPA policy.
        
        Example OPA Policy (in Rego):
        package deployment
        
        default allow = false
        
        # Allow if no insecure docker images are used
        allow {
            not contains(input.plan.docker_image, "insecure-registry")
            input.plan.environment == "staging"
        }
        
        # Prod requires a Jira ticket
        allow {
            input.plan.environment == "production"
            startswith(input.plan.objective, "JIRA-")
        }
        """
        opa_url = os.getenv("OPA_URL", "http://localhost:8181/v1/data/deployment/allow")
        
        # The input must be wrapped in an "input" object for OPA
        input_data = json.dumps({"input": plan_details})
        
        command = f"curl -s -X POST {opa_url} -d '{input_data}'"
        return command

class OpenFGA_Skills:
    @staticmethod
    def check_permission(user: str, relation: str, resource: str):
        """
        Generates a curl command to check a user's permission against an OpenFGA store.
        
        Example OpenFGA Model:
        type user
        
        type application
          relations
            define deployer: [user]
            define can_deploy: deployer
        
        This checks if a 'user' has the 'can_deploy' relation on a specific 'application'.
        """
        fga_api_url = os.getenv("FGA_API_URL", "http://localhost:8080")
        fga_store_id = os.getenv("FGA_STORE_ID")
        
        if not fga_store_id:
            return "echo 'Error: FGA_STORE_ID is not set in .env'"

        body = {
            "tuple_key": {
                "user": user,
                "relation": relation,
                "object": resource
            }
        }
        body_json = json.dumps(body)

        command = f"curl -s -X POST {fga_api_url}/stores/{fga_store_id}/check -H 'Content-Type: application/json' -d '{body_json}'"
        return command
