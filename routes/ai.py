"""FutureShield AI — AI Status, Metrics, and Streaming endpoints."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
import time
import httpx

from collections.abc import AsyncGenerator

from routes import (
    GEMINI_API_KEY,
    _ai_queue,
    _ai_cache,
    _GlobalMetrics,
    _sse_event,
)

router = APIRouter(tags=["AI"])


@router.get("/api/ai/status")
def get_ai_status() -> dict:
    queue_status = _ai_queue.get_status()
    metrics = _GlobalMetrics.get_summary()
    return {
        **queue_status,
        "metrics": metrics,
        "cache_size": len(_ai_cache._cache),
    }


@router.get("/api/ai/metrics")
def get_ai_metrics() -> dict:
    return _GlobalMetrics.get_summary()


@router.post("/api/ai/cache/clear")
def clear_ai_cache() -> dict:
    _ai_cache.clear()
    return {"status": "cache_cleared"}


@router.get("/api/ai/stream")
async def stream_ai_generate(prompt: str, token: str = "") -> StreamingResponse:
    """Generic SSE endpoint that streams AI-generated text from Gemini."""
    async def generate() -> AsyncGenerator[str, None]:
        if not GEMINI_API_KEY:
            yield _sse_event("error", {"message": "Gemini API key not configured"})
            return

        if not _ai_queue.can_call():
            yield _sse_event("error", {"message": "AI rate limit reached. Please wait."})
            return

        _ai_queue.record_call()
        start_time = time.time()

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse&key={GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            req_data = {"contents": [{"parts": [{"text": prompt}]}]}

            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, headers=headers, json=req_data) as resp:
                    if resp.status_code != 200:
                        yield _sse_event("error", {"message": f"Gemini API error: {resp.status_code}"})
                        return

                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        if not line.startswith("data: "):
                            continue
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload)
                            candidates = chunk.get("candidates", [])
                            if not candidates:
                                continue
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                text = part.get("text", "")
                                if text:
                                    yield _sse_event("chunk", {"text": text})
                        except json.JSONDecodeError:
                            continue

            elapsed_ms = round((time.time() - start_time) * 1000, 1)
            _GlobalMetrics.record_call(elapsed_ms)
            yield _sse_event("complete", {})

        except Exception as e:
            _GlobalMetrics.record_error(f"Stream error: {str(e)}")
            yield _sse_event("error", {"message": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
