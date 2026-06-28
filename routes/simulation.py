"""FutureShield AI — Future Simulation endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel
import json

import database
import rag
from routes import call_gemini_with_queue

router = APIRouter(tags=["Simulation"])


class SimulationRequest(BaseModel):
    action: str


@router.post("/api/simulate")
async def run_simulation(request: SimulationRequest) -> dict:
    rag_context = ""
    rag_engine = rag.get_engine()
    if rag_engine:
        results = rag_engine.query(
            f"Simulation context for action: {request.action} current goals threats energy",
            n_results=5,
        )
        if results:
            rag_context = rag_engine.format_context(results)

    rag_section = (
        "CURRENT SYSTEM STATE (retrieved from vector store):\n"
        f"{rag_context}\n\n"
        "Use this real user data to make your simulation more accurate.\n"
    ) if rag_context else ""

    prompt = f"""
    You are the FutureShield Failure Prevention AI agent.
    The user is considering the following action: "{request.action}"

    {rag_section}

    Analyze this action and project three branching future timelines:
    1. "future_a": Current path based directly on this action.
    2. "future_b": An alternative recommended path that optimizes cognitive load, focus, and deadline compliance.
    3. "future_c": A worst-case scenario that triggers an automatic AI Rescue intervention.

    For each future, calculate:
    - status (a short 2-4 word description of the outcome state)
    - success_probability (integer 0-100)
    - failure_probability (integer 0-100)
    - stress_index (integer 0-100)
    - deadline_risk (either "LOW", "MEDIUM", or "HIGH")

    Format your output EXACTLY as a JSON object matching this schema:
    {{
      "future_a": {{
        "status": "string",
        "success_probability": integer,
        "failure_probability": integer,
        "stress_index": integer,
        "deadline_risk": "LOW" | "MEDIUM" | "HIGH"
      }},
      "future_b": {{
        "status": "string",
        "success_probability": integer,
        "failure_probability": integer,
        "stress_index": integer,
        "deadline_risk": "LOW" | "MEDIUM" | "HIGH"
      }},
      "future_c": {{
        "status": "string",
        "success_probability": integer,
        "failure_probability": integer,
        "stress_index": integer,
        "deadline_risk": "LOW" | "MEDIUM" | "HIGH"
      }}
    }}
    Do not add any markdown formatting. Return raw JSON.
    """

    try:
        response_text = await call_gemini_with_queue(prompt, json_mode=True)
        futures: dict = json.loads(response_text)
        return futures
    except Exception as e:
        print("Gemini API error in simulation, using data-driven fallback:", str(e))
        goals_data = database.query_db("SELECT progress, deadline FROM goals")
        threat_count = len(database.query_db("SELECT * FROM threats WHERE resolved = 0"))

        avg_progress = sum(g["progress"] for g in goals_data) / len(goals_data) if goals_data else 50
        risk_multiplier = 1.0 + (threat_count * 0.15) - (avg_progress / 500)

        has_skip_keywords = any(
            w in request.action.lower()
            for w in ["skip", "delay", "sleep", "postpone", "cancel", "ignore", "miss"]
        )

        if has_skip_keywords:
            base_success, base_stress, risk_label = 30, 85, "HIGH"
        elif avg_progress < 30:
            base_success, base_stress, risk_label = 55, 60, "MEDIUM"
        else:
            base_success, base_stress, risk_label = 80, 35, "LOW"

        success_a = max(5, min(95, int(base_success * risk_multiplier)))
        stress_a = max(5, min(95, int(base_stress / risk_multiplier)))
        fail_a = 100 - success_a

        return {
            "future_a": {
                "status": "Critical delay & workload spike" if has_skip_keywords else "Nominal progression",
                "success_probability": success_a,
                "failure_probability": fail_a,
                "stress_index": stress_a,
                "deadline_risk": risk_label,
            },
            "future_b": {
                "status": "Realigned priorities",
                "success_probability": min(95, success_a + 25),
                "failure_probability": max(5, fail_a - 25),
                "stress_index": max(10, stress_a - 25),
                "deadline_risk": "MEDIUM" if risk_label == "HIGH" else "LOW",
            },
            "future_c": {
                "status": "AI Co-pilot active rescue",
                "success_probability": 92,
                "failure_probability": 8,
                "stress_index": 15,
                "deadline_risk": "LOW",
            },
        }
