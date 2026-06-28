"""
FutureShield AI — RAG Engine API Endpoints

Exposes the module-level RAG engine (from rag.py) via REST endpoints:
  GET  /api/rag/stats      — engine statistics
  GET  /api/rag/documents  — list indexed documents (paginated)
  POST /api/rag/query      — semantic search against the vector store
  POST /api/rag/reindex    — rebuild the vector index from current DB data
"""
from fastapi import APIRouter
from pydantic import BaseModel
import rag

router = APIRouter(tags=["RAG"])


class RAGQueryRequest(BaseModel):
    query: str
    n_results: int = 8


@router.get("/api/rag/stats")
def get_rag_stats() -> dict:
    """Return statistics about the RAG engine (backend type, document counts, etc.)."""
    engine = rag.get_engine()
    if engine is None or not engine._initialized:
        return {"initialized": False, "message": "RAG engine not initialized."}
    stats = engine.get_stats()
    stats["initialized"] = True
    return stats


@router.get("/api/rag/documents")
def list_rag_documents(
    limit: int = 20,
    offset: int = 0,
    type_filter: str | None = None,
) -> dict:
    """List all indexed documents with pagination and optional type filter."""
    engine = rag.get_engine()
    if engine is None or not engine._initialized:
        return {"documents": [], "total": 0}
    documents = engine.list_documents(limit=limit, offset=offset, type_filter=type_filter)
    total = engine.get_stats().get("total_documents", 0)
    return {"documents": documents, "total": total, "limit": limit, "offset": offset}


@router.post("/api/rag/query")
def query_rag(request: RAGQueryRequest) -> dict:
    """Query the vector store and return matching documents with similarity distances."""
    engine = rag.get_engine()
    if engine is None or not engine._initialized:
        return {"results": [], "message": "RAG engine not initialized"}
    results = engine.query(request.query, n_results=request.n_results)
    return {"query": request.query, "results": results, "result_count": len(results)}


@router.post("/api/rag/reindex")
def reindex_rag() -> dict:
    """Re-index all data from the database into the RAG engine."""
    engine = rag.get_engine()
    if engine is None or not engine._initialized:
        return {"status": "error", "message": "RAG engine not initialized"}

    if engine._fallback is not None:
        engine._fallback.clear()
    elif engine._chroma_mode and engine._chroma_collection is not None:
        try:
            all_ids = engine._chroma_collection.get()["ids"]
            if all_ids:
                engine._chroma_collection.delete(ids=all_ids)
        except Exception:
            return {"status": "error", "message": "Failed to clear ChromaDB"}

    success = engine.index_all_data()
    stats = engine.get_stats()
    return {
        "status": "success" if success else "error",
        "total_documents": stats.get("total_documents", 0),
        "documents_by_type": stats.get("documents_by_type", {}),
    }