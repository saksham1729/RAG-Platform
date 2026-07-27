from fastapi import FastAPI, Request
from pydantic import BaseModel
import time
from prometheus_client import Counter, Histogram, make_asgi_app

app = FastAPI(title="ingestion-service")

REQUESTS_TOTAL = Counter(
    "ingestion_requests_total", "Total requests handled by the ingestion service", ["path", "status"]
)
REQUEST_DURATION = Histogram(
    "ingestion_request_duration_seconds", "Request duration in seconds", ["path"]
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


class IngestRequest(BaseModel):
    document_id: str
    text: str


class IngestResponse(BaseModel):
    document_id: str
    chunk_count: int


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest):
    # STUB: real implementation chunks the document (e.g. by token count
    # with overlap) and calls the Embedding service for each chunk.
    # A naive length/500 split just proves the request/response contract
    # for now — real chunking logic comes once Retrieval exists to test against.
    chunk_count = max(1, len(req.text) // 500)
    return IngestResponse(document_id=req.document_id, chunk_count=chunk_count)
