from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
import logging
import time
from prometheus_client import Counter, Histogram, make_asgi_app

# Structured logging setup — same reasoning as the Go gateway's
# loggingMiddleware: this format is what Module 10's log pipeline will parse.
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("chat-service")

app = FastAPI(title="chat-service")

# Same RED-method metrics as the Go services, just via prometheus_client's
# API instead of client_golang's. Counter/Histogram behave identically
# conceptually — labeled counters and bucketed timing distributions.
REQUESTS_TOTAL = Counter(
    "chat_requests_total",
    "Total requests handled by the chat service",
    ["path", "status"],
)
REQUEST_DURATION = Histogram(
    "chat_request_duration_seconds",
    "Request duration in seconds",
    ["path"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    # FastAPI middleware wraps the ASGI call chain, not a synchronous
    # handler like Go's http.Handler — call_next is itself async, and we
    # must await it. The timing/recording logic is otherwise the same idea.
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    REQUESTS_TOTAL.labels(path=request.url.path, status=response.status_code).inc()
    REQUEST_DURATION.labels(path=request.url.path).observe(duration)

    return response


# make_asgi_app() builds a small standalone ASGI application that serves
# Prometheus's text exposition format — mounting it is how prometheus_client
# integrates with FastAPI, rather than writing a manual @app.get("/metrics").
app.mount("/metrics", make_asgi_app())


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
