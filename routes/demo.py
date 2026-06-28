"""FutureShield AI — Demo Data endpoints."""

from fastapi import APIRouter, Response
from datetime import datetime, timedelta
from pydantic import BaseModel, root_validator
import random
import json

import database
import rag

router = APIRouter(tags=["Demo"])


# ---------------------------------------------------------------------------
# Pydantic models for import payload validation
# ---------------------------------------------------------------------------


class ImportGoal(BaseModel):
    """A single goal record in the import payload."""
    id: int | None = None
    title: str = ""
    status: str = "ACTIVE"
    progress: int = 0
    deadline: str = ""


class ImportThreat(BaseModel):
    """A single threat record in the import payload."""
    id: str = ""
    name: str = ""
    urgency: str = "LOW"
    probability: int = 0
    success_rate: str = "0%"
    x_pos: int = 0
    y_pos: int = 0
    type: str = "optimized"
    resolved: int = 0


class ImportFocusRecord(BaseModel):
    """A single focus record (energy level) in the import payload."""
    id: int | None = None
    timestamp: str = ""
    energy_level: int = 50


class ImportFocusSession(BaseModel):
    """A single focus session in the import payload."""
    id: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    duration_minutes: int = 0
    actual_duration_seconds: int = 0
    energy_rating: int | None = None
    session_type: str = "focus"
    status: str = "completed"


class ImportData(BaseModel):
    """Container for all entity arrays in the import payload."""
    goals: list[ImportGoal] = []
    threats: list[ImportThreat] = []
    focus_records: list[ImportFocusRecord] = []
    focus_sessions: list[ImportFocusSession] = []


CURRENT_IMPORT_VERSION = "1.0"
_SUPPORTED_VERSIONS = {"1.0"}


class ImportPayload(BaseModel):
    """Top-level structure accepted by POST /api/demo/import."""
    version: str = CURRENT_IMPORT_VERSION
    data: ImportData = ImportData()

    @root_validator(pre=False, skip_on_failure=True)
    def _check_version(cls, values: dict) -> dict:
        """Validate the version field after model initialization."""
        version = values.get("version", "1.0")
        if version not in _SUPPORTED_VERSIONS:
            raise ValueError(
                f"Unsupported import version '{version}'. "
                f"Supported versions: {', '.join(sorted(_SUPPORTED_VERSIONS))}. "
                "Generate a fresh export from the current system to get a compatible file."
            )
        return values


@router.post("/api/demo/seed")
def seed_demo_data() -> dict:
    """Seed rich demo data for an impressive first-time experience."""
    now = datetime.now()

    demo_goals = [
        ("Project Phoenix: Core AI Pipeline Integration", "ACTIVE", 65, (now + timedelta(days=3)).strftime("%Y-%m-%d")),
        ("Digital Twin: Real-time Energy Synchronization", "ACTIVE", 42, (now + timedelta(days=7)).strftime("%Y-%m-%d")),
        ("Radar System: Multi-threat Detection Network", "ACTIVE", 78, (now + timedelta(days=2)).strftime("%Y-%m-%d")),
        ("Simulation Engine: Monte Carlo v2.0 Upgrade", "ACTIVE", 31, (now + timedelta(days=10)).strftime("%Y-%m-%d")),
        ("AI Rescue: Autonomous Code Generation Module", "COMPLETED", 100, (now - timedelta(days=1)).strftime("%Y-%m-%d")),
        ("Knowledge Graph: Cross-entity Dependency Mapping", "ACTIVE", 55, (now + timedelta(days=5)).strftime("%Y-%m-%d")),
        ("Voice Pilot: Multi-language Command Support", "PENDING", 0, (now + timedelta(days=14)).strftime("%Y-%m-%d")),
        ("Calendar AI: Predictive Deep Work Scheduling", "ACTIVE", 23, (now + timedelta(days=9)).strftime("%Y-%m-%d")),
        ("Security Layer: End-to-end Encryption Overhaul", "COMPLETED", 100, (now - timedelta(days=2)).strftime("%Y-%m-%d")),
        ("Mobile Client: PWA Push Notification Integration", "ACTIVE", 88, (now + timedelta(days=1)).strftime("%Y-%m-%d")),
    ]

    database.execute_db("DELETE FROM goals")
    for title, status, progress, deadline in demo_goals:
        database.insert_and_get_id(
            "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
            (title, status, progress, deadline),
        )

    database.execute_db("DELETE FROM threats")
    demo_threats = [
        ("QW-771", "Cross-Origin Resource Cascade Failure", "CRITICAL", 92, "8.1%", 25, 18, "critical", 0),
        ("XR-904", "Quantum Decoherence Gap", "HIGH", 88, "12.4%", 30, 20, "critical", 0),
        ("QR-552", "Memory Leak in Simulation Pipeline", "HIGH", 76, "24.0%", 55, 35, "critical", 0),
        ("TR-421", "Latency Spike in Cluster 7", "MED", 42, "65.1%", 80, 60, "warning", 0),
        ("SK-883", "Stale Dependency Graph Anomaly", "MED", 38, "72.3%", 65, 75, "warning", 0),
        ("BV-112", "Unmapped Resource Call", "LOW", 12, "98.2%", 45, 45, "optimized", 0),
        ("PL-336", "Parallel Task Queue Overflow Risk", "MED", 54, "46.0%", 15, 70, "warning", 0),
        ("DN-204", "DNS Resolution Fragmentation", "LOW", 8, "99.1%", 90, 25, "optimized", 0),
    ]
    for t in demo_threats:
        database.execute_db(
            "INSERT INTO threats (id, name, urgency, probability, success_rate, x_pos, y_pos, type, resolved) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            t,
        )

    database.execute_db("DELETE FROM focus_records")
    energy_curve = [35, 45, 60, 78, 92, 95, 85, 65, 45, 50, 55, 70, 85, 82, 72, 60, 48, 40, 35, 30]
    for level in energy_curve:
        database.execute_db("INSERT INTO focus_records (energy_level) VALUES (?)", (level,))

    database.execute_db("DELETE FROM focus_sessions")
    for i in range(15):
        mins = random.choice([15, 25, 30, 45, 60])
        dur_seconds = mins * 60 - random.randint(0, 120)
        rating = random.randint(4, 10)
        database.execute_db(
            """INSERT INTO focus_sessions
               (duration_minutes, actual_duration_seconds, energy_rating, session_type, status, start_time, end_time)
               VALUES (?, ?, ?, 'focus', 'completed',
                       datetime('now', ? || ' hours'),
                       datetime('now', ? || ' hours'))""",
            (mins, dur_seconds, rating, f"-{i+2}", f"-{i+2}"),
        )

    rag_engine = rag.get_engine()
    if rag_engine:
        rag_engine.index_all_data()

    return {
        "status": "demo_seeded",
        "goals": len(demo_goals),
        "threats": len(demo_threats),
        "focus_records": len(energy_curve),
        "focus_sessions": 15,
        "message": "Rich demo data loaded. Ready for walkthrough.",
    }


@router.post("/api/demo/reset")
def reset_demo_data() -> dict:
    """Reset to default seed data."""
    database.execute_db("DELETE FROM goals")
    database.execute_db("DELETE FROM threats")
    database.execute_db("DELETE FROM focus_records")
    database.execute_db("DELETE FROM focus_sessions")
    database.init_db()
    return {"status": "reset_complete", "message": "Database reset to defaults."}


@router.post("/api/demo/import")
def import_all_data(payload: ImportPayload) -> dict:
    """Import goals, threats, focus records, and focus sessions from an export JSON payload.

    Expects the same JSON structure produced by GET /api/demo/export:
    ```json
    {
      "data": {
        "goals": [{"id": 1, "title": "...", "status": "...", "progress": 0, "deadline": "..."}, ...],
        "threats": [{"id": "XR-904", "name": "...", ...}, ...],
        "focus_records": [{"id": 1, "timestamp": "...", "energy_level": 50}, ...],
        "focus_sessions": [{"id": 1, "start_time": "...", ...}, ...]
      }
    }
    ```
    """
    data = payload.data
    imported = {"goals": 0, "threats": 0, "focus_records": 0, "focus_sessions": 0}

    # ── Import goals ──────────────────────────────────────────────
    if data.goals:
        database.execute_db("DELETE FROM goals")
        for g in data.goals:
            database.insert_and_get_id(
                "INSERT INTO goals (id, title, status, progress, deadline) VALUES (?, ?, ?, ?, ?)",
                (g.id, g.title, g.status, g.progress, g.deadline),
            )
            imported["goals"] += 1

    # ── Import threats ────────────────────────────────────────────
    if data.threats:
        database.execute_db("DELETE FROM threats")
        for t in data.threats:
            database.execute_db(
                """INSERT INTO threats (id, name, urgency, probability, success_rate, x_pos, y_pos, type, resolved)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (t.id, t.name, t.urgency, t.probability, t.success_rate,
                 t.x_pos, t.y_pos, t.type, t.resolved),
            )
            imported["threats"] += 1

    # ── Import focus_records ──────────────────────────────────────
    if data.focus_records:
        database.execute_db("DELETE FROM focus_records")
        for r in data.focus_records:
            database.execute_db(
                "INSERT INTO focus_records (id, timestamp, energy_level) VALUES (?, ?, ?)",
                (r.id, r.timestamp or datetime.now().isoformat(), r.energy_level),
            )
            imported["focus_records"] += 1

    # ── Import focus_sessions ─────────────────────────────────────
    if data.focus_sessions:
        database.execute_db("DELETE FROM focus_sessions")
        for s in data.focus_sessions:
            database.execute_db(
                """INSERT INTO focus_sessions
                   (id, start_time, end_time, duration_minutes, actual_duration_seconds,
                    energy_rating, session_type, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (s.id, s.start_time, s.end_time, s.duration_minutes,
                 s.actual_duration_seconds, s.energy_rating, s.session_type, s.status),
            )
            imported["focus_sessions"] += 1

    # ── Re-index RAG ──────────────────────────────────────────────
    rag_engine = rag.get_engine()
    if rag_engine:
        rag_engine.index_all_data()

    return {
        "status": "import_complete",
        "imported": imported,
        "message": f"Restored {imported['goals']} goals, {imported['threats']} threats, "
                    f"{imported['focus_records']} focus records, "
                    f"{imported['focus_sessions']} focus sessions.",
    }


@router.get("/api/demo/export")
def export_all_data() -> Response:
    """Export all goals, threats, focus records, and focus sessions as JSON for backup/portability.

    Returns a downloadable JSON file with all user data.
    """
    goals = database.query_db("SELECT * FROM goals")
    threats = database.query_db("SELECT * FROM threats")
    focus_records = database.query_db("SELECT * FROM focus_records")
    focus_sessions = database.query_db("SELECT * FROM focus_sessions")

    export_data = {
        "exported_at": datetime.now().isoformat(),
        "version": "1.0",
        "description": "FutureShield AI — full data export",
        "data": {
            "goals": goals,
            "threats": threats,
            "focus_records": focus_records,
            "focus_sessions": focus_sessions,
        },
        "stats": {
            "goals": len(goals),
            "threats": len(threats),
            "focus_records": len(focus_records),
            "focus_sessions": len(focus_sessions),
        },
    }

    json_bytes = json.dumps(export_data, indent=2, default=str).encode("utf-8")
    filename = f"futureshield_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(json_bytes)),
        },
    )