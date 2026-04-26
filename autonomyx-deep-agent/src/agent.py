from typing import TypedDict, Annotated, Sequence, Union, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from .models import get_best_llm, explain_incompatibility
from .constitution import get_constitution_prompt
from .skills import get_all_skills
import operator

class AgentState(TypedDict):
    # The operator.add will append new messages to the existing list
    messages: Annotated[Sequence[BaseMessage], operator.add]

def call_model(state: AgentState):
    messages = state['messages']
    
    # 1. Selection Logic
    # Use the last human message or just the last message content
    last_human_message = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    query = last_human_message.content if last_human_message else ""
    llm = get_best_llm(query)

    if not llm:
        return {"messages": [AIMessage(content=explain_incompatibility())]}

    # 2. Constitution Enforcement
    constitution_prompt = get_constitution_prompt()
    
    # Check if we already have the system message in the state
    # If not, we might want to inject it, but for simplicity we'll just prepend it here
    # Note: Some models support system messages differently.
    system_message = AIMessage(content=f"SYSTEM INSTRUCTION: {constitution_prompt}")
    
    # Prepend system message for the LLM call (don't add to state to avoid duplication)
    full_messages = [system_message] + list(messages)
    
    # 3. Skills Integration
    skills = get_all_skills()
    if skills:
        llm_with_tools = llm.bind_tools(skills)
        response = llm_with_tools.invoke(full_messages)
    else:
        response = llm.invoke(full_messages)

    # We return a list of messages which will be added to the state
    return {"messages": [response]}

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    messages = state['messages']
    last_message = messages[-1]
    # If the LLM is asking to call a tool, we go to the "tools" node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    # Otherwise, we stop
    return END

def build_agent():
    workflow = StateGraph(AgentState)

    # Define the two nodes we will cycle between
    workflow.add_node("agent", call_model)
    
    # ToolNode automatically handles calling the tools requested by the LLM
    tools = get_all_skills()
    workflow.add_node("tools", ToolNode(tools))
    
    workflow.set_entry_point("agent")
    
    # We now add a conditional edge
    workflow.add_conditional_edges(
        "agent",
        should_continue,
    )
    
    # After tools are called, we go back to the agent to summarize or continue
    workflow.add_edge("tools", "agent")

    return workflow.compile()

agent = build_agent()
