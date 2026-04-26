from typing import List, Dict, Any

class MemoryManager:
    """Implements the 9 memory types from the Autonomyx standard."""
    def __init__(self):
        # 1. Sensory Memory: The raw, immediate input.
        self.sensory_memory: str = ""

        # 2. Working Memory: The active state of the agent for the current task.
        self.working_memory: Dict[str, Any] = {}

        # 3. Short-Term Memory: A log of recent actions and events in the current session.
        self.short_term_memory: List[Dict[str, Any]] = []

        # 4. Long-Term Memory (LTM): A knowledge base of facts learned from past sessions.
        # This will store lessons from the self-improvement mechanism.
        self.long_term_memory: Dict[str, str] = {} # e.g., {"aws_s3_permission_error": "Always check IAM policy for s3:PutObject"}

        # 5. Episodic Memory: Detailed records of past deployment experiences (episodes).
        self.episodic_memory: List[Dict[str, Any]] = []

        # 6. Semantic Memory: The agent's core, static knowledge about the world.
        self.semantic_memory = {
            "constitution": None, # Loaded at runtime
            "skills": None      # Loaded at runtime
        }

        # 7. Procedural Memory: The "how-to" knowledge, embodied by the LangGraph workflow itself.
        # This is not a data store but the agent's structure.
        self.procedural_memory = "LangGraph Workflow"

        # 8. Declarative Memory: Facts about the current state of the environment.
        self.declarative_memory: Dict[str, Any] = {
            "available_llms": [],
            "loaded_credentials": []
        }

        # 9. Associative Memory: The LLM's ability to connect concepts across all memory types.
        # This is an emergent property of the underlying model.
        self.associative_memory = "LLM's internal knowledge graph and reasoning ability"

    def update_working_memory(self, state: Dict[str, Any]):
        self.working_memory = state

    def add_short_term_event(self, event: Dict[str, Any]):
        self.short_term_memory.append(event)
    
    def get_context_for_planner(self) -> str:
        """Constructs a context string from memory to aid the planner."""
        context = ""
        if self.long_term_memory:
            context += "--- Relevant Lessons from Long-Term Memory ---
"
            # In a real system, you'd use embeddings to find relevant lessons.
            # Here, we'll just show a few.
            for key, val in list(self.long_term_memory.items())[:3]:
                context += f"- If you encounter '{key}', remember: '{val}'
"
        
        # Add details from declarative memory
        context += "
--- Current Environment ---
"
        context += f"Available LLMs: {', '.join(self.declarative_memory['available_llms'])}
"
        context += f"Authenticated Services: {', '.join(self.declarative_memory['loaded_credentials'])}
"
        
        return context
