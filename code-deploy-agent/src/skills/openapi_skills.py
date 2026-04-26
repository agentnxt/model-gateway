import yaml
import json
import requests
from typing import Dict, Any

class OpenAPISkills:
    @staticmethod
    def parse_spec(spec_path_or_url: str) -> Dict[str, Any]:
        """
        Parses an OpenAPI spec from a local file path or a URL.
        Returns a structured dictionary summarizing the spec.
        """
        try:
            if spec_path_or_url.startswith(('http://', 'https://')):
                response = requests.get(spec_path_or_url)
                response.raise_for_status()
                spec_content = response.text
            else:
                with open(spec_path_or_url, 'r') as f:
                    spec_content = f.read()

            # Try parsing as YAML, then fall back to JSON
            try:
                spec = yaml.safe_load(spec_content)
            except yaml.YAMLError:
                spec = json.loads(spec_content)
                
            # Extract key information into a summary
            summary = {
                "title": spec.get("info", {}).get("title", "N/A"),
                "version": spec.get("info", {}).get("version", "N/A"),
                "servers": [s.get("url") for s in spec.get("servers", [])],
                "paths": list(spec.get("paths", {}).keys()),
                "total_paths": len(spec.get("paths", {})),
                "schemas": list(spec.get("components", {}).get("schemas", {}).keys())
            }
            return summary

        except requests.RequestException as e:
            return {"error": f"Failed to fetch spec from URL: {e}"}
        except FileNotFoundError:
            return {"error": f"Spec file not found at: {spec_path_or_url}"}
        except Exception as e:
            return {"error": f"Failed to parse OpenAPI spec: {e}"}

