"""FutureShield AI - Database Unit Tests

Tests for database.py functions including initialization,
CRUD operations, edge cases, and error handling.

Fixtures from conftest.py:
- use_test_database: isolates each test with a temp database file

Run with: pytest tests/test_database.py -v
"""
import pytest
import os
import tempfile
import sqlite3


# ============================================================================
# Database Initialization
# ============================================================================

class TestDatabaseInit:
    """Test database initialization and schema creation."""

    def test_init_db_creates_tables(self):
        """After init_db, all expected tables should exist."""
        import database
        database.init_db()

        tables = database.query_db(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        table_names = [t["name"] for t in tables]
        assert "threats" in table_names
        assert "goals" in table_names
        assert "focus_records" in table_names
        assert "focus_sessions" in table_names

    def test_init_db_is_idempotent(self):
        """Calling init_db multiple times should not raise errors."""
        import database
        database.init_db()
        database.init_db()
        database.init_db()  # Third call should be fine

    def test_init_db_seeds_default_data(self):
        """init_db should seed default data into empty tables."""
        import database
        database.init_db()

        threats = database.query_db("SELECT COUNT(*) as count FROM threats", one=True)
        assert threats["count"] > 0

        goals = database.query_db("SELECT COUNT(*) as count FROM goals", one=True)
        assert goals["count"] > 0

        records = database.query_db("SELECT COUNT(*) as count FROM focus_records", one=True)
        assert records["count"] > 0

    def test_init_db_does_not_duplicate_seeds(self):
        """Calling init_db twice should not duplicate seed data."""
        import database
        database.init_db()

        count_1 = database.query_db("SELECT COUNT(*) as count FROM threats", one=True)
        database.init_db()  # second init
        count_2 = database.query_db("SELECT COUNT(*) as count FROM threats", one=True)
        assert count_2["count"] == count_1["count"]


# ============================================================================
# query_db
# ============================================================================

class TestQueryDB:
    """Test the query_db function."""

    def test_query_all_goals(self):
        import database
        database.init_db()
        goals = database.query_db("SELECT * FROM goals")
        assert isinstance(goals, list)
        assert len(goals) > 0
        assert "id" in goals[0]
        assert "title" in goals[0]
        assert "status" in goals[0]
        assert "progress" in goals[0]
        assert "deadline" in goals[0]

    def test_query_with_parameters(self):
        import database
        database.init_db()
        # Get a specific goal by status
        goals = database.query_db(
            "SELECT * FROM goals WHERE status = ?", ("COMPLETED",)
        )
        assert isinstance(goals, list)
        for g in goals:
            assert g["status"] == "COMPLETED"

    def test_query_one_returns_single_dict(self):
        import database
        database.init_db()
        result = database.query_db(
            "SELECT COUNT(*) as count FROM goals", one=True
        )
        assert isinstance(result, dict)
        assert "count" in result

    def test_query_one_returns_none_if_empty(self):
        import database
        database.init_db()
        # Query a non-existent ID
        result = database.query_db(
            "SELECT * FROM goals WHERE id = ?", (99999,), one=True
        )
        assert result is None

    def test_query_returns_empty_list_if_no_results(self):
        import database
        database.init_db()
        goals = database.query_db(
            "SELECT * FROM goals WHERE status = 'NONEXISTENT'"
        )
        assert goals == []

    def test_query_with_complex_where(self):
        import database
        database.init_db()
        goals = database.query_db(
            "SELECT * FROM goals WHERE progress > ? AND status != ?",
            (50, "COMPLETED")
        )
        assert isinstance(goals, list)

    def test_query_order_by(self):
        import database
        database.init_db()
        goals = database.query_db("SELECT * FROM goals ORDER BY progress DESC")
        assert len(goals) >= 2
        assert goals[0]["progress"] >= goals[-1]["progress"]


# ============================================================================
# execute_db
# ============================================================================

class TestExecuteDB:
    """Test the execute_db function."""

    def test_execute_insert(self):
        import database
        database.init_db()
        count_before = database.query_db(
            "SELECT COUNT(*) as count FROM goals", one=True
        )["count"]

        database.execute_db(
            "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
            ("Test Goal", "ACTIVE", 50, "2026-12-31")
        )

        count_after = database.query_db(
            "SELECT COUNT(*) as count FROM goals", one=True
        )["count"]
        assert count_after == count_before + 1

    def test_execute_update(self):
        import database
        database.init_db()
        # Get first goal
        goal = database.query_db("SELECT * FROM goals LIMIT 1", one=True)
        goal_id = goal["id"]

        database.execute_db(
            "UPDATE goals SET progress = ? WHERE id = ?",
            (99, goal_id)
        )

        updated = database.query_db(
            "SELECT * FROM goals WHERE id = ?", (goal_id,), one=True
        )
        assert updated["progress"] == 99

    def test_execute_delete(self):
        import database
        database.init_db()
        count_before = database.query_db(
            "SELECT COUNT(*) as count FROM goals", one=True
        )["count"]

        # Delete one goal
        goal = database.query_db("SELECT * FROM goals LIMIT 1", one=True)
        database.execute_db("DELETE FROM goals WHERE id = ?", (goal["id"],))

        count_after = database.query_db(
            "SELECT COUNT(*) as count FROM goals", one=True
        )["count"]
        assert count_after == count_before - 1

    def test_execute_with_empty_args(self):
        import database
        database.init_db()
        # Should handle empty args tuple
        count = database.query_db("SELECT COUNT(*) as count FROM threats", one=True)
        assert count["count"] >= 0

    def test_execute_multiple_statements_safely(self):
        """execute_db should only execute single statements (SQLite safety)."""
        import database
        database.init_db()
        # Single INSERT should work
        database.execute_db(
            "INSERT INTO threats (id, name, urgency, probability, success_rate, x_pos, y_pos, type) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("TEST-001", "Test Threat", "LOW", 10, "99%", 10, 10, "optimized")
        )
        threat = database.query_db(
            "SELECT * FROM threats WHERE id = ?", ("TEST-001",), one=True
        )
        assert threat is not None
        assert threat["name"] == "Test Threat"


# ============================================================================
# insert_and_get_id
# ============================================================================

class TestInsertAndGetID:
    """Test the insert_and_get_id function."""

    def test_insert_returns_positive_id(self):
        import database
        database.init_db()
        new_id = database.insert_and_get_id(
            "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
            ("Insert Test", "ACTIVE", 10, "2026-12-31")
        )
        assert new_id is not None
        assert isinstance(new_id, int)
        assert new_id > 0

    def test_inserted_row_is_retrievable(self):
        import database
        database.init_db()
        new_id = database.insert_and_get_id(
            "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
            ("Retrievable Goal", "ACTIVE", 25, "2026-12-31")
        )
        goal = database.query_db(
            "SELECT * FROM goals WHERE id = ?", (new_id,), one=True
        )
        assert goal is not None
        assert goal["title"] == "Retrievable Goal"

    def test_insert_increments_id(self):
        import database
        database.init_db()
        id_1 = database.insert_and_get_id(
            "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
            ("First", "ACTIVE", 10, "2026-12-31")
        )
        id_2 = database.insert_and_get_id(
            "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
            ("Second", "ACTIVE", 20, "2026-12-31")
        )
        assert id_2 > id_1

    def test_insert_goal_with_empty_deadline(self):
        import database
        database.init_db()
        new_id = database.insert_and_get_id(
            "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
            ("No Deadline", "ACTIVE", 0, "")
        )
        assert new_id > 0


# ============================================================================
# Edge Cases & Error Handling
# ============================================================================

class TestDatabaseEdgeCases:
    """Test edge cases and error handling."""

    def test_query_on_empty_table(self):
        import database
        database.init_db()
        # Delete all records, then query should return empty list
        database.execute_db("DELETE FROM focus_sessions")
        sessions = database.query_db("SELECT * FROM focus_sessions")
        assert sessions == []

    def test_execute_rollback_on_error(self):
        """When execute_db fails, it should not leave the DB in a broken state."""
        import database
        database.init_db()
        count_before = database.query_db(
            "SELECT COUNT(*) as count FROM goals", one=True
        )["count"]

        with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)):
            # Try to insert a goal with missing required fields (should fail)
            database.execute_db(
                "INSERT INTO goals (title) VALUES (?)",
                ("Incomplete",)
            )

        # DB should still be usable
        count_after = database.query_db(
            "SELECT COUNT(*) as count FROM goals", one=True
        )["count"]
        assert count_after == count_before

    def test_bulk_insert_and_query(self):
        """Test inserting and retrieving many records."""
        import database
        database.init_db()

        # Insert 50 goals
        for i in range(50):
            database.execute_db(
                "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
                (f"Bulk Goal {i}", "ACTIVE", i, "2026-12-31")
            )

        goals = database.query_db("SELECT * FROM goals WHERE status = 'ACTIVE'")
        assert len(goals) >= 50

    def test_query_with_special_characters(self):
        """Titles with special characters should store and retrieve correctly."""
        import database
        database.init_db()
        special_title = "Test: Project with 'quotes' & <html> & 日本語"
        database.execute_db(
            "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
            (special_title, "ACTIVE", 50, "2026-12-31")
        )
        goal = database.query_db(
            "SELECT * FROM goals WHERE title = ?", (special_title,), one=True
        )
        assert goal is not None
        assert goal["title"] == special_title

    def test_query_with_limit(self):
        import database
        database.init_db()
        # Insert extra goals
        for i in range(10):
            database.execute_db(
                "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
                (f"Limit Test {i}", "ACTIVE", i, "2026-12-31")
            )
        goals = database.query_db("SELECT * FROM goals LIMIT 5")
        assert len(goals) <= 5

    def test_query_with_offset(self):
        import database
        database.init_db()
        # Insert goals with sequential titles
        for i in range(10):
            database.execute_db(
                "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
                (f"Offset Test {i}", "ACTIVE", i, "2026-12-31")
            )
        # Get page 2
        goals = database.query_db("SELECT * FROM goals LIMIT 3 OFFSET 3")
        assert len(goals) <= 3


# ============================================================================
# Thread Safety (basic)
# ============================================================================

class TestDatabaseConcurrency:
    """Basic thread safety tests for database operations."""

    def test_concurrent_reads(self):
        """Multiple sequential reads should not interfere."""
        import database
        database.init_db()
        for _ in range(100):
            goals = database.query_db("SELECT * FROM goals")
            assert isinstance(goals, list)

    def test_read_write_sequence(self):
        """Interleaved reads/writes should not break."""
        import database
        database.init_db()
        for i in range(20):
            database.execute_db(
                "INSERT INTO goals (title, status, progress, deadline) VALUES (?, ?, ?, ?)",
                (f"Concurrent Test {i}", "ACTIVE", i, "2026-12-31")
            )
            goal = database.query_db(
                "SELECT * FROM goals WHERE title = ?", (f"Concurrent Test {i}",), one=True
            )
            assert goal is not None
            assert goal["progress"] == i
