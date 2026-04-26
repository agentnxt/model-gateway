import os
from typing import Optional, Any
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

class ModelSelection(BaseModel):
    model_name: str
    provider: str
    is_compatible: bool
    explanation: Optional[str] = None

def get_best_llm(task_description: str) -> Any:
    """
    Chooses the best available LLM for a particular task.
    Prioritizes the Autonomyx Gateway (LiteLLM proxy).
    """
    gateway_url = os.getenv("GATEWAY_URL", "https://llm.openautonomyx.com")
    master_key = os.getenv("LITELLM_MASTER_KEY")
    
    # Priority 0: Autonomyx Gateway
    if master_key:
        try:
            # We use ChatOpenAI because the gateway is OpenAI-compatible
            return ChatOpenAI(
                model="ollama/qwen3:30b-a3b", # Default powerful local model
                base_url=f"{gateway_url}/v1",
                api_key=master_key,
                timeout=30
            )
        except Exception:
            pass

    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    google_api_key = os.getenv("GOOGLE_API_KEY")

    # Fallback to direct providers
    if anthropic_api_key:
        try:
            return ChatAnthropic(model="claude-3-5-sonnet-20240620", anthropic_api_key=anthropic_api_key)
        except Exception:
            pass
            
    if openai_api_key:
        try:
            return ChatOpenAI(model="gpt-4o", api_key=openai_api_key)
        except Exception:
            pass

    if google_api_key:
        try:
            return ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=google_api_key)
        except Exception:
            pass

    return None

def explain_incompatibility():
    return """
I am sorry, but I cannot process your request at this time.
No compatible Large Language Models (LLMs) are currently configured or available.
Please ensure that at least one of the following environment variables is set:
- LITELLM_MASTER_KEY (for Autonomyx Gateway)
- ANTHROPIC_API_KEY
- OPENAI_API_KEY
- GOOGLE_API_KEY
"""
