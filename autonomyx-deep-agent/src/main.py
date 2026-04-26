from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from .agent import agent
from langchain_core.messages import HumanMessage, AIMessage

app = FastAPI(title="Autonomyx Deep Agent API")

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = []

@app.post("/chat")
async def chat(request: ChatRequest):
    messages = []
    for h in request.history:
        if h["role"] == "user":
            messages.append(HumanMessage(content=h["content"]))
        else:
            messages.append(AIMessage(content=h["content"]))
    
    messages.append(HumanMessage(content=request.message))
    
    try:
        result = agent.invoke({"messages": messages})
        last_message = result["messages"][-1]
        return {"response": last_message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
