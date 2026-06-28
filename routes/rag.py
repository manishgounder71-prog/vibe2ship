from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import requests
import time
from database import query_db
import rag

router = APIRouter(tags=["RAG"])

# Hugging Face API configuration (free tier)
HF_API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-large"
HF_TOKEN = os.getenv("HF_TOKEN", "")  # Optional for higher rate limits

class RAGQueryRequest(BaseModel):
    query: str
    n_results: int = 8

class GenerateMitigationRequest(BaseModel):
    threat_id: str

def query_huggingface(payload):
    """Query Hugging Face Inference API with fallback"""
    try:
        headers = {}
        if HF_TOKEN:
            headers["Authorization"] = f"Bearer {HF_TOKEN}"

        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"HF API error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"HF API request failed: {e}")
        return None

def extract_action_steps(text):
    """Extract actionable steps from generated text"""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    steps = []

    for line in lines:
        # Remove numbering if present
        clean_line = line.lstrip('0123456789. )-')
        if len(clean_line) > 10 and any(word in clean_line.lower() for word in
                                       ['evacuate', 'contain', 'secure', 'evacuate', 'move',
                                        'establish', 'deploy', 'notify', 'alert', 'protect']):
            steps.append(clean_line)
            if len(steps) >= 3:
                break

    return steps

def generate_fallback_plan(threat):
    """Generate a plausible fallback plan when API fails"""
    threat_type = threat['type'].lower()
    urgency = threat['urgency'].lower()

    # Base tactics by threat type
    tactics = {
        'fire': [
            f"Establish {max(30, threat['x_pos']//10)}m safety perimeter around coordinates ({threat['x_pos']}, {threat['y_pos']})",
            f"Deploy {['engine', 'ladder', 'rescue'][threat['x_pos']%3]} unit to {threat['y_pos'] > 150 and 'north' or 'south'} flank",
            f"Initiate evacuation of sectors {chr(65 + (threat['x_pos']//20))} through {chr(65 + (threat['x_pos']//20 + 2))}"
        ],
        'flood': [
            f"Activate flood barriers at grid reference ({threat['x_pos']-10},{threat['y_pos']})",
            f"Deploy sandbag teams to reinforce eastern bank near ({threat['x_pos']+15},{threat['y_pos']})",
            f"Issue evacuation order for low-lying areas west of coordinate {threat['y_pos']}"
        ],
        'chemical': [
            f"Establish {max(50, threat['y_pos']//2)}m exclusion zone downwind from ({threat['x_pos']}, {threat['y_pos']})",
            f"Deploy HAZMAT team with Level {['A','B','C'][threat['x_pos']%3]} protection to hot zone",
            f"Implement shelter-in-place for buildings within 200m radius of incident"
        ],
        'active_shooter': [
            f"Establish perimeter and contain threat within building sector {chr(65 + (threat['x_pos']//15))}",
            f"Deploy negotiator and SWAT team to {threat['x_pos'] > 100 and 'east' or 'west'} wing",
            f"Initiate lockdown of adjacent zones and begin casualty collection point setup"
        ],
        'default': [
            f"Establish incident command post at ({threat['x_pos']+20},{threat['y_pos']+20})",
            f"Deploy assessment team to verify threat characteristics at reported location",
            f"Begin evacuation of immediate surroundings while awaiting further intelligence"
        ]
    }

    selected_tactics = tactics.get(threat_type, tactics['default'])

    # Adjust based on urgency
    if urgency == 'high':
        selected_tactics = [t.replace('Consider', 'Immediately').replace('Evaluate', 'Execute') for t in selected_tactics]
    elif urgency == 'low':
        selected_tactics = [t.replace('Immediately', 'Consider').replace('Execute', 'Evaluate') for t in selected_tactics]

    return "\n".join([f"{i+1}. {t}" for i, t in enumerate(selected_tactics)])

@router.get("/api/rag/stats")
def get_rag_stats() -> dict:
    """Return statistics about the RAG engine (backend type, document counts, etc.)."""
    engine = rag.get_engine()
    if engine is None or not engine._initialized:
        return {
            "initialized": False,
            "message": "RAG engine not initialized. Restart the server.",
        }
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
    return {
        "documents": documents,
        "total": total,
        "limit": limit,
        "offset": offset,
    }

@router.post("/api/rag/query")
def query_rag(request: RAGQueryRequest) -> dict:
    """Query the vector store and return matching documents with similarity distances."""
    engine = rag.get_engine()
    if engine is None or not engine._initialized:
        return {"results": [], "message": "RAG engine not initialized"}

    results = engine.query(request.query, n_results=request.n_results)
    return {
        "query": request.query,
        "results": results,
        "result_count": len(results),
    }

@router.post("/api/rag/reindex")
def reindex_rag() -> dict:
    """Re-index all data from the database into the RAG engine."""
    engine = rag.get_engine()
    if engine is None or not engine._initialized:
        return {"status": "error", "message": "RAG engine not initialized"}

    # Clear existing data in the fallback store
    if engine._fallback is not None:
        engine._fallback.clear()
    elif engine._chroma_mode and engine._chroma_collection is not None:
        try:
            all_ids = engine._chroma_collection.get()["ids"]
            if all_ids:
                engine._chroma_collection.delete(ids=all_ids)
        except Exception as e:
            return {"status": "error", "message": f"Failed to clear ChromaDB: {e}"}

    success = engine.index_all_data()
    stats = engine.get_stats()
    return {
        "status": "success" if success else "error",
        "total_documents": stats.get("total_documents", 0),
        "documents_by_type": stats.get("documents_by_type", {}),
    }

@router.post("/api/rag/generate-mitigation")
def generate_mitigation(request: GenerateMitigationRequest) -> dict:
    """Generate AI-powered mitigation plan for a threat"""
    try:
        threat_id = request.threat_id

        # Get threat details from database
        threat = query_db(
            "SELECT * FROM threats WHERE id = ?",
            (threat_id,),
            one=True
        )

        if not threat:
            raise HTTPException(status_code=404, detail="Threat not found")

        # Simulate processing time for realism
        time.sleep(0.8)

        # Use RAG to get relevant context (if available)
        context = ""
        try:
            # Query the RAG engine for threat-related information
            rag_query = f"{threat['name']} {threat['type']} mitigation procedures"
            rag_results = rag.get_engine().query(rag_query, n_results=3)
            if rag_results:
                context = " ".join([doc.get('text', '') for doc in rag_results[:2]])
        except Exception as e:
            print(f"RAG query failed: {e}")
            # Continue without RAG context

        # Create prompt for the LLM
        prompt = f"""As an emergency response expert, generate 3 specific, actionable mitigation steps for a {threat['type']} threat with {threat['urgency']} urgency level located at coordinates ({threat['x_pos']}, {threat['y_pos']}).
        Threat details: {threat['name']} with {threat['probability']}% probability of success.
        Context from knowledge base: {context}
        Focus on immediate responder safety and public protection. Be concise and tactical.
        Format as a numbered list."""

        # Try Hugging Face API first
        hf_result = query_huggingface({
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 200,
                "temperature": 0.7,
                "do_sample": True,
                "return_full_text": False
            }
        })

        if hf_result and isinstance(hf_result, list) and len(hf_result) > 0:
            generated_text = hf_result[0].get('generated_text', '')
            # Extract actionable steps from generated text
            steps = extract_action_steps(generated_text)
            if len(steps) >= 3:
                mitigation_plan = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps[:3])])
                source = "huggingface"
            else:
                # Fallback to template if extraction failed
                mitigation_plan = generate_fallback_plan(threat)
                source = "fallback (extraction failed)"
        else:
            # Use fallback plan if HF API fails
            mitigation_plan = generate_fallback_plan(threat)
            source = "fallback (HF API unavailable)"

        return {
            "threat_id": threat_id,
            "mitigation_plan": mitigation_plan,
            "generated_at": time.time(),
            "source": source,
            "context_used": bool(context)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating mitigation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Register blueprint in main app (not needed for FastAPI, but keeping for reference)
def init_rag_routes(app):
    app.include_router(router, prefix="/api/rag")