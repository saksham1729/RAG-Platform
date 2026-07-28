from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List
import time
from prometheus_client import Counter, Histogram, make_asgi_app

app = FastAPI(title="retrieval-service")

REQUESTS_TOTAL = Counter(
    "retrieval_requests_total", "Total requests handled by the retrieval service", ["path", "status"]
)
REQUEST_DURATION = Histogram(
    "retrieval_request_duration_seconds", "Request duration in seconds", ["path"]
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


class SearchRequest(BaseModel):
    query: str
    top_k: int = 3


class SearchResult(BaseModel):
    chunk_id: str
    text: str
    score: float


class SearchResponse(BaseModel):
    results: List[SearchResult]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    # STUB: real implementation embeds req.query and does a vector
    # similarity search against Qdrant. Wired in Module 4 once Qdrant
    # is running as a StatefulSet in the cluster.
    fake_results = [
        SearchResult(chunk_id=f"chunk-{i}", text=f"stub context for '{req.query}'", score=1.0 - i * 0.1)
        for i in range(req.top_k)
    ]
    return SearchResponse(results=fake_results)
