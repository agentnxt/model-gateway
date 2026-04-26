# Autonomyx Deep Agent

**Deep Agent** is an advanced orchestration backend based on LangGraph, designed to serve as a central intelligence layer for the Autonomyx platform.

## Key Features

- **Multi-Model Routing**: Prioritizes the Autonomyx LLM Gateway (LiteLLM) with local Qwen3 models, falling back to Claude, GPT, or Gemini as needed.
- **Constitutional AI**: Every response is filtered through a predefined constitution (helpful, honest, harmless) managed via `constitution.py`.
- **Integrated Skills**:
  - **Agent Discovery**: Dynamically discovers platform capabilities via the `.well-known` configuration.
  - **Agent Identity**: Manages lifecycle of other specialized agents (Fraud Sentinel, Policy Creator, etc.).
  - **Model Recommendation**: Uses the platform's recommender service to select the best model per task.
  - **Claude Skills**: Direct integration with instructions from `~/.agents/skills`.
- **LangGraph Loop**: Full tool execution cycle using `ToolNode` and conditional edges for autonomous multi-step reasoning.
- **FastAPI Interface**: Clean REST API for chat and health monitoring.

## Project Structure

```
autonomyx-deep-agent/
├── src/
│   ├── agent.py        # LangGraph workflow definition
│   ├── skills.py       # Tool/Skill integration logic
│   ├── models.py       # LLM provider and routing logic
│   ├── constitution.py # Behavior principles
│   └── main.py         # FastAPI entry point
├── .env                # Local secrets (Gateway + Keys)
├── pyproject.toml      # Dependencies
└── GEMINI.md           # This project record
```

## Setup & Execution

1.  **Environment**: Ensure `LITELLM_MASTER_KEY` is set in `.env`.
2.  **Install**: `pip install -e .`
3.  **Run**: `python src/main.py`
4.  **Test**: `curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "What agents are available?"}'`

## Progress Record (2026-04-25)

- [x] Initial codebase audit.
- [x] Refactored `agent.py` to support full LangGraph tool loop.
- [x] Implemented `DiscoveryTool`, `IdentityTool`, and `RecommenderTool` in `skills.py`.
- [x] Enhanced Claude skill loading to support instruction-based reasoning.
- [x] Configured `models.py` to prioritize Autonomyx Gateway with Qwen3.
- [x] Created `GEMINI.md` for project tracking.
