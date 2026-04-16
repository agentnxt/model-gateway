"""
recommender.py — Model recommender FastAPI router
Mounted on LiteLLM via general_settings.additional_routers.
Exposes POST /recommend endpoint.

Calls local classifier sidecar (port 8100) for task type detection.
Reads budget state from LiteLLM Postgres.
Returns ranked model list with fit scores.
"""

import os, httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

CLASSIFIER_URL  = os.environ.get("CLASSIFIER_URL", "http://classifier:8100")
LITELLM_DB_URL  = os.environ.get("DATABASE_URL", "")
RECOMMENDER_MODE = os.environ.get("RECOMMENDER_MODE", "local")  # local | cloud

# Model catalogue — task affinities and cost
MODEL_CATALOGUE = [
    {"alias": "ollama/qwen3:30b-a3b",      "tasks": ["reason","agent","chat","policy","analysis"], "cost_per_1k": 0.0,   "local": True,  "always_on": True},
    {"alias": "ollama/qwen2.5-coder:32b",  "tasks": ["code"],                                     "cost_per_1k": 0.0,   "local": True,  "always_on": True},
    {"alias": "ollama/qwen2.5:14b",        "tasks": ["extract","summarise"],                       "cost_per_1k": 0.0,   "local": True,  "always_on": True},
    {"alias": "ollama/llama3.2-vision:11b","tasks": ["vision"],                                    "cost_per_1k": 0.0,   "local": True,  "always_on": False},
    {"alias": "ollama/llama3.1:8b",        "tasks": ["chat"],                                      "cost_per_1k": 0.0,   "local": True,  "always_on": False},
    {"alias": "ollama/gemma3:9b",          "tasks": ["long_context"],                              "cost_per_1k": 0.0,   "local": True,  "always_on": False},
    {"alias": "groq/llama3-70b",           "tasks": ["reason","chat","agent"],                     "cost_per_1k": 0.59,  "local": False, "always_on": False},
    {"alias": "vertex/gemini-2.5-pro",     "tasks": ["reason","long_context","vision"],            "cost_per_1k": 1.25,  "local": False, "always_on": False},
    {"alias": "vertex/gemini-2.5-flash",   "tasks": ["chat","extract","summarise"],                "cost_per_1k": 0.15,  "local": False, "always_on": False},
    {"alias": "vertex/claude-3-5-sonnet",  "tasks": ["reason","policy","analysis"],                "cost_per_1k": 3.0,   "local": False, "always_on": False},
    {"alias": "gpt-4o",                    "tasks": ["reason","vision","agent"],                   "cost_per_1k": 5.0,   "local": False, "always_on": False},
    {"alias": "claude-3-5-sonnet",         "tasks": ["reason","policy","analysis"],                "cost_per_1k": 3.0,   "local": False, "always_on": False},
]


class RecommendRequest(BaseModel):
    prompt: str
    virtual_key: Optional[str] = None
    top_n: int = 3
    require_local: bool = False


class RecommendResponse(BaseModel):
    task_type: str
    task_confidence: float
    below_threshold: bool
    recommendations: list
    budget_state: Optional[dict] = None


async def classify_task(prompt: str) -> dict:
    """Call local classifier sidecar."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(
                f"{CLASSIFIER_URL}/classify",
                json={"text": prompt[:2000], "top_n": 3},
            )
            return r.json()
    except Exception:
        return {"task": "chat", "confidence": 0.5, "below_threshold": True}


def score_models(task: str, require_local: bool) -> list:
    """Score models for a given task type."""
    scored = []
    for model in MODEL_CATALOGUE:
        if require_local and not model["local"]:
            continue
        # Task fit score
        fit = 100 if task in model["tasks"] else 20
        # Boost always-on local models
        if model["local"] and model["always_on"]:
            fit += 10
        # Cost penalty for cloud
        cost_penalty = min(model["cost_per_1k"] * 5, 30)
        final_score = max(0, fit - cost_penalty)

        scored.append({
            "alias":        model["alias"],
            "fit_score":    round(final_score),
            "local":        model["local"],
            "always_on":    model["always_on"],
            "cost_per_1k":  model["cost_per_1k"],
            "reason":       f"{'Always-on local' if model['local'] and model['always_on'] else 'Cloud fallback'} — optimised for {', '.join(model['tasks'][:2])}",
        })

    return sorted(scored, key=lambda x: x["fit_score"], reverse=True)


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(
    req: RecommendRequest,
    authorization: Optional[str] = Header(None),
):
    # Classify task
    classification = await classify_task(req.prompt)
    task       = classification.get("task", "chat")
    confidence = classification.get("confidence", 0.5)
    below_threshold = classification.get("below_threshold", False)

    # Score models
    scored = score_models(task, req.require_local)
    top_n  = scored[:req.top_n]

    return RecommendResponse(
        task_type=task,
        task_confidence=confidence,
        below_threshold=below_threshold,
        recommendations=top_n,
        budget_state=None,  # extend: query LiteLLM /key/info for budget state
    )
