"""FutureShield AI — System Status endpoint."""

from fastapi import APIRouter
import database

router = APIRouter(tags=["Status"])


@router.get("/api/status")
def get_status() -> dict:
    goals = database.query_db("SELECT * FROM goals")
    if goals:
        success_score = int(sum(g["progress"] for g in goals) / len(goals))
    else:
        success_score = 90

    active_threats = database.query_db("SELECT COUNT(*) as count FROM threats WHERE resolved = 0", one=True)
    active_count = active_threats["count"] if active_threats else 0
    core_load = 15 + (active_count * 12)

    return {
        "success_score": success_score,
        "data_nodes": f"{4.2 + (len(goals) * 0.1):.1f}k",
        "latency": f"{10 + active_count * 2}ms",
        "telemetry": {
            "core_load": f"{min(core_load, 100)}%",
            "ai_engine": "ACTIVE",
        },
        "nodes": [
            {"id": "NY_01", "status": "ONLINE"},
            {"id": "LN_42", "status": "ONLINE"},
            {"id": "TK_09", "status": "SYNCING" if active_count > 1 else "ONLINE"},
            {"id": "SF_03", "status": "ONLINE"},
        ],
    }
