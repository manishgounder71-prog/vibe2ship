"""
FutureShield AI — Shared infrastructure for route modules.

Holds the global AI queue, cache, metrics, and the core Gemini call functions
that are shared across all API route modules.
"""

import os
import json
import time
import asyncio
import threading

import httpx
from collections.abc import AsyncGenerator

from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# API keys & tokens
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_ACCESS_TOKEN = os.getenv("API_ACCESS_TOKEN", "shield-admin-pass")


# ---------------------------------------------------------------------------
# Core Gemini caller
# ---------------------------------------------------------------------------

class _GlobalMetrics:
    """Module-level AI API usage metrics (shared across all routes)."""
    _lock = threading.Lock()
    total_calls: int = 0
    cache_hits: int = 0
    total_errors: int = 0
    total_response_time_ms: float = 0.0
    last_call_time: float | None = None
    last_error_time: float | None = None
    last_error_message: str | None = None

    @classmethod
    def record_call(cls, response_time_ms: float) -> None:
        with cls._lock:
            cls.total_calls += 1
            cls.total_response_time_ms += response_time_ms
            cls.last_call_time = time.time()

    @classmethod
    def record_cache_hit(cls) -> None:
        with cls._lock:
            cls.cache_hits += 1

    @classmethod
    def record_error(cls, message: str) -> None:
        with cls._lock:
            cls.total_errors += 1
            cls.last_error_time = time.time()
            cls.last_error_message = message

    @classmethod
    def get_summary(cls) -> dict:
        with cls._lock:
            avg_time = 0.0
            if cls.total_calls > 0:
                avg_time = round(cls.total_response_time_ms / cls.total_calls, 1)
            return {
                "total_calls": cls.total_calls,
                "cache_hits": cls.cache_hits,
                "total_errors": cls.total_errors,
                "average_response_time_ms": avg_time,
                "last_call_time": cls.last_call_time,
                "last_error_time": cls.last_error_time,
                "last_error_message": cls.last_error_message,
            }


async def call_gemini(prompt: str, json_mode: bool = False) -> str:
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured in .env file.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    data: dict[str, object] = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    if json_mode:
        data["generationConfig"] = {"responseMimeType": "application/json"}

    max_retries = 3
    base_delay = 1.0
    last_error = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                response = await client.post(url, headers=headers, json=data)
                elapsed_ms = round((time.time() - start_time) * 1000, 1)

                if response.status_code == 200:
                    _GlobalMetrics.record_call(elapsed_ms)
                    res_json = response.json()
                    try:
                        text: str = res_json["candidates"][0]["content"]["parts"][0]["text"]
                        return text
                    except (KeyError, IndexError, TypeError) as e:
                        _GlobalMetrics.record_error(f"Unexpected response structure: {response.text[:200]}")
                        raise HTTPException(status_code=500, detail=f"Unexpected response structure from Gemini: {response.text}")

                if response.status_code in (400, 401, 403):
                    _GlobalMetrics.record_error(f"Gemini auth/bad request: {response.status_code}")
                    raise HTTPException(status_code=500, detail=f"Gemini API returned error {response.status_code}: {response.text}")

                if response.status_code in (429, 500, 502, 503):
                    _GlobalMetrics.record_error(f"Gemini retryable error {response.status_code}")
                    last_error = f"Gemini API returned status {response.status_code}"
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"[AI] Retry {attempt + 1}/{max_retries} after {delay:.1f}s (status {response.status_code})")
                        await asyncio.sleep(delay)
                        continue
                    raise HTTPException(status_code=502, detail=f"Gemini API unavailable after {max_retries} retries.")

                _GlobalMetrics.record_error(f"Gemini unexpected status: {response.status_code}")
                raise HTTPException(status_code=500, detail=f"Gemini API returned error {response.status_code}: {response.text}")

            except httpx.RequestError as e:
                last_error = str(e)
                _GlobalMetrics.record_error(f"Network error: {str(e)}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"[AI] Network retry {attempt + 1}/{max_retries} after {delay:.1f}s")
                    await asyncio.sleep(delay)
                    continue
                raise HTTPException(status_code=500, detail=f"Network error calling Gemini after {max_retries} retries: {str(e)}")

    raise HTTPException(status_code=500, detail=f"Gemini API call failed after all retries: {last_error}")


# ---------------------------------------------------------------------------
# AI Cache
# ---------------------------------------------------------------------------

class AICache:
    def __init__(self, ttl_seconds: int = 300):
        self._cache: dict[str, dict[str, object]] = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, prompt: str) -> str | None:
        key = prompt.strip()
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - (entry["time"] if isinstance(entry["time"], (int, float)) else 0) < self._ttl:
                    result = entry.get("result")
                    return str(result) if result is not None else None
                del self._cache[key]
        return None

    def set(self, prompt: str, result: str) -> None:
        key = prompt.strip()
        with self._lock:
            self._cache[key] = {"result": result, "time": time.time()}

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


# ---------------------------------------------------------------------------
# AI Queue (rate-limit awareness)
# ---------------------------------------------------------------------------

class AIQueue:
    def __init__(self, max_per_minute: int = 20) -> None:
        self.max_per_minute = max_per_minute
        self.call_timestamps: list[float] = []
        self.lock = threading.Lock()
        self._status: str = "ready"
        self._last_error: int | None = None
        self._cooldown_until: float = 0.0

    def can_call(self) -> bool:
        now = time.time()
        with self.lock:
            self.call_timestamps = [t for t in self.call_timestamps if now - t < 60]
            return len(self.call_timestamps) < self.max_per_minute

    def record_call(self) -> None:
        with self.lock:
            self.call_timestamps.append(time.time())

    def record_error(self, status_code: int) -> None:
        if status_code == 429:
            self._status = "limited"
            self._cooldown_until = time.time() + 60
        elif status_code >= 500:
            self._status = "limited"
            self._cooldown_until = time.time() + 30
        self._last_error = status_code

    def get_status(self) -> dict:
        now = time.time()
        if self._cooldown_until > now:
            remaining = int(self._cooldown_until - now)
            return {
                "status": "limited",
                "cooldown_seconds": remaining,
                "key_configured": bool(GEMINI_API_KEY),
                "requests_this_minute": len([t for t in self.call_timestamps if now - t < 60]),
            }
        if not GEMINI_API_KEY:
            return {
                "status": "offline",
                "key_configured": False,
                "requests_this_minute": 0,
                "message": "Gemini API key not configured. Add GEMINI_API_KEY to .env file.",
            }
        can = self.can_call()
        return {
            "status": "ready" if can else "limited",
            "key_configured": True,
            "requests_this_minute": len([t for t in self.call_timestamps if now - t < 60]),
            "max_per_minute": self.max_per_minute,
        }


# Global singletons
_ai_queue = AIQueue()
_ai_cache = AICache(ttl_seconds=300)


# ---------------------------------------------------------------------------
# Queue-aware wrapper
# ---------------------------------------------------------------------------

async def call_gemini_with_queue(prompt: str, json_mode: bool = False) -> str:
    """Wrapper for call_gemini that respects rate limits and caches responses."""
    if not json_mode:
        cached = _ai_cache.get(prompt)
        if cached is not None:
            _GlobalMetrics.record_cache_hit()
            return cached

    if not _ai_queue.can_call():
        raise HTTPException(
            status_code=429,
            detail="AI rate limit reached. Please wait a moment before trying again.",
        )
    _ai_queue.record_call()
    try:
        result = await call_gemini(prompt, json_mode=json_mode)
        if not json_mode:
            _ai_cache.set(prompt, result)
        return result
    except HTTPException as e:
        if e.status_code in (429, 500, 502, 503):
            _ai_queue.record_error(e.status_code)
        raise


# ---------------------------------------------------------------------------
# SSE event formatter
# ---------------------------------------------------------------------------

def _sse_event(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# Gemini streaming helper
# ---------------------------------------------------------------------------

async def call_gemini_stream(prompt: str) -> "AsyncGenerator[tuple[str, str], None]":
    """Call Gemini with streaming (streamGenerateContent).
    Yields (text_chunk, accumulated_text) tuples as tokens arrive.
    Uses httpx.AsyncClient for non-blocking streaming.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured in .env file.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse&key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, headers=headers, json=data) as response:
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Gemini streaming error: {response.status_code}")

            accumulated = ""
            async for line in response.aiter_lines():
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
                            accumulated += text
                            yield (text, accumulated)
                except json.JSONDecodeError:
                    continue
