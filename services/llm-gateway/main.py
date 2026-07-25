from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title="llm-gateway")


class Message(BaseModel):
    role: str
    content: str


class CompletionRequest(BaseModel):
    messages: List[Message]


class CompletionResponse(BaseModel):
    content: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/complete", response_model=CompletionResponse)
def complete(req: CompletionRequest):
    # STUB: real implementation calls the Anthropic API (or another
    # provider) here. This is the ONLY service that will hold a model
    # API key — every other service reaches the model through this one,
    # so swapping providers later touches exactly one file, not seven.
    last_user_msg = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    return CompletionResponse(content=f"[stub llm reply] re: {last_user_msg}")
