"""Knowledge RAG API router."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from knowledge import retrieval

router = APIRouter()


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    scope: Optional[str] = None


class ReindexResponse(BaseModel):
    status: str
    chunks: int


@router.post("/query")
def knowledge_query(body: QueryRequest):
    results = retrieval.search(body.query, body.top_k, body.scope)
    return {"query": body.query, "results": results, "count": len(results)}


@router.get("/sources")
def knowledge_sources():
    return retrieval.sources()


@router.post("/reindex")
def knowledge_reindex():
    count = retrieval.rebuild()
    return ReindexResponse(status="ok", chunks=count)
