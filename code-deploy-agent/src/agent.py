import os
import subprocess
import re
import json
from typing import TypedDict, List, Any
from langgraph.graph import StateGraph, END
import litellm
from langfuse.model import CreateTrace
from src.constitution import get_constitutional_prompt
from src.skills.integrations.automation import N8nSkills, LangflowSkills, WebhookSkills
# (Import all other skills as they are created)

# --- Agent State ---
class AgentState(TypedDict):
    objective: str
    agent_id: str
    logger: Any
    memory: Any
    auth: Any
    langfuse: Any
    is_safe: bool
    policy_approved: bool
    execution_log: List[str]
    messages: List[Any]
    plan: str
    review_feedback: str
    policy_feedback: str
    api_spec_summary: dict

# --- Unified LLM Invocation ---
def invoke_llm_with_tracing(state: AgentState, trace_name: str, prompt: str) -> str:
    """Helper to invoke LLM via LiteLLM and trace via Langfuse."""
    langfuse = state['langfuse']
    agent_id = state['agent_id']
    
    # Create a child trace/span for this LLM call
    generation = langfuse.generation(
        name=trace_name,
        input=prompt,
        metadata={"agent_id": agent_id}
    )
    
    try:
        response = litellm.completion(
            model="fast-model", 
            messages=[{"role": "system", "content": get_constitutional_prompt()},
                     {"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        generation.end(output=content)
        return content
    except Exception as e:
        generation.end(output=str(e), level="ERROR")
        return f"Error: {str(e)}"

# --- Executor with Skill Dispatcher ---
def handle_automation_task(state: AgentState, line: str) -> bool:
    """Handles tasks related to n8n, Langflow, and generic webhooks."""
    logger = state['logger']
    
    # n8n
    n8n_match = re.search(r"trigger n8n workflow at '([^']*)'", line, re.IGNORECASE)
    if n8n_match:
        url = n8n_match.groups()[0]
        # In a real scenario, the payload would be dynamically constructed
        payload = {"message": "Hello from Code-Deploy-Agent!"}
        logger.deployment_step("N8nTrigger", "PENDING", {"url": url})
        result = N8nSkills.trigger_webhook(url, payload)
        logger.deployment_step("N8nTrigger", result['status'].upper(), result)
        return True
        
    # Langflow
    langflow_match = re.search(r"trigger langflow flow at '([^']*)'", line, re.IGNORECASE)
    if langflow_match:
        url = langflow_match.groups()[0]
        # In a real scenario, API key would come from Infisical
        api_key = state['auth'].get_secret("LANGFLOW_API_KEY", "production") or "dummy-key"
        payload = {"input": "What is the capital of France?"}
        logger.deployment_step("LangflowTrigger", "PENDING", {"url": url})
        result = LangflowSkills.trigger_flow(url, api_key, payload)
        logger.deployment_step("LangflowTrigger", result['status'].upper(), result)
        return True
        
    return False

def executor(state: AgentState):
    """
    Parses the plan and routes tasks to specialized handlers.
    """
    logger = state['logger']
    logger.audit("executor_start", {})
    
    plan_lines = state.get('plan', '').split('
')
    
    for line in plan_lines:
        if not line.strip():
            continue
            
        logger.deployment_step("ParsePlanLine", "IN_PROGRESS", {"line": line})
        
        # Route to the appropriate handler
        # This structure allows for easy expansion
        if handle_automation_task(state, line):
            continue
        # elif handle_iam_task(state, line):
        #     continue
        # elif handle_cms_task(state, line):
        #     continue
        else:
            logger.deployment_step("ParsePlanLine", "SKIPPED", {"line": line, "reason": "No handler found"})

    logger.audit("executor_end", {})
    return {} # The executor now mainly logs and calls skills, state changes happen there.


# --- LANGGRAPH NODES ---
def planner(state: AgentState):
    state['logger'].audit("planner_start", {})
    prompt = f"Objective: {state['objective']}\nCreate a step-by-step deployment plan."
    plan = invoke_llm_with_tracing(state, "Planner", prompt)
    state['logger'].audit("planner_end", {"plan": plan})
    return {"plan": plan}

def reviewer(state: AgentState):
    state['logger'].audit("reviewer_start", {})
    prompt = f"Plan: {state['plan']}\nReview this plan for safety and completeness."
    feedback = invoke_llm_with_tracing(state, "Reviewer", prompt)
    is_safe = "safe" in feedback.lower() and "error" not in feedback.lower()
    state['logger'].audit("reviewer_end", {"is_safe": is_safe, "feedback": feedback})
    return {"review_feedback": feedback, "is_safe": is_safe}
    
def policy_checker(state: AgentState):
    state['logger'].audit("policy_checker_start", {})
    # In a real scenario, this would call OPA/OpenFGA
    prompt = f"Plan: {state['plan']}\nCheck if this plan adheres to enterprise policies."
    feedback = invoke_llm_with_tracing(state, "PolicyChecker", prompt)
    approved = "approved" in feedback.lower()
    state['logger'].audit("policy_checker_end", {"approved": approved, "feedback": feedback})
    return {"policy_feedback": feedback, "policy_approved": approved}

def human_approval(state: AgentState):
    """
    Human-in-the-loop node. Pauses for user approval.
    """
    print("\n=== HUMAN IN THE LOOP APPROVAL ===")
    print(f"Plan:\n{state['plan']}")
    print(f"Review Feedback: {state['review_feedback']}")
    print(f"Policy Feedback: {state['policy_feedback']}")
    print(f"Is Safe: {state['is_safe']}, Policy Approved: {state['policy_approved']}")
    
    approval = input("\nDo you approve this deployment plan? (yes/no): ").strip().lower()
    
    if approval == 'yes':
        state['logger'].audit("human_approval", {"status": "approved"})
        return {"policy_approved": True} 
    else:
        state['logger'].audit("human_approval", {"status": "rejected"})
        print("Deployment rejected by human.")
        return {"policy_approved": False}

# --- GRAPH SETUP ---
def create_agent_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("planner", planner)
    workflow.add_node("reviewer", reviewer)
    workflow.add_node("policy_checker", policy_checker)
    workflow.add_node("human_approval", human_approval)
    workflow.add_node("executor", executor)
    
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "reviewer")
    workflow.add_edge("reviewer", "policy_checker")
    workflow.add_edge("policy_checker", "human_approval")
    
    # Conditional edge: Only execute if human approved
    def should_execute(state: AgentState):
        if state.get("policy_approved"):
            return "executor"
        return END
        
    workflow.add_conditional_edges("human_approval", should_execute)
    workflow.add_edge("executor", END)
    
    return workflow.compile()
