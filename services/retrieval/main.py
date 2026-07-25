from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title="retrieval-service")


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
