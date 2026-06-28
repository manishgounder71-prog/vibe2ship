"""FutureShield AI — Timeline: chronological event feed from all sources."""

from fastapi import APIRouter
import database

router = APIRouter(tags=["Timeline"])


@router.get("/api/timeline")
def get_timeline(limit: int = 50, offset: int = 0, type_filter: str | None = None) -> dict:
    """Return a merged, reverse-chronological event feed across all data sources."""
    events: list[dict] = []

    # ── Focus sessions ────────────────────────────────────────────
    if not type_filter or type_filter == "focus":
        sessions = database.query_db(
            "SELECT * FROM focus_sessions ORDER BY start_time DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        for s in sessions:
            status = s.get("status", "")
            if status == "completed":
                title = "Focus Session Completed"
                desc = f"{s.get('actual_duration_seconds', 0) // 60}m · Energy: {s.get('energy_rating', '—')}/10"
                icon = "check_circle"
                color = "#00d4ff"
            elif status == "active":
                title = "Focus Session Started"
                desc = f"{s.get('duration_minutes', 25)}m {s.get('session_type', 'focus')} session"
                icon = "timelapse"
                color = "#d0bcff"
            elif status == "abandoned":
                title = "Focus Session Abandoned"
                desc = f"{s.get('duration_minutes', 25)}m session ended early"
                icon = "cancel"
                color = "#ffb4ab"
            else:
                title = "Focus Session"
                desc = s.get("session_type", "focus")
                icon = "timelapse"
                color = "#859398"

            events.append({
                "id": f"focus_{s['id']}",
                "timestamp": s.get("start_time", ""),
                "type": "focus",
                "title": title,
                "description": desc,
                "icon": icon,
                "color": color,
                "raw": dict(s),
            })

    # ── Goals ─────────────────────────────────────────────────────
    if not type_filter or type_filter == "goal":
        goals = database.query_db(
            "SELECT * FROM goals ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        for g in goals:
            status = g.get("status", "")
            if status == "COMPLETED":
                title = f"Goal Completed: {g['title']}"
                desc = "100% achieved"
                icon = "celebration"
                color = "#00d4ff"
            elif status == "ACTIVE":
                title = f"Milestone Active: {g['title']}"
                desc = f"{g.get('progress', 0)}% complete · Due {g.get('deadline', '')}"
                icon = "flag"
                color = "#d0bcff"
            else:
                title = f"Goal Created: {g['title']}"
                desc = f"Due {g.get('deadline', '')}"
                icon = "add_task"
                color = "#93ecff"

            events.append({
                "id": f"goal_{g['id']}",
                "timestamp": g.get("deadline", ""),
                "type": "goal",
                "title": title,
                "description": desc,
                "icon": icon,
                "color": color,
                "raw": dict(g),
            })

    # ── Threats ───────────────────────────────────────────────────
    if not type_filter or type_filter == "threat":
        threats = database.query_db(
            "SELECT * FROM threats ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        for t in threats:
            resolved = t.get("resolved", 0)
            if resolved:
                title = f"Threat Resolved: {t['name']}"
                desc = f"{t.get('type', 'unknown')} · Success rate {t.get('success_rate', '—')}"
                icon = "verified"
                color = "#00d4ff"
            else:
                title = f"Threat Detected: {t['name']}"
                desc = f"Urgency {t.get('urgency', 'LOW')} · Probability {t.get('probability', 0)}%"
                icon = "warning"
                color = "#ffb4ab"

            events.append({
                "id": f"threat_{t['id']}",
                "timestamp": "",
                "type": "threat",
                "title": title,
                "description": desc,
                "icon": icon,
                "color": color,
                "raw": dict(t),
            })

    # Sort by timestamp descending (empty timestamps last)
    events.sort(key=lambda e: e["timestamp"] or "", reverse=True)

    return {
        "events": events[:limit],
        "total": len(events),
        "limit": limit,
        "offset": offset,
        "type_filter": type_filter,
    }
