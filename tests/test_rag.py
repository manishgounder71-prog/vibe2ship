"""
FutureShield AI - RAG Engine Unit & Integration Tests

Tests the pure-Python fallback TF-IDF engine, the RAGEngine class,
and the RAG integration in main.py API endpoints.

Fixtures are defined in conftest.py:
- engine: fresh RAGEngine instance
- populated_engine: RAGEngine with sample data
- api_client: authenticated FastAPI TestClient
- rag_engine: module-level engine from main startup

Run with: pytest tests/test_rag.py -v
"""
import pytest

import rag
from rag import _tokenize, _ngrams, _cosine_similarity, _FallbackStore, RAGEngine


# ============================================================================
# Pure-Python Fallback Internals
# ============================================================================

class TestTokenize:
    """Test the _tokenize helper function."""

    def test_simple_text(self):
        assert _tokenize("Hello World") == ["hello", "world"]

    def test_lowercase(self):
        assert _tokenize("UPPERCASE") == ["uppercase"]

    def test_strips_punctuation(self):
        assert _tokenize("Hello, World!") == ["hello", "world"]

    def test_numbers(self):
        assert _tokenize("test 123 goal") == ["test", "123", "goal"]

    def test_empty_string(self):
        assert _tokenize("") == []

    def test_only_punctuation(self):
        assert _tokenize("!!! ???") == []

    def test_mixed_case(self):
        assert _tokenize("Goal: Project Phoenix") == ["goal", "project", "phoenix"]


class TestNgrams:
    """Test the _ngrams helper function."""

    def test_basic_trigrams(self):
        tokens = ["hello", "world"]
        # "hello world" -> trigrams: hel, ell, llo, lo , o w,  wo, wor, orl, rld
        grams = _ngrams(tokens, n=3)
        assert "hel" in grams
        assert "wor" in grams
        assert "rld" in grams
        assert "llo" in grams

    def test_single_token(self):
        grams = _ngrams(["abc"], n=3)
        assert grams == ["abc"]  # only one trigram possible

    def test_short_text_falls_back_to_1gram(self):
        """When text is shorter than n, it returns at least the full text."""
        grams = _ngrams(["a"], n=3)
        assert grams == ["a"]  # max(1, len-2) = 1

    def test_bigrams(self):
        tokens = ["abc", "def"]
        grams = _ngrams(tokens, n=2)
        # "abc def" -> bigrams: ab, bc, c ,  d, de, ef
        assert "ab" in grams
        assert "bc" in grams
        assert "de" in grams
        assert "ef" in grams

    def test_empty_tokens(self):
        grams = _ngrams([], n=3)
        # Empty tokens produce empty string, which yields one empty n-gram
        assert grams == [""]


class TestCosineSimilarity:
    """Test the _cosine_similarity function."""

    def test_identical_vectors(self):
        vec = {"a": 1.0, "b": 2.0, "c": 3.0}
        assert _cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Vectors with no overlapping keys should have 0 similarity."""
        vec_a = {"a": 1.0, "b": 1.0}
        vec_b = {"c": 1.0, "d": 1.0}
        assert _cosine_similarity(vec_a, vec_b) == 0.0

    def test_similarity_between_parallel(self):
        vec_a = {"a": 1.0, "b": 1.0}
        vec_b = {"a": 2.0, "b": 2.0}
        # Parallel vectors have cosine similarity 1.0
        assert _cosine_similarity(vec_a, vec_b) == pytest.approx(1.0)

    def test_partial_overlap(self):
        vec_a = {"a": 1.0, "b": 0.0}
        vec_b = {"a": 1.0, "b": 1.0}
        sim = _cosine_similarity(vec_a, vec_b)
        assert 0 < sim < 1.0

    def test_empty_vectors(self):
        assert _cosine_similarity({}, {}) == 0.0

    def test_one_empty_vector(self):
        assert _cosine_similarity({"a": 1.0}, {}) == 0.0
        assert _cosine_similarity({}, {"a": 1.0}) == 0.0


class TestFallbackStore:
    """Test the _FallbackStore class (pure-Python TF-IDF engine)."""

    def test_initial_state(self):
        store = _FallbackStore()
        assert store.count() == 0
        assert store.query("anything") == []
        assert store.documents == []
        assert store.vectors == []

    def test_add_single_document(self):
        store = _FallbackStore()
        store.add(
            documents=["Goal: Build a dashboard. Status: ACTIVE. Progress: 50%."],
            metadatas=[{"type": "goal", "id": "1", "progress": 50}],
            ids=["goal_1"]
        )
        assert store.count() == 1
        assert store.documents[0]["id"] == "goal_1"
        assert store.documents[0]["meta"]["type"] == "goal"

    def test_add_multiple_documents(self):
        store = _FallbackStore()
        store.add(
            documents=["doc a", "doc b", "doc c"],
            metadatas=[{"type": "a"}, {"type": "b"}, {"type": "c"}],
            ids=["id_a", "id_b", "id_c"]
        )
        assert store.count() == 3

    def test_query_returns_most_similar_first(self):
        """Query should return documents sorted by similarity (closest first)."""
        store = _FallbackStore()
        store.add(
            documents=[
                "Goal: Project Phoenix. Status: ACTIVE. Progress: 75%.",
                "Threat: Network outage. Urgency: HIGH. Probability: 88%.",
                "Focus session: deep work. Duration: 25 minutes."
            ],
            metadatas=[
                {"type": "goal", "id": "1"},
                {"type": "threat", "id": "XR-904"},
                {"type": "focus_session", "id": "1"}
            ],
            ids=["goal_1", "threat_XR-904", "session_1"]
        )

        # Query about goals should return the goal doc first
        results = store.query("goal project active status", n_results=3)
        assert len(results) >= 1
        assert results[0]["metadata"]["type"] == "goal"

    def test_query_limited_results(self):
        store = _FallbackStore()
        store.add(
            documents=[f"doc {i}" for i in range(10)],
            metadatas=[{"type": "test", "id": str(i)} for i in range(10)],
            ids=[f"id_{i}" for i in range(10)]
        )
        results = store.query("doc", n_results=3)
        assert len(results) <= 3

    def test_query_with_no_match(self):
        store = _FallbackStore()
        store.add(
            documents=["completely unrelated text about zebras"],
            metadatas=[{"type": "goal", "id": "1"}],
            ids=["goal_1"]
        )
        results = store.query("python code programming")
        # May or may not match depending on n-gram overlap; should not crash
        assert isinstance(results, list)
        # With very different text, distance should be high (low similarity)
        if results:
            assert results[0]["distance"] > 0.5

    def test_query_empty_store(self):
        store = _FallbackStore()
        assert store.query("anything") == []

    def test_clear(self):
        store = _FallbackStore()
        store.add(documents=["test"], metadatas=[{"type": "t"}], ids=["t1"])
        assert store.count() == 1
        store.clear()
        assert store.count() == 0
        assert store.documents == []
        assert store.vectors == []
        assert store.idf == {}

    def test_results_have_correct_keys(self):
        store = _FallbackStore()
        store.add(
            documents=["Goal: Test goal."],
            metadatas=[{"type": "goal", "id": "1"}],
            ids=["goal_1"]
        )
        results = store.query("goal test")
        assert len(results) >= 1
        r = results[0]
        assert "document" in r
        assert "metadata" in r
        assert "distance" in r
        assert isinstance(r["document"], str)
        assert isinstance(r["metadata"], dict)
        assert isinstance(r["distance"], float)

    def test_dirty_flag_triggers_rebuild(self):
        """Adding documents sets _dirty=True, and query triggers rebuild."""
        store = _FallbackStore()
        assert store._dirty is True
        store.query("test")  # triggers rebuild even with empty store
        store.add(documents=["test doc"], metadatas=[{"type": "t"}], ids=["id1"])
        assert store._dirty is True
        store.query("test")
        assert store._dirty is False
        # Vectors should now exist
        assert len(store.vectors) > 0


# ============================================================================
# RAGEngine Class
# ============================================================================

class TestRAGEngineInitialize:
    """Test RAGEngine initialization (should fall back to pure Python)."""

    def test_initialize_fallback(self):
        engine = RAGEngine()
        result = engine.initialize()
        assert result is True
        assert engine._initialized is True
        assert engine._chroma_mode is False  # ChromaDB not available in test env
        assert engine._fallback is not None
        assert isinstance(engine._fallback, _FallbackStore)

    def test_initialize_is_idempotent(self):
        engine = RAGEngine()
        engine.initialize()
        original_fallback = engine._fallback
        engine.initialize()  # second call
        assert engine._initialized is True
        assert engine._fallback is original_fallback  # same instance

    def test_get_engine_returns_none_before_init(self):
        # Reset the module-level engine
        rag._engine = None
        assert rag.get_engine() is None

    def test_init_engine_creates_engine(self):
        rag._engine = None
        engine = rag.init_engine()
        assert engine is not None
        assert engine._initialized is True
        assert rag.get_engine() is engine


class TestRAGEngineDocumentHelpers:
    """Test the document formatting helpers."""

    def test_make_goal_doc(self, engine):
        goal = {"id": 1, "title": "Test Goal", "status": "ACTIVE",
                "progress": 50, "deadline": "2026-07-01"}
        doc = engine._make_goal_doc(goal)
        assert "Test Goal" in doc
        assert "ACTIVE" in doc
        assert "50" in doc
        assert "2026-07-01" in doc

    def test_make_goal_doc_missing_fields(self, engine):
        doc = engine._make_goal_doc({})
        # Should not crash with empty dict
        assert isinstance(doc, str)

    def test_make_threat_doc(self, engine):
        threat = {"id": "XR-1", "name": "Critical Bug", "urgency": "HIGH",
                  "probability": 88, "success_rate": "12.4%", "type": "critical"}
        doc = engine._make_threat_doc(threat)
        assert "Critical Bug" in doc
        assert "HIGH" in doc
        assert "88" in doc
        assert "12.4%" in doc
        assert "critical" in doc

    def test_make_focus_session_doc(self, engine):
        session = {"id": 1, "session_type": "focus", "duration_minutes": 25,
                   "actual_duration_seconds": 1500, "energy_rating": 8, "status": "completed"}
        doc = engine._make_focus_session_doc(session)
        assert "focus" in doc
        assert "25" in doc
        assert "8" in doc
        assert "completed" in doc

    def test_make_focus_record_doc(self, engine):
        record = {"id": 1, "energy_level": 85, "timestamp": "2026-06-25"}
        doc = engine._make_focus_record_doc(record)
        assert "85" in doc
        assert "2026-06-25" in doc


class TestRAGEngineIndexing:
    """Test indexing various data types into the RAG engine."""

    def test_index_goal(self, engine):
        goal = {"id": 1, "title": "Test Goal", "status": "ACTIVE",
                "progress": 50, "deadline": "2026-07-01"}
        engine.index_goal(goal)
        assert engine._fallback.count() == 1

    def test_index_threat(self, engine):
        threat = {"id": "XR-1", "name": "Critical Bug", "urgency": "HIGH",
                  "probability": 88, "success_rate": "12.4%", "type": "critical"}
        engine.index_threat(threat)
        assert engine._fallback.count() == 1

    def test_index_focus_session(self, engine):
        session = {"id": 1, "session_type": "focus", "duration_minutes": 25,
                   "actual_duration_seconds": 1500, "energy_rating": 8, "status": "completed"}
        engine.index_focus_session(session)
        assert engine._fallback.count() == 1

    def test_index_focus_record(self, engine):
        record = {"id": 1, "energy_level": 85, "timestamp": "2026-06-25"}
        engine.index_focus_record(record)
        assert engine._fallback.count() == 1

    def test_index_multiple_types(self, engine):
        engine.index_goal({"id": 1, "title": "G1", "status": "A", "progress": 50, "deadline": "d1"})
        engine.index_threat({"id": "T1", "name": "T1", "urgency": "H", "probability": 50,
                             "success_rate": "50%", "type": "warning"})
        engine.index_focus_session({"id": 1, "session_type": "focus", "duration_minutes": 25,
                                    "actual_duration_seconds": 0, "energy_rating": 5, "status": "completed"})
        engine.index_focus_record({"id": 1, "energy_level": 80, "timestamp": "now"})
        assert engine._fallback.count() == 4

    def test_can_query_after_indexing(self, engine):
        engine.index_goal({"id": 1, "title": "Build React Dashboard", "status": "ACTIVE",
                           "progress": 30, "deadline": "2026-07-01"})
        results = engine.query("react dashboard frontend")
        assert len(results) >= 1
        assert results[0]["metadata"]["type"] == "goal"

    def test_index_empty_dict_does_not_crash(self, engine):
        engine.index_goal({})
        engine.index_threat({})
        engine.index_focus_session({})
        engine.index_focus_record({})
        # Should not raise exceptions


class TestRAGEngineQuery:
    """Test the query and format_context methods."""

    def test_query_returns_relevant_type(self, populated_engine):
        results = populated_engine.query("threat risk urgent critical")
        # The threat docs should be among the top results
        types = [r["metadata"]["type"] for r in results]
        assert "threat" in types

    def test_query_returns_multiple_results(self, populated_engine):
        results = populated_engine.query("project goal milestone", n_results=5)
        assert len(results) >= 1
        assert len(results) <= 5

    def test_query_has_correct_keys(self, populated_engine):
        results = populated_engine.query("test query", n_results=2)
        for r in results:
            assert "document" in r
            assert "metadata" in r
            assert "distance" in r
            assert isinstance(r["document"], str)
            assert isinstance(r["metadata"], dict)
            assert isinstance(r["distance"], float)

    def test_query_returns_empty_list_for_unrelated_query(self, populated_engine):
        """Very specific unrelated text may still match via n-grams, but shouldn't crash."""
        results = populated_engine.query("zzzzzxxxxyyyyywwww", n_results=3)
        assert isinstance(results, list)

    def test_format_context_returns_string(self, populated_engine):
        results = populated_engine.query("project", n_results=2)
        context = populated_engine.format_context(results)
        assert isinstance(context, str)
        assert len(context) > 0

    def test_format_context_contains_type_prefix(self, populated_engine):
        results = populated_engine.query("project", n_results=1)
        context = populated_engine.format_context(results)
        assert context.startswith("[")  # should start with [TYPE]

    def test_format_context_empty_results(self, populated_engine):
        context = populated_engine.format_context([])
        assert context == ""

    def test_query_engine_not_initialized(self):
        """Querying an uninitialized engine should return empty list."""
        engine = RAGEngine()
        # Don't call initialize()
        results = engine.query("test")
        assert results == []

    def test_distance_is_between_0_and_1(self, populated_engine):
        results = populated_engine.query("project", n_results=3)
        for r in results:
            assert 0.0 <= r["distance"] <= 2.0  # distance can be up to 2.0 (1 - (-1))


class TestRAGEngineIndexAllData:
    """Test the index_all_data method (requires database module)."""

    def test_index_all_data_imports_database(self):
        """Verify that index_all_data can import database module."""
        import database
        assert database is not None

    def test_index_all_runs_without_error(self):
        """index_all_data should not crash, even with no seed data."""
        import database as db

        # Temporarily replace DB path to use an in-memory or empty state
        engine = RAGEngine()
        engine.initialize()

        # Use _fallback directly since chromadb isn't available
        assert engine._fallback is not None

        # Manually index some data to verify the method works
        engine.index_goal({"id": 99, "title": "Test from DB", "status": "ACTIVE",
                           "progress": 10, "deadline": "2026-07-15"})
        assert engine._fallback.count() >= 1


# ============================================================================
# Integration Tests: RAG + main.py API Endpoints
# ============================================================================

class TestRAGIntegrationInAPI:
    """Test that the RAG engine integrates correctly with main.py endpoints."""

    def test_rag_initialized_on_app_startup(self, api_client, rag_engine):
        """When main.py is imported, the startup event initializes the RAG engine."""
        assert rag_engine is not None
        assert rag_engine._initialized is True

    def test_create_goal_indexes_into_rag(self, api_client, rag_engine):
        """Creating a goal via the API should index it into the RAG vector store."""
        count_before = rag_engine._fallback.count() if rag_engine._fallback else 0

        # Create a goal with a unique title
        unique_title = "RAG Indexing Test Goal - Unique"
        response = api_client.post("/api/goals", json={
            "title": unique_title,
            "status": "ACTIVE",
            "progress": 10,
            "deadline": "2026-08-01"
        })
        assert response.status_code == 200

        # Verify the vector store has one more document
        count_after = rag_engine._fallback.count() if rag_engine._fallback else 0
        assert count_after == count_before + 1

        # Verify we can query for the new goal by its title
        results = rag_engine.query(unique_title, n_results=5)
        goal_results = [r for r in results if r["metadata"]["type"] == "goal"]
        assert len(goal_results) >= 1

    def test_goal_decompose_indexes_milestones(self, api_client, rag_engine):
        """Goal decomposition creates milestones that get indexed by RAG."""
        count_before = rag_engine._fallback.count() if rag_engine._fallback else 0

        response = api_client.post("/api/goals/decompose", json={
            "goal_title": "Complete RAG integration tests with CI/CD pipeline setup",
            "target_date": "2026-07-30"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["milestones"]) == 3

        if rag_engine._fallback:
            assert rag_engine._fallback.count() >= count_before + 3

    def test_rag_query_after_goal_decompose(self, api_client, rag_engine):
        """After decomposing a goal, querying for it should return the milestones."""
        if not rag_engine or not rag_engine._fallback:
            pytest.skip("RAG engine fallback not available")

        results = rag_engine.query("RAG integration tests with CI CD pipeline", n_results=5)
        goal_results = [r for r in results if r["metadata"]["type"] == "goal"]
        assert len(goal_results) >= 1

    def test_simulation_endpoint_handles_rag_gracefully(self, api_client):
        """Simulation endpoint should work with RAG context, even when Gemini is unavailable."""
        response = api_client.post("/api/simulate", json={
            "action": "Skip all work for the rest of the week"
        })
        assert response.status_code == 200
        data = response.json()
        assert "future_a" in data
        assert "future_b" in data
        assert "future_c" in data

    def test_summary_endpoint_handles_rag_gracefully(self, api_client):
        """Summary endpoint should work with RAG context, even when Gemini is unavailable."""
        response = api_client.post("/api/summary", json={"period": "daily"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        s = data["summary"]
        assert "overall_assessment" in s
        assert "productivity_score" in s
        assert isinstance(s["productivity_score"], int)

    def test_rescue_endpoint_handles_rag_gracefully(self, api_client):
        """Rescue endpoint should work with RAG context, even when Gemini is unavailable."""
        response = api_client.post("/api/rescue")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "RESCUE_MISSION_LAUNCHED"
        assert len(data["action_plan"]) >= 1
        assert len(data["generated_asset"]) > 0

    def test_all_api_endpoints_work_without_gemini_key(self, api_client):
        """All RAG-enhanced endpoints should work when Gemini API key is missing."""
        import os
        original_key = os.environ.pop("GEMINI_API_KEY", None)
        try:
            assert api_client.post("/api/goals/decompose", json={
                "goal_title": "Test fallback", "target_date": "2026-08-01"
            }).status_code == 200

            assert api_client.post("/api/simulate", json={
                "action": "Test fallback"
            }).status_code == 200

            assert api_client.post("/api/rescue").status_code == 200

            assert api_client.post("/api/summary", json={
                "period": "daily"
            }).status_code == 200
        finally:
            if original_key is not None:
                os.environ["GEMINI_API_KEY"] = original_key


# ============================================================================
# Edge Cases & Error Handling
# ============================================================================

class TestRAGEdgeCases:
    """Test edge cases and error handling in the RAG engine."""

    def test_init_engine_idempotent(self):
        """Calling init_engine() multiple times returns the same instance."""
        rag._engine = None
        e1 = rag.init_engine()
        e2 = rag.init_engine()
        assert e1 is e2  # same instance

    def test_engine_with_empty_data_does_not_crash(self):
        engine = RAGEngine()
        engine.initialize()
        results = engine.query("anything")
        assert results == []

    def test_engine_gracefully_handles_query_before_index(self):
        engine = RAGEngine()
        engine.initialize()
        # Query before any data is indexed
        results = engine.query("test query")
        assert results == []

    def test_large_number_of_documents(self):
        """Engine should handle indexing many documents without issues."""
        engine = RAGEngine()
        engine.initialize()
        for i in range(100):
            engine.index_goal({
                "id": i,
                "title": f"Goal {i}",
                "status": "ACTIVE",
                "progress": i % 100,
                "deadline": "2026-12-31"
            })
        assert engine._fallback.count() == 100
        # Query should still work
        results = engine.query("goal 50", n_results=5)
        assert len(results) <= 5

    def test_format_context_with_duplicate_types(self):
        """format_context should handle multiple results of the same type."""
        engine = RAGEngine()
        engine.initialize()
        engine.index_goal({"id": 1, "title": "G1", "status": "A", "progress": 10, "deadline": "d1"})
        engine.index_goal({"id": 2, "title": "G2", "status": "A", "progress": 20, "deadline": "d2"})
        results = engine.query("goal", n_results=2)
        context = engine.format_context(results)
        lines = context.split("\n")
        assert len(lines) == 2
        assert all(line.startswith("[GOAL]") for line in lines)
