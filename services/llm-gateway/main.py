from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List
import time
from prometheus_client import Counter, Histogram, make_asgi_app

app = FastAPI(title="llm-gateway")

REQUESTS_TOTAL = Counter(
    "llm_gateway_requests_total", "Total requests handled by the llm-gateway service", ["path", "status"]
)
REQUEST_DURATION = Histogram(
    "llm_gateway_request_duration_seconds", "Request duration in seconds", ["path"]
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    REQUESTS_TOTAL.labels(path=request.url.path, status=response.status_code).inc()
    REQUEST_DURATION.labels(path=request.url.path).observe(duration)
    return response


app.mount("/metrics", make_asgi_app())


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
