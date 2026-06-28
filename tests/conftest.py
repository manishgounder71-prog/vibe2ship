"""pytest fixtures for FutureShield AI tests.

Provides shared fixtures used across test modules:
- use_test_database: isolated temp database for each test (SQLite)
- engine: fresh RAGEngine instance
- populated_engine: RAGEngine with sample goals, threats, and focus data
- api_client: authenticated FastAPI TestClient
- rag_engine: module-level RAG engine from main app startup
"""
import pytest
import tempfile
import os
import sys

# Ensure project root is on sys.path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ---------------------------------------------------------------------------
# Database isolation (SQLite for tests)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def use_test_database(request, monkeypatch):
    """Override the database path to use a temporary file for test isolation.

    Uses SQLite for unit/integration tests. PostgreSQL tests (marked @pgsql)
    use the FUTURESHIELD_DB_URL environment variable instead.

    Skips the override for e2e tests (they start their own server with an
    isolated database via the FUTURESHIELD_DB_PATH environment variable).
    """
    # Skip for e2e tests — they have their own session-scoped server + DB
    if request.node.get_closest_marker("pgsql") or request.node.get_closest_marker("e2e"):
        yield
        return

    import database
    # Create a temporary file for the test database
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setattr(database, "_DB_PATH", tmp.name)
    monkeypatch.setattr(database, "DB_URL", "")
    monkeypatch.setattr(database, "_use_postgres", False)
    # Re-initialize the database with fresh seed data
    database.init_db()
    yield
    # Cleanup: close all connections and delete temp file
    try:
        os.unlink(tmp.name)
    except (OSError, PermissionError):
        pass


# ---------------------------------------------------------------------------
# RAG engine fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    """Create a fresh RAGEngine instance initialized with the pure-Python fallback."""
    import rag
    from rag import RAGEngine
    e = RAGEngine()
    e.initialize()
    return e


@pytest.fixture
def populated_engine():
    """Create a RAGEngine pre-populated with sample goals, threats, and focus data."""
    import rag
    from rag import RAGEngine
    e = RAGEngine()
    e.initialize()
    # Goals
    e.index_goal({"id": 1, "title": "Project Phoenix Core Integration",
                  "status": "ACTIVE", "progress": 75, "deadline": "2026-06-27"})
    e.index_goal({"id": 2, "title": "Digital Twin Synchronization",
                  "status": "PENDING", "progress": 0, "deadline": "2026-06-30"})
    # Threats
    e.index_threat({"id": "XR-1", "name": "Quantum Decoherence Gap",
                    "urgency": "HIGH", "probability": 88,
                    "success_rate": "12.4%", "type": "critical"})
    e.index_threat({"id": "TR-2", "name": "Latency Spike",
                    "urgency": "MED", "probability": 42,
                    "success_rate": "65.1%", "type": "warning"})
    # Focus session
    e.index_focus_session({"id": 1, "session_type": "deep_work",
                           "duration_minutes": 25, "actual_duration_seconds": 1500,
                           "energy_rating": 8, "status": "completed"})
    # Focus record
    e.index_focus_record({"id": 1, "energy_level": 85, "timestamp": "2026-06-25"})
    return e


# ---------------------------------------------------------------------------
# API client fixture (for integration tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    """Create an authenticated FastAPI TestClient.

    The app's startup event fires, so the module-level RAG engine and
    database are initialized.
    """
    import warnings
    from fastapi.testclient import TestClient
    from main import app
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="httpx")
    client = TestClient(app=app)
    client.headers["Authorization"] = "Bearer shield-admin-pass"
    return client


# ---------------------------------------------------------------------------
# Module-level RAG engine fixture (for integration tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def rag_engine():
    """Get or initialize the module-level RAG engine.

    This is the same engine initialized by main.py's startup event.
    Falls back to direct initialization if the event hasn't fired yet
    (e.g., when running tests in isolation).
    """
    import rag
    engine = rag.get_engine()
    if engine is None:
        engine = rag.init_engine()
    return engine
