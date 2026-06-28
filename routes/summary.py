"""FutureShield AI — AI-powered Smart Summary endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel
import json

import database
import rag
from routes import call_gemini_with_queue

router = APIRouter(tags=["Summary"])


class SummaryPeriod(BaseModel):
    period: str = "daily"


@router.post("/api/summary")
async def get_ai_summary(request: SummaryPeriod) -> dict:
    goals = database.query_db("SELECT * FROM goals ORDER BY id ASC")
    threats = database.query_db("SELECT * FROM threats WHERE resolved = 0")
    focus_records = database.query_db("SELECT energy_level, timestamp FROM focus_records ORDER BY id DESC LIMIT 8")

    total_goals = len(goals)
    completed_goals = len([g for g in goals if g["status"] == "COMPLETED"])
    active_goals = len([g for g in goals if g["status"] == "ACTIVE"])
    avg_progress = int(sum(g["progress"] for g in goals) / total_goals) if total_goals else 0
    active_threats = len(threats)

    energy_values = [r["energy_level"] for r in reversed(focus_records)] if focus_records else []
    energy_trend = ""
    if len(energy_values) >= 2:
        recent_avg = sum(energy_values[-3:]) / 3
        earlier_avg = sum(energy_values[:3]) / 3
        if recent_avg > earlier_avg + 5:
            energy_trend = "rising"
        elif recent_avg < earlier_avg - 5:
            energy_trend = "declining"
        else:
            energy_trend = "stable"

    rag_context = ""
    rag_engine = rag.get_engine()
    if rag_engine:
        results = rag_engine.query(
            f"Productivity summary for user with {active_goals} active goals, {active_threats} threats, energy {energy_trend}",
            n_results=4,
        )
        if results:
            rag_context = rag_engine.format_context(results)

    rag_section = (
        "ADDITIONAL HISTORICAL CONTEXT (from vector store):\n"
        f"{rag_context}\n\n"
        "Use this additional context to provide deeper, more personalized insights.\n"
    ) if rag_context else ""

    goals_summary = "; ".join(
        [f"'{g['title']}' ({g['status']}, {g['progress']}% progress, deadline {g['deadline']})" for g in goals]
    )
    threats_summary = "; ".join(
        [f"'{t['name']}' ({t['urgency']} urgency, {t['probability']}% probability)" for t in threats]
    ) if threats else "No active threats"
    energy_summary = ", ".join([str(e) for e in energy_values]) if energy_values else "No data"

    prompt = f"""
    You are the FutureShield AI Strategic Analyst. Generate a {request.period} productivity summary for a high-performer managing complex deadlines.

    Here is the current system state:

    GOALS ({total_goals} total, {completed_goals} completed, {active_goals} active):
    {goals_summary}

    ACTIVE THREATS ({active_threats}):
    {threats_summary}

    FOCUS ENERGY TREND ({energy_trend}):
    Energy levels over the last 8 periods: [{energy_summary}]
    Average progress across all goals: {avg_progress}%

    {rag_section}

    Generate a structured analysis with these exact sections:
    1. "overall_assessment": A 1-2 sentence summary of the user's current productivity state (be direct and motivational).
    2. "productivity_score": An integer 0-100 representing overall productivity health.
    3. "key_insights": An array of 3 specific, data-backed observations about their work patterns.
    4. "top_priority": A single, specific recommended action they should take right now (1 sentence).
    5. "risk_warning": A 1-sentence warning about the biggest current risk to their deadlines.
    6. "energy_verdict": A 1-sentence assessment of their focus energy trend and whether they should push or rest.

    Format your output EXACTLY as a JSON object matching this schema:
    {{
      "overall_assessment": "string",
      "productivity_score": integer,
      "key_insights": ["string", "string", "string"],
      "top_priority": "string",
      "risk_warning": "string",
      "energy_verdict": "string"
    }}
    Do not add markdown formatting. Return raw JSON.
    """

    try:
        response_text = await call_gemini_with_queue(prompt, json_mode=True)
        result = json.loads(response_text)
        return {"status": "success", "period": request.period, "summary": result}
    except Exception as e:
        print("Gemini API error in summary, using fallback:", str(e))

        if energy_trend == "declining":
            energy_verdict = "Your energy levels are trending downward. Consider a strategic recovery break before pushing critical deadlines."
        elif energy_trend == "rising":
            energy_verdict = "Your focus energy is building. Capitalize on this momentum for your most challenging tasks."
        else:
            energy_verdict = "Your energy levels are stable. Maintain your current cadence with scheduled recovery intervals."

        if active_threats > 2:
            risk_warning = f"You have {active_threats} unresolved threats that could cascade into critical deadline failures."
        elif active_threats > 0:
            risk_warning = "One active threat requires attention before it escalates."
        else:
            risk_warning = "No immediate threats detected. Maintain vigilance."

        if avg_progress < 30:
            top_priority = "Focus on completing early-stage milestones to build momentum across your active goals."
        elif avg_progress < 70:
            top_priority = "Push your active goals past the midpoint to reduce deadline risk exposure."
        else:
            top_priority = "Finalize remaining deliverables and conduct pre-deployment reviews."

        insights = []
        if active_goals > 0:
            insights.append(f"You have {active_goals} active goals in progress with an average completion of {avg_progress}%.")
        if completed_goals > 0:
            insights.append(f"You've completed {completed_goals} goal(s). Momentum is building — keep executing.")
        if active_threats > 0:
            insights.append(f"{active_threats} active threat(s) detected. Prioritize resolution to protect your timeline.")
        else:
            insights.append("All threats neutralized. Your operational security is optimal.")
        if len(insights) < 3:
            insights.append(f"Energy trend is {energy_trend}. {'Leverage peak hours for deep work.' if energy_trend != 'declining' else 'Consider adjusting your schedule for better focus.'}")

        return {
            "status": "success",
            "period": request.period,
            "summary": {
                "overall_assessment": f"Your command center shows {active_goals} active missions with {avg_progress}% average completion. {active_threats} threat(s) require attention. Energy levels are {energy_trend}.",
                "productivity_score": max(10, min(95, avg_progress - active_threats * 8 + (10 if energy_trend == "rising" else 0))),
                "key_insights": insights[:3],
                "top_priority": top_priority,
                "risk_warning": risk_warning,
                "energy_verdict": energy_verdict,
            },
        }
