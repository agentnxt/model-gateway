"""
feedback.py — Human feedback capture FastAPI router
Mounted on LiteLLM via general_settings.additional_routers.
Exposes POST /feedback endpoint.

Routes feedback scores to the correct Langfuse tenant project
via the virtual key → tenant mapping.
"""

import os, time, httpx
from fastapi import APIRouter, Header
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

LANGFUSE_HOST       = os.environ.get("LANGFUSE_HOST", "https://traces.openautonomyx.com")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
LITELLM_MASTER_KEY  = os.environ.get("LITELLM_MASTER_KEY", "")
LITELLM_URL         = os.environ.get("LITELLM_URL", "http://localhost:4000")


class FeedbackRequest(BaseModel):
    trace_id:    str           # response.id from LLM call
    score:       int           # 1 = good, 0 = bad
    virtual_key: Optional[str] = None
    comment:     Optional[str] = ""
    source:      Optional[str] = "api"   # api | widget | langflow | agent


class FeedbackResponse(BaseModel):
    status:          str
    trace_id:        str
    score:           int
    langfuse_score_id: Optional[str] = None


async def get_langfuse_keys(virtual_key: str) -> tuple[str, str]:
    """
    Look up Langfuse project keys for a virtual key alias.
    In production: query a mapping table in Postgres or Keycloak group attributes.
    For now: use master Langfuse keys (all traces go to same project, separated by tag).
    """
    # TODO: per-tenant Langfuse keys when multi-tenant Langfuse orgs are provisioned
    public_key  = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key  = os.environ.get("LANGFUSE_SECRET_KEY", "")
    return public_key, secret_key


@router.post("/feedback", response_model=FeedbackResponse)
async def capture_feedback(
    req: FeedbackRequest,
    authorization: Optional[str] = Header(None),
):
    langfuse_score_id = None

    try:
        public_key, secret_key = await get_langfuse_keys(req.virtual_key or "default")

        if public_key and secret_key:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"{LANGFUSE_HOST}/api/public/scores",
                    auth=(public_key, secret_key),
                    json={
                        "traceId": req.trace_id,
                        "name":    "user_feedback",
                        "value":   req.score,
                        "comment": req.comment or "",
                        "source":  req.source,
                        "dataType": "BOOLEAN",
                    },
                )
                if r.status_code in (200, 201):
                    langfuse_score_id = r.json().get("id")

    except Exception as e:
        print(f"[FeedbackRouter] Langfuse error: {e}")

    return FeedbackResponse(
        status="received",
        trace_id=req.trace_id,
        score=req.score,
        langfuse_score_id=langfuse_score_id,
    )
