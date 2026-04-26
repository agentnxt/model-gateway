import os
import sys
import subprocess
import uuid
from langfuse import Langfuse # Import Langfuse
from src.agent import create_agent_graph, AgentState
from src.auth.manager import InfisicalAuthManager
from src.logging.logger import DeploymentLogger
from src.memory.manager import MemoryManager

def get_available_models():
    # ... (function is unchanged)
    return []

def main():
    agent_id = f"code-deploy-agent-v1-{uuid.uuid4().hex[:8]}"
    print(f"--- Constitutional Code Deploy Agent [ID: {agent_id}] ---")
    
    # --- Core Service Initialization ---
    logger = DeploymentLogger(agent_id=agent_id)
    memory = MemoryManager()
    
    try:
        auth_manager = InfisicalAuthManager()
    except ValueError as e:
        # ... (error handling is unchanged)
        sys.exit(1)
        
    # Initialize Langfuse
    langfuse = Langfuse() # This automatically picks up credentials from .env
    
    logger.audit("session_start", {"agentId": agent_id})
    # ... (memory priming is unchanged)

    # --- Objective Input ---
    memory.sensory_memory = input("
Enter deployment objective: ")
    logger.audit("objective_received", {"objective": memory.sensory_memory})

    # --- Agent Execution ---
    agent = create_agent_graph() # Model name is now handled by LiteLLM router
    
    initial_state: AgentState = {
        "objective": memory.sensory_memory,
        "agent_id": agent_id,
        "logger": logger,
        "memory": memory,
        "auth": auth_manager,
        "langfuse": langfuse, # Pass the langfuse client into the state
        "is_safe": False,
        "policy_approved": False,
        "execution_log": [],
        "messages": [],
        "plan": "",
        "review_feedback": "",
        "policy_feedback": "",
        "api_spec_summary": {}
    }
    
    print("
[*] Starting LangGraph workflow...")
    # The initial trace for the entire session
    session_trace = langfuse.trace(name="DeploymentSession", user_id=agent_id, metadata={"objective": memory.sensory_memory})
    
    # Each node in LangGraph will create its own child trace
    final_state = agent.invoke(initial_state, {"callbacks": [session_trace.get_langchain_handler()]})
    
    print("
--- Workflow Complete ---")
    # ... (rest of the output is unchanged)

    logger.audit("session_end", {"finalStatus": "completed"})
    langfuse.flush() # Ensure all traces are sent

if __name__ == "__main__":
    main()
