from fastapi import FastAPI
from pydantic import BaseModel
import os
import logging
import time

# Structured logging setup — same reasoning as the Go gateway's
# loggingMiddleware: this format is what Module 10's log pipeline will parse.
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("chat-service")

app = FastAPI(title="chat-service")


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str


@app.get("/health")
def health():
    # Kubernetes readiness/liveness probes hit this. Keep it dependency-free —
    # it should report "this process can serve HTTP", not "the database is up".
    # We'll add a separate /ready check later that DOES verify dependencies,
    # once Postgres/Redis are wired in (Module 4).
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    start = time.time()

    # STUB: real implementation will call Retrieval service for context,
    # then LLM Gateway for the model response. Both don't exist yet, so
    # this proves the service boundary and request/response shape now —
    # we'll swap this stub for real HTTP calls once those services exist.
    reply = f"[stub reply] you said: {req.message}"

    duration_ms = int((time.time() - start) * 1000)
    logger.info(
        f"conversation_id={req.conversation_id} "
        f"duration_ms={duration_ms} status=200"
    )

    return ChatResponse(conversation_id=req.conversation_id, reply=reply)
