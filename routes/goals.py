"""FutureShield AI — Goals CRUD and AI decomposition endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel
import json

import database
import rag
from routes import call_gemini_with_queue

router = APIRouter(tags=["Goals"])


class GoalCreate(BaseModel):
    title: str
    status: str
    progress: int
    deadline: str


class GoalDecomposeRequest(BaseModel):
    goal_title: str
    target_date: str


@router.post("/api/goals")
def create_goal(goal: GoalCreate) -> dict:
    new_id = database.insert_and_get_id(
        "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
        (goal.title, goal.status, goal.progress, goal.deadline),
    )
    rag_engine = rag.get_engine()
    if rag_engine and new_id:
        rag_engine.index_goal({
            "id": new_id,
            "title": goal.title,
            "status": goal.status,
            "progress": goal.progress,
            "deadline": goal.deadline,
        })
    return {"status": "success", "created_goal": goal.title}


@router.put("/api/goals/{goal_id}")
def update_goal(goal_id: int, progress: int) -> dict:
    database.execute_db("UPDATE goals SET progress = ? WHERE id = ?", (progress, goal_id))
    return {"status": "success", "updated_goal_id": goal_id}


@router.get("/api/goals")
def get_goals(limit: int = 50, offset: int = 0, status: str | None = None) -> dict:
    if status:
        goals = database.query_db(
            "SELECT * FROM goals WHERE status = ? ORDER BY id ASC LIMIT ? OFFSET ?",
            (status, limit, offset),
        )
        total = database.query_db("SELECT COUNT(*) as count FROM goals WHERE status = ?", (status,), one=True)
    else:
        goals = database.query_db(
            "SELECT * FROM goals ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        total = database.query_db("SELECT COUNT(*) as count FROM goals", one=True)
    return {
        "goals": goals,
        "total": total["count"] if total else 0,
        "limit": limit,
        "offset": offset,
    }


@router.post("/api/goals/decompose")
async def decompose_goal(request: GoalDecomposeRequest) -> dict:
    rag_context = ""
    rag_engine = rag.get_engine()
    if rag_engine:
        results = rag_engine.query(
            f"Goal decomposition for: {request.goal_title}",
            n_results=3,
        )
        if results:
            rag_context = rag_engine.format_context(results)

    rag_section = (
        "REFERENCE CONTEXT from similar past activities:\n"
        f"{rag_context}\n\n"
        "Use these as reference for realistic milestones.\n"
    ) if rag_context else ""

    prompt = f"""
    You are the FutureShield Goal Architect. A user wants to achieve the following high-level goal: "{request.goal_title}" by "{request.target_date}".

    {rag_section}

    Decompose this goal into exactly 3 actionable, sequential milestones.
    For each milestone, provide:
    - title (a concise, professional description of the milestone)
    - deadline (a realistic YYYY-MM-DD date between today and the target date)

    Format your output EXACTLY as a JSON object matching this schema:
    {{
      "milestones": [
        {{
          "title": "string",
          "deadline": "YYYY-MM-DD"
        }},
        {{
          "title": "string",
          "deadline": "YYYY-MM-DD"
        }},
        {{
          "title": "string",
          "deadline": "YYYY-MM-DD"
        }}
      ]
    }}
    Do not add markdown formatting. Return raw JSON.
    """

    try:
        response_text = await call_gemini_with_queue(prompt, json_mode=True)
        data = json.loads(response_text)
        milestones = data.get("milestones", [])
    except Exception as e:
        print("Gemini API error in goals decomposition, using fallback:", str(e))
        milestones = [
            {"title": f"Phase 1: Initial Planning & Setup for {request.goal_title}", "deadline": request.target_date},
            {"title": "Phase 2: Core Development & Implementation", "deadline": request.target_date},
            {"title": "Phase 3: Integration, Testing & Deployment", "deadline": request.target_date},
        ]

    created_milestones = []
    for m in milestones:
        new_id = database.insert_and_get_id(
            "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
            (m["title"], "ACTIVE", 0, m["deadline"]),
        )
        if rag_engine and new_id:
            rag_engine.index_goal({
                "id": new_id,
                "title": m["title"],
                "status": "ACTIVE",
                "progress": 0,
                "deadline": m["deadline"],
            })
        created_milestones.append(m["title"])

    return {"status": "success", "milestones": created_milestones}
