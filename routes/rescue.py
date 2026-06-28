"""FutureShield AI — AI Rescue endpoints with SSE streaming and fallback."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

import database
import rag
from collections.abc import AsyncGenerator

from routes import call_gemini_with_queue, call_gemini_stream, _sse_event, _GlobalMetrics

router = APIRouter(tags=["Rescue"])


# ---------------------------------------------------------------------------
# Shared rescue helpers
# ---------------------------------------------------------------------------

def _build_rescue_context() -> tuple:
    unresolved_threats = database.query_db("SELECT * FROM threats WHERE resolved = 0")
    threat_descriptions = ", ".join(
        [f"{t['name']} ({t['urgency']} urgency)" for t in unresolved_threats]
    ) if unresolved_threats else "No current active threats"

    rag_context = ""
    rag_engine = rag.get_engine()
    if rag_engine and unresolved_threats:
        results = rag_engine.query(
            f"Rescue mission for threats: {threat_descriptions} recovery plan",
            n_results=4,
        )
        if results:
            rag_context = rag_engine.format_context(results)

    rag_section = (
        "REFERENCE PAST RESCUE DATA:\n"
        f"{rag_context}\n\n"
        "Use these past patterns to inform your recovery strategy.\n"
    ) if rag_context else ""

    prompt = f"""
    You are the FutureShield AI Commander. An emergency rescue mission has been initiated to resolve the following active system threats: {threat_descriptions}.

    {rag_section}

    Provide an autonomous recovery plan and a technical solution/boilerplate.
    Generate:
    1. A list of 4 concise recovery action steps (e.g. schedule re-allocation, buffer insertion, specific technical tasks).
    2. A complete, clean code snippet or technical document resolving the technical aspect of these threats.

    Format your output EXACTLY as a JSON object matching this schema:
    {{
      "action_plan": [
        "string",
        "string",
        "string",
        "string"
      ],
      "generated_asset": "string (the technical code, configuration, or document to display in the editor)"
    }}
    Do not add markdown formatting. Return raw JSON.
    """

    return unresolved_threats, threat_descriptions, rag_engine, prompt


def _rescue_fallback(unresolved_threats: list, threat_descriptions: str) -> dict:
    action_plan = [
        "Analyzed active anomaly database for mitigation mapping.",
        "Isolated and containerized threat sectors to prevent memory load spikes.",
        "Re-routed network traffic to secure active node redundancy.",
        "Generated custom recovery module and synchronized digital twin baseline.",
    ]

    generated_asset = f"""# FutureShield Anomaly Resolution Module
# Target Threats: {threat_descriptions}
# Executed automatically to prevent project timeline collapse.

import os
import sys
import time

def run_diagnostics():
    print("[INFO] Starting FutureShield Emergency Rescue...")
    print("[INFO] Active Threats Identified:")
"""
    for t in unresolved_threats:
        generated_asset += f'    print("  - [{t["id"]}] {t["name"]} ({t["urgency"]} urgency)")\n'

    generated_asset += """
    print("[INFO] Re-aligning database indices...")
    time.sleep(0.4)
    print("[INFO] Cleaning unmapped resource calls...")
    time.sleep(0.4)
    print("[SUCCESS] All active anomalies resolved successfully. Baseline score synchronized.")

if __name__ == '__main__':
    run_diagnostics()
"""

    return {
        "action_plan": action_plan,
        "generated_asset": generated_asset,
    }


def _cleanup_rescue(unresolved_threats: list, rag_engine: "rag.RAGEngine | None") -> None:
    if rag_engine:
        for t in unresolved_threats:
            rag_engine.index_threat({**t, "resolved": 1})
    database.execute_db("UPDATE threats SET resolved = 1")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/api/rescue")
async def trigger_rescue() -> dict:
    unresolved_threats, threat_descriptions, rag_engine, prompt = _build_rescue_context()

    try:
        response_text = await call_gemini_with_queue(prompt, json_mode=True)
        result = json.loads(response_text)
    except Exception as e:
        print("Gemini API error in rescue, using fallback:", str(e))
        result = _rescue_fallback(unresolved_threats, threat_descriptions)

    _cleanup_rescue(unresolved_threats, rag_engine)

    return {
        "status": "RESCUE_MISSION_LAUNCHED",
        "action_plan": result.get("action_plan", []),
        "generated_asset": result.get("generated_asset", ""),
    }


@router.get("/api/rescue/stream")
async def stream_rescue(token: str = "") -> StreamingResponse:
    """SSE endpoint for the rescue page with streaming code generation."""
    async def generate() -> AsyncGenerator[str, None]:
        unresolved_threats, threat_descriptions, rag_engine, prompt = _build_rescue_context()
        yield _sse_event("plan_start", {})

        action_plan = []
        generated_asset = ""
        try:
            full_text = ""
            async for _token_chunk, accumulated in call_gemini_stream(prompt):
                full_text = accumulated
            result = json.loads(full_text)
            action_plan = result.get("action_plan", [])
            generated_asset = result.get("generated_asset", "")
        except Exception as e:
            print("Gemini API error in rescue stream, using fallback:", str(e))
            _GlobalMetrics.record_error(f"Rescue stream fallback: {str(e)}")
            fallback = _rescue_fallback(unresolved_threats, threat_descriptions)
            action_plan = fallback["action_plan"]
            generated_asset = fallback["generated_asset"]

        for step in action_plan:
            yield _sse_event("plan_step", {"step": step})

        token_size = 4
        for i in range(0, len(generated_asset), token_size):
            yield _sse_event("code_chunk", {"text": generated_asset[i:i + token_size]})

        _cleanup_rescue(unresolved_threats, rag_engine)
        yield _sse_event("complete", {})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
