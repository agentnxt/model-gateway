import os
import json
import yaml
import httpx
from typing import List, Any, Optional
from langchain.tools import BaseTool, Tool
from langchain_mcp_adapters.tools import load_mcp_tools
from pydantic import Field

# Load credentials from environment
LITELLM_MASTER_KEY = os.getenv("LITELLM_MASTER_KEY", "")
GATEWAY_URL = os.getenv("GATEWAY_URL", "https://llm.openautonomyx.com")
IDENTITY_API_URL = os.getenv("IDENTITY_API_URL", "https://id.unboxd.cloud")

class DiscoveryTool(BaseTool):
    name: str = "agent_discovery"
    description: str = "Discover available agents and capabilities in the Autonomyx platform."

    def _run(self, query: str = None):
        try:
            r = httpx.get(f"{GATEWAY_URL}/.well-known/agent-configuration", timeout=10)
            if r.status_code == 200:
                return json.dumps(r.json(), indent=2)
            return f"Error: Status code {r.status_code}"
        except Exception as e:
            return f"Error connecting to discovery endpoint: {e}"

class IdentityTool(BaseTool):
    name: str = "agent_identity"
    description: str = "Manage agent identities (create, list, suspend, rotate). Query requires agent_id or action."

    def _run(self, action: str, agent_name: Optional[str] = None, tenant_id: Optional[str] = None):
        headers = {"Authorization": f"Bearer {LITELLM_MASTER_KEY}"}
        try:
            if action == "list":
                r = httpx.get(f"{IDENTITY_API_URL}/agents", headers=headers, timeout=10)
            elif action == "create" and agent_name and tenant_id:
                r = httpx.post(f"{IDENTITY_API_URL}/agents/create", headers=headers, json={
                    "agent_name": agent_name,
                    "tenant_id": tenant_id,
                    "sponsor_id": "admin@openautonomyx.com"
                }, timeout=10)
            else:
                return "Invalid action or missing parameters for agent_identity tool."
            
            if r.status_code in [200, 201]:
                return json.dumps(r.json(), indent=2)
            return f"Error: Status code {r.status_code} - {r.text}"
        except Exception as e:
            return f"Error connecting to identity API: {e}"

class RecommenderTool(BaseTool):
    name: str = "model_recommender"
    description: str = "Get the best model recommendation for a specific task prompt."

    def _run(self, prompt: str):
        headers = {"Authorization": f"Bearer {LITELLM_MASTER_KEY}"}
        try:
            r = httpx.post(f"{GATEWAY_URL}/recommend", headers=headers, json={
                "prompt": prompt,
                "top_n": 1
            }, timeout=10)
            if r.status_code == 200:
                return json.dumps(r.json(), indent=2)
            return f"Error: Status code {r.status_code}"
        except Exception as e:
            return f"Error connecting to recommender: {e}"

def get_autonomyx_skills() -> List[BaseTool]:
    return [DiscoveryTool(), IdentityTool(), RecommenderTool()]

def load_claude_skills() -> List[Tool]:
    """
    Loads all Claude skills from the .agents/skills directory.
    Each skill is a directory containing a SKILL.md file.
    """
    skills_dir = os.path.join(os.path.expanduser("~"), ".agents/skills")
    if not os.path.isdir(skills_dir):
        return []

    claude_skills = []
    for skill_name in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, skill_name)
        skill_md_path = os.path.join(skill_path, "SKILL.md")
        
        if os.path.isdir(skill_path) and os.path.exists(skill_md_path):
            try:
                with open(skill_md_path, "r") as f:
                    content = f.read()
                    # Parse YAML frontmatter for description
                    parts = content.split("---")
                    description = "No description available."
                    if len(parts) > 2:
                        frontmatter = yaml.safe_load(parts[1])
                        description = frontmatter.get("description", description)
                    
                    # Create a tool that returns the full SKILL.md content
                    # This allows the agent to 'read' the instructions for the skill
                    skill_tool = Tool(
                        name=f"skill_{skill_name.replace('-', '_')}",
                        func=lambda q, c=content: c,
                        description=f"Instructions for {skill_name}: {description}"
                    )
                    claude_skills.append(skill_tool)
            except Exception as e:
                print(f"Error loading skill '{skill_name}': {e}")
                
    return claude_skills


def get_anthropic_mcp_tools() -> List[Any]:
    """
    Loads MCP tools from .mcp.json if available.
    """
    search_paths = [
        os.path.join(os.getcwd(), ".mcp.json"),
        os.path.join(os.path.expanduser("~"), ".mcp.json")
    ]
    
    mcp_config_path = None
    for path in search_paths:
        if os.path.exists(path):
            mcp_config_path = path
            break
        
    if mcp_config_path:
        try:
            with open(mcp_config_path, "r") as f:
                config = json.load(f)
            
            all_mcp_tools = []
            for name, server_config in config.get("mcpServers", {}).items():
                if server_config.get("type") == "http":
                    url = server_config.get("url")
                    try:
                        tools = load_mcp_tools(url)
                        all_mcp_tools.extend(tools)
                    except Exception:
                        continue
            return all_mcp_tools
        except Exception as e:
            return []
    return []

def get_all_skills() -> List[Any]:
    skills = []
    skills.extend(get_autonomyx_skills())
    # skills.extend(get_anthropic_mcp_tools()) # Disable for now to avoid load errors
    skills.extend(load_claude_skills())
    return skills
