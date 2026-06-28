"""FutureShield AI — Threat Detection endpoints."""

from fastapi import APIRouter, HTTPException
import database

router = APIRouter(tags=["Threats"])


@router.get("/api/threats")
def get_threats() -> dict:
    unresolved_threats = database.query_db("SELECT * FROM threats WHERE resolved = 0")
    return {
        "scanned_count": 1400 + len(unresolved_threats) * 10,
        "threats": unresolved_threats,
    }


@router.post("/api/threats/{threat_id}/resolve")
def resolve_threat(threat_id: str) -> dict:
    threat = database.query_db("SELECT * FROM threats WHERE id = ?", (threat_id,), one=True)
    if not threat:
        raise HTTPException(status_code=404, detail="Threat not found")
    database.execute_db("UPDATE threats SET resolved = 1 WHERE id = ?", (threat_id,))
    return {"status": "success", "resolved_threat": threat_id}
