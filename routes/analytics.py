"""FutureShield AI — Focus Analytics: session trends, energy patterns, and productivity metrics."""

from fastapi import APIRouter
import database

router = APIRouter(tags=["Analytics"])


@router.get("/api/analytics/focus")
def get_focus_analytics(days: int = 30) -> dict:
    """Return aggregated focus analytics for the last N days."""

    # ── Daily session counts ──────────────────────────────────────
    daily = database.query_db(
        """SELECT DATE(start_time) as day,
                  COUNT(*) as sessions,
                  COALESCE(SUM(actual_duration_seconds), 0) as total_seconds,
                  COALESCE(AVG(energy_rating), 0) as avg_energy
           FROM focus_sessions
           WHERE start_time >= DATE('now', ?)
           GROUP BY DATE(start_time)
           ORDER BY day ASC""",
        (f"-{days} days",),
    )

    daily_data = []
    for row in daily:
        daily_data.append({
            "day": row["day"],
            "sessions": row["sessions"],
            "total_minutes": round(row["total_seconds"] / 60, 1),
            "avg_energy": round(row["avg_energy"], 1),
        })

    # ── Energy rating distribution ─────────────────────────────────
    energy_dist = database.query_db(
        """SELECT energy_rating, COUNT(*) as count
           FROM focus_sessions
           WHERE energy_rating IS NOT NULL
             AND start_time >= DATE('now', ?)
           GROUP BY energy_rating
           ORDER BY energy_rating ASC""",
        (f"-{days} days",),
    )
    energy_buckets = {"low": 0, "medium": 0, "high": 0}
    for row in energy_dist:
        rating = row["energy_rating"]
        if rating is None:
            continue
        if rating <= 3:
            energy_buckets["low"] += row["count"]
        elif rating <= 6:
            energy_buckets["medium"] += row["count"]
        else:
            energy_buckets["high"] += row["count"]

    # ── Session type breakdown ─────────────────────────────────────
    type_breakdown = database.query_db(
        """SELECT session_type, COUNT(*) as count
           FROM focus_sessions
           WHERE start_time >= DATE('now', ?)
           GROUP BY session_type
           ORDER BY count DESC""",
        (f"-{days} days",),
    )
    types = [{"type": row["session_type"], "count": row["count"]} for row in type_breakdown]

    # ── Avg duration by session type ───────────────────────────────
    duration_by_type = database.query_db(
        """SELECT session_type,
                  AVG(actual_duration_seconds) as avg_seconds,
                  COUNT(*) as count
           FROM focus_sessions
           WHERE status = 'completed'
             AND start_time >= DATE('now', ?)
           GROUP BY session_type""",
        (f"-{days} days",),
    )
    avg_durations = [
        {
            "type": row["session_type"],
            "avg_minutes": round(row["avg_seconds"] / 60, 1) if row["avg_seconds"] else 0,
            "count": row["count"],
        }
        for row in duration_by_type
    ]

    # ── Overall stats ──────────────────────────────────────────────
    all_sessions = database.query_db(
        "SELECT * FROM focus_sessions WHERE start_time >= DATE('now', ?)",
        (f"-{days} days",),
    )
    completed = [s for s in all_sessions if s["status"] == "completed"]
    total_minutes = sum(s.get("actual_duration_seconds", 0) for s in completed) // 60
    avg_energy_all = (
        round(sum(s["energy_rating"] for s in completed if s["energy_rating"] is not None) / len(completed), 1)
        if completed else 0
    )
    best_day = max(daily_data, key=lambda d: d["total_minutes"]) if daily_data else None
    streak = 0
    for d in reversed(daily_data):
        if d["sessions"] > 0:
            streak += 1
        else:
            break

    return {
        "daily": daily_data,
        "energy_distribution": energy_buckets,
        "type_breakdown": types,
        "avg_durations": avg_durations,
        "overall": {
            "total_sessions": len(completed),
            "total_focus_minutes": total_minutes,
            "avg_energy_rating": avg_energy_all,
            "best_day": best_day,
            "current_streak": streak,
            "days_analyzed": days,
        },
    }
