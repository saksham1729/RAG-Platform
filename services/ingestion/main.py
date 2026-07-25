from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="ingestion-service")


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
