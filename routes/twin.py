"""FutureShield AI — Digital Twin endpoint."""

from fastapi import APIRouter
import database

router = APIRouter(tags=["Twin"])


@router.get("/api/twin")
def get_twin_data() -> dict:
    records = database.query_db("SELECT energy_level FROM focus_records ORDER BY id DESC LIMIT 8")
    energy_levels = [r["energy_level"] for r in reversed(records)] if records else [50] * 8

    completed_sessions = database.query_db(
        "SELECT * FROM focus_sessions WHERE status = 'completed' ORDER BY id DESC LIMIT 10"
    )
    total_completed = len(completed_sessions)

    if completed_sessions:
        avg_rating = sum(s["energy_rating"] or 5 for s in completed_sessions) / total_completed
        total_seconds = sum(s["actual_duration_seconds"] or 0 for s in completed_sessions)
        total_minutes = total_seconds // 60
        consistency_bonus = min(10, total_completed * 2)
        behavior_score = min(99.9, round(avg_rating * 9 + consistency_bonus, 1))

        recent = completed_sessions[:3]
        prior = completed_sessions[3:6]
        if recent and prior:
            recent_avg = sum(s["energy_rating"] or 5 for s in recent) / len(recent)
            prior_avg = sum(s["energy_rating"] or 5 for s in prior) / len(prior)
            change_pct = round(((recent_avg - prior_avg) / max(prior_avg, 1)) * 100, 1)
            behavior_change = f"{'+' if change_pct >= 0 else ''}{change_pct}% vs baseline"
        else:
            behavior_change = "+0.0% vs baseline"

        neural_drift = f"{min(5, round(100 / max(total_completed, 1), 2))}%"
    else:
        behavior_score = 92.0
        behavior_change = "+0.0% vs baseline"
        neural_drift = "0.04%"
        total_minutes = 0

    active_session = database.query_db(
        "SELECT * FROM focus_sessions WHERE status = 'active' ORDER BY id DESC LIMIT 1",
        one=True,
    )

    return {
        "behavior_score": behavior_score,
        "behavior_change": behavior_change,
        "energy_levels": energy_levels,
        "neural_drift": neural_drift,
        "user_focus_data": {
            "total_sessions_completed": total_completed,
            "total_focus_minutes": total_minutes,
            "is_in_session": active_session is not None,
        },
        "success_dna": {
            "logic_resilience": "Extreme",
            "decision_velocity": "420ms",
            "risk_appetite": "Calculated",
            "sync_quality": "Pristine",
        },
    }
