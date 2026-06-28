"""FutureShield AI — Focus Timer endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import database

router = APIRouter(tags=["Focus"])


class FocusStartRequest(BaseModel):
    duration_minutes: int = 25
    session_type: str = "focus"


class FocusStopRequest(BaseModel):
    energy_rating: int = 5


@router.post("/api/focus/start")
def start_focus_session(request: FocusStartRequest) -> dict:
    active = database.query_db(
        "SELECT * FROM focus_sessions WHERE status = 'active' ORDER BY id DESC LIMIT 1",
        one=True,
    )
    if active:
        database.execute_db(
            "UPDATE focus_sessions SET status = 'abandoned', end_time = CURRENT_TIMESTAMP WHERE id = ?",
            (active["id"],),
        )

    session_id = database.insert_and_get_id(
        "INSERT INTO focus_sessions (duration_minutes, session_type, status) VALUES (?, ?, 'active')",
        (request.duration_minutes, request.session_type),
    )
    session = database.query_db("SELECT * FROM focus_sessions WHERE id = ?", (session_id,), one=True)
    return {"status": "focus_started", "session": dict(session)}


@router.post("/api/focus/stop")
def stop_focus_session(request: FocusStopRequest) -> dict:
    active = database.query_db(
        "SELECT * FROM focus_sessions WHERE status = 'active' ORDER BY id DESC LIMIT 1",
        one=True,
    )
    if not active:
        raise HTTPException(status_code=404, detail="No active focus session found")

    database.execute_db(
        """UPDATE focus_sessions
           SET status = 'completed', end_time = CURRENT_TIMESTAMP,
               energy_rating = ?,
               actual_duration_seconds = CAST(
                   (julianday(CURRENT_TIMESTAMP) - julianday(start_time)) * 86400 AS INTEGER
               )
           WHERE id = ?""",
        (request.energy_rating, active["id"]),
    )

    # Store energy rating (1-10) directly; scale to 0-100 for the energy_level field
    energy_level: int = min(100, max(0, request.energy_rating * 10))
    database.execute_db(
        "INSERT INTO focus_records (energy_level) VALUES (?)",
        (energy_level,),
    )

    session = database.query_db("SELECT * FROM focus_sessions WHERE id = ?", (active["id"],), one=True)
    return {"status": "focus_stopped", "session": dict(session)}


@router.get("/api/focus/current")
def get_current_session() -> dict:
    active = database.query_db(
        "SELECT * FROM focus_sessions WHERE status = 'active' ORDER BY id DESC LIMIT 1",
        one=True,
    )
    if not active:
        return {"active": False, "session": None}
    return {"active": True, "session": dict(active)}


@router.get("/api/focus/sessions")
def get_focus_sessions(limit: int = 20, offset: int = 0, status: str | None = None) -> dict:
    if status:
        sessions = database.query_db(
            "SELECT * FROM focus_sessions WHERE status = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (status, limit, offset),
        )
        total = database.query_db("SELECT COUNT(*) as count FROM focus_sessions WHERE status = ?", (status,), one=True)
    else:
        sessions = database.query_db(
            "SELECT * FROM focus_sessions ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        total = database.query_db("SELECT COUNT(*) as count FROM focus_sessions", one=True)

    all_completed = database.query_db("SELECT * FROM focus_sessions WHERE status = 'completed'")
    total_focus_minutes = sum(s.get("actual_duration_seconds", 0) for s in all_completed) // 60
    avg_energy = (
        sum(s["energy_rating"] for s in all_completed if s["energy_rating"] is not None) / len(all_completed)
    ) if all_completed else 0

    return {
        "sessions": [dict(s) for s in sessions],
        "total": total["count"] if total else 0,
        "limit": limit,
        "offset": offset,
        "stats": {
            "total_sessions": len(all_completed),
            "total_focus_minutes": total_focus_minutes,
            "average_energy_rating": round(avg_energy, 1),
        },
    }
