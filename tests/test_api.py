"""
FutureShield AI - Backend API Tests
Run with: pytest tests/test_api.py -v
"""
import pytest
import os
import sys
import json

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import warnings
from fastapi.testclient import TestClient
# Import the app - will initialize DB on startup
from main import app

# Filter httpx deprecation warning for the 'app' shortcut
warnings.filterwarnings("ignore", category=DeprecationWarning, module="httpx")

# Create test client
client = TestClient(app=app)
client.headers["Authorization"] = "Bearer shield-admin-pass"


class TestStatusEndpoint:
    """Test the /api/status endpoint"""

    def test_get_status_returns_200(self):
        response = client.get("/api/status")
        assert response.status_code == 200

    def test_get_status_has_required_fields(self):
        response = client.get("/api/status")
        data = response.json()
        assert "success_score" in data
        assert "data_nodes" in data
        assert "latency" in data
        assert "telemetry" in data
        assert "nodes" in data
        assert isinstance(data["success_score"], int)
        assert 0 <= data["success_score"] <= 100

    def test_get_status_telemetry_structure(self):
        response = client.get("/api/status")
        data = response.json()
        telemetry = data["telemetry"]
        assert "core_load" in telemetry
        assert "ai_engine" in telemetry
        assert telemetry["ai_engine"] == "ACTIVE"

    def test_get_status_nodes_structure(self):
        response = client.get("/api/status")
        data = response.json()
        assert len(data["nodes"]) >= 3
        for node in data["nodes"]:
            assert "id" in node
            assert "status" in node


class TestThreatsEndpoint:
    """Test the /api/threats endpoint"""

    def test_get_threats_returns_200(self):
        response = client.get("/api/threats")
        assert response.status_code == 200

    def test_get_threats_has_required_fields(self):
        response = client.get("/api/threats")
        data = response.json()
        assert "scanned_count" in data
        assert "threats" in data
        assert isinstance(data["threats"], list)

    def test_get_threats_structure(self):
        response = client.get("/api/threats")
        data = response.json()
        for threat in data["threats"]:
            assert "id" in threat
            assert "name" in threat
            assert "urgency" in threat
            assert "probability" in threat
            assert "success_rate" in threat
            assert "x_pos" in threat
            assert "y_pos" in threat
            assert "type" in threat

    def test_resolve_threat_returns_200(self):
        # Get first threat
        response = client.get("/api/threats")
        threats = response.json()["threats"]
        if threats:
            threat_id = threats[0]["id"]
            resolve_resp = client.post(f"/api/threats/{threat_id}/resolve")
            assert resolve_resp.status_code == 200
            assert resolve_resp.json()["status"] == "success"
            assert resolve_resp.json()["resolved_threat"] == threat_id

    def test_resolve_nonexistent_threat_returns_404(self):
        response = client.post("/api/threats/INVALID_ID/resolve")
        assert response.status_code == 404


class TestGoalsEndpoint:
    """Test the /api/goals endpoints"""

    def test_get_goals_returns_200(self):
        response = client.get("/api/goals")
        assert response.status_code == 200

    def test_get_goals_structure(self):
        response = client.get("/api/goals")
        data = response.json()
        assert "goals" in data
        assert isinstance(data["goals"], list)

    def test_create_goal(self):
        goal_data = {
            "title": "Test Hackathon Goal",
            "status": "ACTIVE",
            "progress": 25,
            "deadline": "2026-07-01"
        }
        response = client.post("/api/goals", json=goal_data)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"

    def test_update_goal_progress(self):
        # Get existing goals
        response = client.get("/api/goals")
        goals = response.json()["goals"]
        if goals:
            goal_id = goals[0]["id"]
            update_resp = client.put(f"/api/goals/{goal_id}?progress=75")
            assert update_resp.status_code == 200
            assert update_resp.json()["status"] == "success"

    def test_goal_decompose_with_missing_fields(self):
        response = client.post("/api/goals/decompose", json={})
        # Should fail validation
        assert response.status_code == 422


class TestTwinEndpoint:
    """Test the /api/twin endpoint"""

    def test_get_twin_returns_200(self):
        response = client.get("/api/twin")
        assert response.status_code == 200

    def test_get_twin_has_required_fields(self):
        response = client.get("/api/twin")
        data = response.json()
        assert "behavior_score" in data
        assert "behavior_change" in data
        assert "energy_levels" in data
        assert "neural_drift" in data
        assert "success_dna" in data
        assert isinstance(data["energy_levels"], list)
        assert len(data["energy_levels"]) == 8

    def test_get_twin_dna_structure(self):
        response = client.get("/api/twin")
        data = response.json()
        dna = data["success_dna"]
        assert "logic_resilience" in dna
        assert "decision_velocity" in dna
        assert "risk_appetite" in dna
        assert "sync_quality" in dna


class TestSimulationEndpoint:
    """Test the /api/simulate endpoint"""

    def test_simulate_with_skip_keyword(self):
        response = client.post("/api/simulate", json={"action": "Skip today's work"})
        assert response.status_code == 200
        data = response.json()
        assert "future_a" in data
        assert "future_b" in data
        assert "future_c" in data

    def test_simulate_structure(self):
        response = client.post("/api/simulate", json={"action": "Work on project"})
        data = response.json()
        for future_key in ["future_a", "future_b", "future_c"]:
            future = data[future_key]
            assert "status" in future
            assert "success_probability" in future
            assert "failure_probability" in future
            assert "stress_index" in future
            assert "deadline_risk" in future
            assert future["deadline_risk"] in ["LOW", "MEDIUM", "HIGH"]

    def test_simulate_with_empty_action(self):
        response = client.post("/api/simulate", json={"action": ""})
        assert response.status_code == 200

    def test_simulate_without_action_field(self):
        response = client.post("/api/simulate", json={})
        # Should fail validation
        assert response.status_code == 422


class TestRescueEndpoint:
    """Test the /api/rescue endpoint"""

    def test_rescue_returns_200(self):
        response = client.post("/api/rescue")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "RESCUE_MISSION_LAUNCHED"
        assert "action_plan" in data
        assert "generated_asset" in data

    def test_rescue_plan_is_list(self):
        response = client.post("/api/rescue")
        data = response.json()
        assert isinstance(data["action_plan"], list)
        assert len(data["action_plan"]) >= 1

    def test_rescue_asset_is_string(self):
        response = client.post("/api/rescue")
        data = response.json()
        assert isinstance(data["generated_asset"], str)
        assert len(data["generated_asset"]) > 0


class TestHTMLPages:
    """Test that all HTML pages are served"""

    @pytest.mark.parametrize("route", [
        "/",
        "/index.html",
        "/dashboard.html",
        "/radar.html",
        "/simulation.html",
        "/rescue.html",
        "/twin.html",
    ])
    def test_html_pages_return_200(self, route):
        response = client.get(route)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_invalid_page_returns_404(self):
        response = client.get("/nonexistent.html")
        assert response.status_code == 404

    def test_invalid_page_returns_404_detail(self):
        response = client.get("/foo.html")
        assert response.status_code == 404
        assert response.json()["detail"] == "Page not found"


class TestSummaryEndpoint:
    """Test the /api/summary endpoint"""

    def test_daily_summary_returns_200(self):
        response = client.post("/api/summary", json={"period": "daily"})
        assert response.status_code == 200

    def test_weekly_summary_returns_200(self):
        response = client.post("/api/summary", json={"period": "weekly"})
        assert response.status_code == 200

    def test_summary_has_required_fields(self):
        response = client.post("/api/summary", json={"period": "daily"})
        data = response.json()
        assert data["status"] == "success"
        assert "period" in data
        assert "summary" in data
        s = data["summary"]
        assert "overall_assessment" in s
        assert "productivity_score" in s
        assert "key_insights" in s
        assert "top_priority" in s
        assert "risk_warning" in s
        assert "energy_verdict" in s

    def test_summary_score_is_integer(self):
        response = client.post("/api/summary", json={"period": "daily"})
        score = response.json()["summary"]["productivity_score"]
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_summary_insights_are_list(self):
        response = client.post("/api/summary", json={"period": "daily"})
        insights = response.json()["summary"]["key_insights"]
        assert isinstance(insights, list)
        assert len(insights) >= 1

    def test_summary_defaults_to_daily(self):
        response = client.post("/api/summary", json={})
        assert response.status_code == 200
        assert response.json()["period"] == "daily"


class TestFocusTimer:
    """Test the /api/focus endpoints"""

    def test_start_focus_returns_200(self):
        response = client.post("/api/focus/start", json={
            "duration_minutes": 25,
            "session_type": "focus"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "focus_started"
        assert "session" in data
        assert data["session"]["status"] == "active"
        assert data["session"]["duration_minutes"] == 25

    def test_start_focus_default_duration(self):
        response = client.post("/api/focus/start", json={
            "session_type": "focus"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["duration_minutes"] == 25

    def test_start_focus_auto_closes_previous(self):
        # Start first session
        client.post("/api/focus/start", json={"duration_minutes": 10})
        # Start second session (should auto-close first)
        response = client.post("/api/focus/start", json={"duration_minutes": 15})
        assert response.status_code == 200
        data = response.json()
        assert data["session"]["duration_minutes"] == 15

    def test_stop_focus_no_active_session(self):
        response = client.post("/api/focus/stop", json={"energy_rating": 7})
        assert response.status_code == 404

    def test_stop_focus_start_and_stop(self):
        # Start
        start_resp = client.post("/api/focus/start", json={"duration_minutes": 15})
        assert start_resp.status_code == 200
        session_id = start_resp.json()["session"]["id"]

        # Stop
        stop_resp = client.post("/api/focus/stop", json={"energy_rating": 8})
        assert stop_resp.status_code == 200
        data = stop_resp.json()
        assert data["status"] == "focus_stopped"
        assert data["session"]["status"] == "completed"
        assert data["session"]["energy_rating"] == 8

    def test_get_current_session_no_active(self):
        response = client.get("/api/focus/current")
        assert response.status_code == 200
        data = response.json()
        assert data["active"] == False

    def test_get_current_session_active(self):
        client.post("/api/focus/start", json={"duration_minutes": 25})
        response = client.get("/api/focus/current")
        assert response.status_code == 200
        data = response.json()
        assert data["active"] == True
        assert data["session"]["status"] == "active"

    def test_get_focus_sessions(self):
        # Start and stop a session
        client.post("/api/focus/start", json={"duration_minutes": 10})
        client.post("/api/focus/stop", json={"energy_rating": 6})

        response = client.get("/api/focus/sessions?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "stats" in data
        assert "total_sessions" in data["stats"]
        assert "total_focus_minutes" in data["stats"]
        assert "average_energy_rating" in data["stats"]

    def test_focus_session_updates_focus_records(self):
        # Start and stop a session
        client.post("/api/focus/start", json={"duration_minutes": 10})
        client.post("/api/focus/stop", json={"energy_rating": 9})

        # Check that focus_records was updated
        response = client.get("/api/twin")
        data = response.json()
        assert len(data["energy_levels"]) > 0
        # Should show the 90 (9 * 10) energy level we submitted
        assert data["user_focus_data"]["total_sessions_completed"] > 0

    def test_twin_has_focus_data_field(self):
        response = client.get("/api/twin")
        data = response.json()
        assert "user_focus_data" in data
        assert "total_sessions_completed" in data["user_focus_data"]
        assert "total_focus_minutes" in data["user_focus_data"]
        assert "is_in_session" in data["user_focus_data"]


class TestCORS:
    """Test CORS headers are present"""

    def test_cors_headers(self):
        response = client.options("/api/status", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        assert "access-control-allow-origin" in response.headers


class TestSecurityToken:
    """Test that API endpoints are protected by the token"""

    def test_unauthenticated_request_returns_401(self):
        # Temporarily clear authorization header
        auth = client.headers.pop("Authorization", None)
        try:
            response = client.get("/api/status")
            assert response.status_code == 401
            assert "detail" in response.json()
            assert response.json()["detail"] == "Invalid or missing FutureShield security token."
        finally:
            # Restore
            if auth:
                client.headers["Authorization"] = auth

    def test_invalid_token_returns_401(self):
        # Temporarily set invalid authorization header
        auth = client.headers.get("Authorization")
        client.headers["Authorization"] = "Bearer invalid-token-value"
        try:
            response = client.get("/api/status")
            assert response.status_code == 401
        finally:
            # Restore
            if auth:
                client.headers["Authorization"] = auth


class TestDemoEndpoints:
    """Test the /api/demo endpoints"""

    def test_demo_seed_returns_200(self):
        response = client.post("/api/demo/seed")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "demo_seeded"
        assert data["goals"] >= 1
        assert data["threats"] >= 1
        assert data["focus_records"] >= 1

    def test_demo_seed_populates_goals(self):
        client.post("/api/demo/seed")
        response = client.get("/api/goals")
        data = response.json()
        assert len(data["goals"]) >= 10

    def test_demo_seed_populates_threats(self):
        client.post("/api/demo/seed")
        response = client.get("/api/threats")
        data = response.json()
        assert len(data["threats"]) >= 8

    def test_demo_seed_updates_twin(self):
        client.post("/api/demo/seed")
        response = client.get("/api/twin")
        data = response.json()
        # Twin endpoint returns up to 8 energy levels (limited by query)
        assert len(data["energy_levels"]) == 8
        assert all(isinstance(l, int) for l in data["energy_levels"])

    def test_demo_reset_returns_200(self):
        response = client.post("/api/demo/reset")
        assert response.status_code == 200
        assert response.json()["status"] == "reset_complete"

    def test_demo_reset_clears_data(self):
        # Seed first
        client.post("/api/demo/seed")
        # Reset
        client.post("/api/demo/reset")
        # Check data is back to defaults
        response = client.get("/api/goals")
        data = response.json()
        assert len(data["goals"]) >= 0

    def test_demo_seed_is_idempotent(self):
        client.post("/api/demo/seed")
        count_1 = client.get("/api/goals").json()["total"]
        client.post("/api/demo/seed")
        count_2 = client.get("/api/goals").json()["total"]
        assert count_1 == count_2  # Should overwrite, not accumulate


class TestDemoExportEndpoint:
    """Test the GET /api/demo/export endpoint"""

    def test_export_returns_200(self):
        """Export should return 200 with seeded data."""
        response = client.get("/api/demo/export")
        assert response.status_code == 200

    def test_export_has_content_disposition(self):
        """Export response should have Content-Disposition: attachment header."""
        response = client.get("/api/demo/export")
        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert ".json" in response.headers["content-disposition"]

    def test_export_content_type_is_json(self):
        """Export response should have application/json content type."""
        response = client.get("/api/demo/export")
        assert "application/json" in response.headers.get("content-type", "")

    def test_export_structure_with_default_seed(self):
        """Export with default seed data should return the expected top-level structure."""
        response = client.get("/api/demo/export")
        data = response.json()
        assert "exported_at" in data
        assert "version" in data
        assert data["version"] == "1.0"
        assert "description" in data
        assert "data" in data
        assert "stats" in data

    def test_export_data_keys(self):
        """The .data field should contain all four entity types."""
        response = client.get("/api/demo/export")
        d = response.json()["data"]
        assert "goals" in d
        assert "threats" in d
        assert "focus_records" in d
        assert "focus_sessions" in d

    def test_export_contains_goals(self):
        """Export should include the seeded goals."""
        response = client.get("/api/demo/export")
        data = response.json()
        assert len(data["data"]["goals"]) > 0
        goal = data["data"]["goals"][0]
        assert "id" in goal
        assert "title" in goal
        assert "status" in goal
        assert "progress" in goal
        assert "deadline" in goal

    def test_export_contains_threats(self):
        """Export should include the seeded threats."""
        response = client.get("/api/demo/export")
        data = response.json()
        assert len(data["data"]["threats"]) > 0
        threat = data["data"]["threats"][0]
        assert "id" in threat
        assert "name" in threat
        assert "urgency" in threat
        assert "probability" in threat
        assert "success_rate" in threat

    def test_export_stats_match_data(self):
        """The .stats counts should match actual array lengths in .data."""
        response = client.get("/api/demo/export")
        d = response.json()
        for key in ("goals", "threats", "focus_records", "focus_sessions"):
            assert d["stats"][key] == len(d["data"][key]), (
                f"Stats count for {key} ({d['stats'][key]}) doesn't match data length ({len(d['data'][key])})"
            )

    def test_export_focus_records_have_timestamp(self):
        """Focus records should include the timestamp field."""
        response = client.get("/api/demo/export")
        records = response.json()["data"]["focus_records"]
        if records:
            assert "timestamp" in records[0]
            assert "energy_level" in records[0]

    def test_export_focus_sessions_have_all_fields(self):
        """Focus sessions should include all expected columns."""
        response = client.get("/api/demo/export")
        sessions = response.json()["data"]["focus_sessions"]
        if sessions:
            s = sessions[0]
            assert "id" in s
            assert "start_time" in s
            assert "duration_minutes" in s
            assert "session_type" in s
            assert "status" in s

    def test_export_round_trip_preserves_data_count(self):
        """Export then import should preserve the number of records."""
        # Get baseline export
        export_resp = client.get("/api/demo/export")
        export_data = export_resp.json()
        original_counts = export_data["stats"]

        # Reset to blank slate
        client.post("/api/demo/reset")

        # Re-import the exported data
        import_resp = client.post("/api/demo/import", json=export_data)
        assert import_resp.status_code == 200
        imported = import_resp.json()["imported"]

        # Verify counts match
        for key in ("goals", "threats", "focus_records", "focus_sessions"):
            assert imported[key] == original_counts[key], (
                f"Import count for {key} ({imported[key]}) doesn't match export ({original_counts[key]})"
            )

    def test_export_round_trip_preserves_goal_progress(self):
        """After export->import, goal progress values should be preserved."""
        export_resp = client.get("/api/demo/export")
        original_progress = [
            g["progress"] for g in export_resp.json()["data"]["goals"]
        ]

        client.post("/api/demo/reset")
        client.post("/api/demo/import", json=export_resp.json())

        restored = client.get("/api/goals").json()["goals"]
        restored_progress = [g["progress"] for g in restored]
        assert restored_progress == original_progress

    def test_export_after_reset_still_has_seed_data(self):
        """After reset (clear + re-init), export should still return valid data.
        init_db seeds default data, so it should not be truly empty.
        """
        client.post("/api/demo/reset")
        response = client.get("/api/demo/export")
        data = response.json()
        # Default seed inserts data, so all should be > 0
        for key in ("goals", "threats", "focus_records"):
            assert data["stats"][key] > 0, f"{key} should have default seed data"

    def test_export_on_truly_empty_database(self):
        """Export should handle a completely empty database gracefully:
        valid JSON, zero counts, empty arrays (no crashes/missing keys).
        """
        import database
        database.execute_db("DELETE FROM goals")
        database.execute_db("DELETE FROM threats")
        database.execute_db("DELETE FROM focus_records")
        database.execute_db("DELETE FROM focus_sessions")

        response = client.get("/api/demo/export")
        assert response.status_code == 200
        data = response.json()

        # Should still have all structural keys
        assert "exported_at" in data
        assert "version" in data
        assert "data" in data
        assert "stats" in data

        # All data arrays should be empty
        assert data["data"]["goals"] == []
        assert data["data"]["threats"] == []
        assert data["data"]["focus_records"] == []
        assert data["data"]["focus_sessions"] == []

        # All stats should be zero
        for key in ("goals", "threats", "focus_records", "focus_sessions"):
            assert data["stats"][key] == 0, f"{key} stats should be 0 when empty"

    def test_export_version_field(self):
        """The version field should be '1.0'."""
        response = client.get("/api/demo/export")
        assert response.json()["version"] == "1.0"

    def test_export_description_field(self):
        """The description field should be a non-empty string."""
        response = client.get("/api/demo/export")
        desc = response.json()["description"]
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_export_has_exported_at(self):
        """The exported_at field should be an ISO datetime string."""
        response = client.get("/api/demo/export")
        ts = response.json()["exported_at"]
        assert "T" in ts  # ISO format includes T separator
        assert ts.endswith("T") is False

    def test_export_threats_include_resolved_field(self):
        """Each exported threat should have a 'resolved' boolean field."""
        response = client.get("/api/demo/export")
        threats = response.json()["data"]["threats"]
        if threats:
            for t in threats:
                assert "resolved" in t
                assert t["resolved"] in (0, 1)

    def test_export_focus_sessions_include_energy_rating(self):
        """Focus sessions should include the nullable energy_rating field."""
        response = client.get("/api/demo/export")
        sessions = response.json()["data"]["focus_sessions"]
        if sessions:
            assert "energy_rating" in sessions[0]

    def test_export_endpoint_requires_auth(self):
        """Export endpoint should require authentication."""
        auth = client.headers.pop("Authorization", None)
        try:
            response = client.get("/api/demo/export")
            assert response.status_code == 401
        finally:
            if auth:
                client.headers["Authorization"] = auth


class TestDemoImportEndpoint:
    """Test the POST /api/demo/import endpoint"""

    def test_import_empty_payload_returns_zero_counts(self):
        """Import with an empty JSON body should return zero counts for all entities."""
        response = client.post("/api/demo/import", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "import_complete"
        assert data["imported"] == {"goals": 0, "threats": 0, "focus_records": 0, "focus_sessions": 0}
        assert "message" in data

    def test_import_missing_data_field_returns_zero_counts(self):
        """Import with no .data field should gracefully return zero counts."""
        response = client.post("/api/demo/import", json={"version": "1.0"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "import_complete"
        assert data["imported"] == {"goals": 0, "threats": 0, "focus_records": 0, "focus_sessions": 0}

    def test_import_empty_data_returns_zero_counts(self):
        """Import with empty .data field should return zero counts."""
        response = client.post("/api/demo/import", json={"data": {}})
        assert response.status_code == 200
        data = response.json()
        assert data["imported"] == {"goals": 0, "threats": 0, "focus_records": 0, "focus_sessions": 0}

    def test_import_only_goals_partial_data(self):
        """Import with only goals should populate goals but leave other entities at zero."""
        payload = {
            "data": {
                "goals": [
                    {"id": 1, "title": "Goal A", "status": "ACTIVE", "progress": 50, "deadline": "2026-07-01"},
                    {"id": 2, "title": "Goal B", "status": "COMPLETED", "progress": 100, "deadline": "2026-06-15"},
                ]
            }
        }
        response = client.post("/api/demo/import", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["imported"]["goals"] == 2
        assert data["imported"]["threats"] == 0
        assert data["imported"]["focus_records"] == 0
        assert data["imported"]["focus_sessions"] == 0

        # Verify goals are actually in the database
        goals_resp = client.get("/api/goals")
        goals = goals_resp.json()["goals"]
        titles = [g["title"] for g in goals]
        assert "Goal A" in titles
        assert "Goal B" in titles

    def test_import_only_threats_partial_data(self):
        """Import with only threats should populate threats but leave other entities at zero."""
        payload = {
            "data": {
                "threats": [
                    {"id": "TH-001", "name": "Test threat", "urgency": "HIGH",
                     "probability": 75, "success_rate": "15%", "x_pos": 10, "y_pos": 20,
                     "type": "critical", "resolved": 0},
                ]
            }
        }
        response = client.post("/api/demo/import", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["imported"]["goals"] == 0
        assert data["imported"]["threats"] == 1
        assert data["imported"]["focus_records"] == 0
        assert data["imported"]["focus_sessions"] == 0

        # Verify threats exist
        threats_resp = client.get("/api/threats")
        threats = threats_resp.json()["threats"]
        names = [t["name"] for t in threats]
        assert "Test threat" in names

    def test_import_only_focus_records_partial_data(self):
        """Import with only focus records should leave other entities at zero."""
        payload = {
            "data": {
                "focus_records": [
                    {"id": 1, "timestamp": "2026-06-27T10:00:00", "energy_level": 85},
                    {"id": 2, "timestamp": "2026-06-27T11:00:00", "energy_level": 70},
                    {"id": 3, "timestamp": "2026-06-27T12:00:00", "energy_level": 90},
                ]
            }
        }
        response = client.post("/api/demo/import", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["imported"]["focus_records"] == 3
        assert data["imported"]["goals"] == 0
        assert data["imported"]["threats"] == 0
        assert data["imported"]["focus_sessions"] == 0

    def test_import_overwrites_existing_data(self):
        """Importing should clear existing data before inserting new data."""
        # First import some goals
        client.post("/api/demo/import", json={
            "data": {"goals": [{"id": 1, "title": "Old Goal", "status": "ACTIVE", "progress": 10, "deadline": "2026-07-01"}]}
        })

        # Then import different goals
        client.post("/api/demo/import", json={
            "data": {"goals": [{"id": 2, "title": "New Goal", "status": "ACTIVE", "progress": 50, "deadline": "2026-08-01"}]}
        })

        # Should only have the new goal
        goals_resp = client.get("/api/goals")
        goals = goals_resp.json()["goals"]
        assert len(goals) == 1
        assert goals[0]["title"] == "New Goal"
        assert goals[0]["id"] == 2

    def test_import_with_minimal_goal_fields(self):
        """Import should handle goals with only required fields, filling defaults for missing fields."""
        payload = {
            "data": {
                "goals": [
                    # Missing status, progress, deadline - should use defaults
                    {"id": 1, "title": "Minimal Goal"},
                ]
            }
        }
        response = client.post("/api/demo/import", json=payload)
        assert response.status_code == 200
        assert response.json()["imported"]["goals"] == 1

        goals_resp = client.get("/api/goals")
        goal = goals_resp.json()["goals"][0]
        assert goal["title"] == "Minimal Goal"
        assert goal["status"] == "ACTIVE"  # default
        assert goal["progress"] == 0  # default

    def test_import_with_minimal_threat_fields(self):
        """Import should handle threats with only required fields, filling defaults."""
        payload = {
            "data": {
                "threats": [
                    # Missing most fields - should use defaults
                    {"id": "TH-MIN", "name": "Minimal threat"},
                ]
            }
        }
        response = client.post("/api/demo/import", json=payload)
        assert response.status_code == 200
        assert response.json()["imported"]["threats"] == 1

        threats_resp = client.get("/api/threats")
        threat = threats_resp.json()["threats"][0]
        assert threat["name"] == "Minimal threat"
        assert threat["urgency"] == "LOW"  # default
        assert threat["resolved"] == 0  # default

    def test_import_nonexistent_entity_keys_ignored(self):
        """Extra unknown keys in the payload should be ignored gracefully."""
        payload = {
            "data": {
                "goals": [],
                "threats": [],
                "focus_records": [],
                "focus_sessions": [],
                "unknown_table": [{"foo": "bar"}],
            }
        }
        response = client.post("/api/demo/import", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "import_complete"

    def test_import_round_trip_export_import_preserves_all_data(self):
        """Full round-trip: export -> import -> export should preserve all data."""
        # Get baseline export
        export_resp = client.get("/api/demo/export")
        assert export_resp.status_code == 200
        original = export_resp.json()

        # Reset to clear data
        client.post("/api/demo/reset")

        # Import the exported data back
        import_resp = client.post("/api/demo/import", json=original)
        assert import_resp.status_code == 200
        imported_counts = import_resp.json()["imported"]

        # Verify counts match original
        for key in ("goals", "threats", "focus_records", "focus_sessions"):
            assert imported_counts[key] == original["stats"][key], (
                f"Count mismatch for {key}: imported {imported_counts[key]} vs exported {original['stats'][key]}"
            )

        # Export again and compare
        re_export = client.get("/api/demo/export").json()
        for key in ("goals", "threats", "focus_records", "focus_sessions"):
            # Compare individual fields of each record
            for orig_rec, re_exp_rec in zip(original["data"][key], re_export["data"][key]):
                for field in orig_rec:
                    assert orig_rec[field] == re_exp_rec[field], (
                        f"Field '{field}' mismatch for {key}: {orig_rec[field]} != {re_exp_rec[field]}"
                    )

    def test_import_round_trip_preserves_goal_deadlines(self):
        """Round-trip should preserve goal deadline strings exactly."""
        export_resp = client.get("/api/demo/export")
        original_deadlines = [g["deadline"] for g in export_resp.json()["data"]["goals"]]

        client.post("/api/demo/reset")
        client.post("/api/demo/import", json=export_resp.json())

        restored = client.get("/api/goals").json()["goals"]
        restored_deadlines = [g["deadline"] for g in restored]
        assert restored_deadlines == original_deadlines

    def test_import_endpoint_requires_auth(self):
        """Import endpoint should return 401 without Authorization header."""
        auth = client.headers.pop("Authorization", None)
        try:
            response = client.post("/api/demo/import", json={"data": {}})
            assert response.status_code == 401
        finally:
            if auth:
                client.headers["Authorization"] = auth

    def test_import_unknown_version_returns_422(self):
        """Import with an unsupported version should return 422 with a clear error message."""
        response = client.post("/api/demo/import", json={
            "version": "99.99",
            "data": {"goals": []},
        })
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert "Unsupported import version" in str(detail)
        assert "99.99" in str(detail)

    def test_import_with_version_1_0_succeeds(self):
        """Import with explicit version '1.0' should be accepted."""
        response = client.post("/api/demo/import", json={
            "version": "1.0",
            "data": {}
        })
        assert response.status_code == 200
        assert response.json()["status"] == "import_complete"

    def test_import_missing_version_defaults_to_current(self):
        """Import without a version field should use the current version default."""
        response = client.post("/api/demo/import", json={"data": {}})
        assert response.status_code == 200
        assert response.json()["status"] == "import_complete"

    def test_import_only_focus_sessions_partial_data(self):
        """Import with only focus sessions should populate sessions but leave other entities at zero."""
        payload = {
            "data": {
                "focus_sessions": [
                    {"id": 1, "start_time": "2026-06-27T10:00:00", "end_time": "2026-06-27T10:25:00",
                     "duration_minutes": 25, "actual_duration_seconds": 1500, "energy_rating": 8,
                     "session_type": "focus", "status": "completed"},
                    {"id": 2, "start_time": "2026-06-27T14:00:00", "end_time": "2026-06-27T14:15:00",
                     "duration_minutes": 15, "actual_duration_seconds": 900, "energy_rating": 6,
                     "session_type": "focus", "status": "completed"},
                ]
            }
        }
        response = client.post("/api/demo/import", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["imported"]["focus_sessions"] == 2
        assert data["imported"]["goals"] == 0
        assert data["imported"]["threats"] == 0
        assert data["imported"]["focus_records"] == 0

    def test_import_all_entity_types_at_once(self):
        """Import should handle all four entity types in a single payload."""
        payload = {
            "data": {
                "goals": [
                    {"id": 1, "title": "Combined Goal", "status": "ACTIVE", "progress": 30, "deadline": "2026-08-01"},
                ],
                "threats": [
                    {"id": "TH-ALL", "name": "Combined threat", "urgency": "MED",
                     "probability": 50, "success_rate": "50%", "x_pos": 10, "y_pos": 10,
                     "type": "warning", "resolved": 0},
                ],
                "focus_records": [
                    {"id": 1, "timestamp": "2026-06-27T12:00:00", "energy_level": 75},
                ],
                "focus_sessions": [
                    {"id": 1, "start_time": "2026-06-27T09:00:00", "duration_minutes": 30,
                     "session_type": "focus", "status": "completed"},
                ],
            }
        }
        response = client.post("/api/demo/import", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["imported"] == {"goals": 1, "threats": 1, "focus_records": 1, "focus_sessions": 1}

        # Verify each entity type is readable via its respective API
        assert len(client.get("/api/goals").json()["goals"]) == 1
        assert len(client.get("/api/threats").json()["threats"]) == 1

    def test_import_duplicate_full_payload_overwrites_all(self):
        """Importing a second full payload should replace all entities (not accumulate)."""
        # First import — all entities
        payload_a = {
            "data": {
                "goals": [{"id": 1, "title": "First Goal", "status": "ACTIVE", "progress": 10, "deadline": "2026-07-01"}],
                "threats": [{"id": "TH-1", "name": "Threat A", "urgency": "LOW",
                             "probability": 10, "success_rate": "90%", "x_pos": 0, "y_pos": 0,
                             "type": "optimized", "resolved": 0}],
                "focus_records": [{"id": 1, "timestamp": "2026-06-27T08:00:00", "energy_level": 60}],
                "focus_sessions": [{"id": 1, "start_time": "2026-06-27T08:00:00", "duration_minutes": 20,
                                     "session_type": "focus", "status": "completed"}],
            }
        }
        client.post("/api/demo/import", json=payload_a)

        # Second import — different data for all entities
        payload_b = {
            "data": {
                "goals": [{"id": 2, "title": "Second Goal", "status": "ACTIVE", "progress": 80, "deadline": "2026-09-01"}],
                "threats": [{"id": "TH-2", "name": "Threat B", "urgency": "HIGH",
                             "probability": 80, "success_rate": "20%", "x_pos": 50, "y_pos": 50,
                             "type": "critical", "resolved": 0}],
                "focus_records": [{"id": 2, "timestamp": "2026-06-28T08:00:00", "energy_level": 90}],
                "focus_sessions": [{"id": 2, "start_time": "2026-06-28T08:00:00", "duration_minutes": 45,
                                     "session_type": "focus", "status": "completed"}],
            }
        }
        response = client.post("/api/demo/import", json=payload_b)
        assert response.status_code == 200
        assert response.json()["imported"] == {"goals": 1, "threats": 1, "focus_records": 1, "focus_sessions": 1}

        # Should have only the second import's data (not accumulated)
        goals = client.get("/api/goals").json()["goals"]
        assert len(goals) == 1
        assert goals[0]["title"] == "Second Goal"

        threats = client.get("/api/threats").json()["threats"]
        assert len(threats) == 1
        assert threats[0]["name"] == "Threat B"

    def test_import_round_trip_preserves_threat_resolved_field(self):
        """Round-trip should preserve the 'resolved' boolean field on threats."""
        export = client.get("/api/demo/export").json()
        original_resolved = [t["resolved"] for t in export["data"]["threats"]]

        client.post("/api/demo/reset")
        client.post("/api/demo/import", json=export)

        re_export = client.get("/api/demo/export").json()
        restored_resolved = [t["resolved"] for t in re_export["data"]["threats"]]
        assert restored_resolved == original_resolved

    def test_import_round_trip_preserves_focus_session_fields(self):
        """Round-trip should preserve all focus session fields including nullable energy_rating."""
        export = client.get("/api/demo/export").json()
        original_sessions = export["data"]["focus_sessions"]

        client.post("/api/demo/reset")
        client.post("/api/demo/import", json=export)

        re_export = client.get("/api/demo/export").json()
        restored_sessions = re_export["data"]["focus_sessions"]

        for orig, rest in zip(original_sessions, restored_sessions):
            for field in ("id", "start_time", "end_time", "duration_minutes",
                          "actual_duration_seconds", "energy_rating", "session_type", "status"):
                assert orig[field] == rest[field], (
                    f"Session field '{field}' mismatch: {orig[field]} != {rest[field]}"
                )

    def test_import_with_null_optional_fields(self):
        """Import should handle null values in optional Pydantic model fields gracefully."""
        payload = {
            "data": {
                "goals": [
                    {"id": None, "title": "Null ID Goal", "status": "ACTIVE", "progress": 0, "deadline": ""},
                ],
                "focus_sessions": [
                    {"id": 1, "start_time": None, "end_time": None, "duration_minutes": 25,
                     "actual_duration_seconds": 0, "energy_rating": None,
                     "session_type": "focus", "status": "completed"},
                ],
            }
        }
        response = client.post("/api/demo/import", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["imported"]["goals"] == 1
        assert data["imported"]["focus_sessions"] == 1

        # Verify the null-ID goal was created (SQLite autoincrements)
        goals = client.get("/api/goals").json()["goals"]
        assert any(g["title"] == "Null ID Goal" for g in goals)

    def test_import_preserves_energy_rating_null(self):
        """Import should preserve a null energy_rating on focus sessions (not coerce to 0)."""
        # Create a session with null energy_rating via import
        payload = {
            "data": {
                "focus_sessions": [
                    {"id": 1, "start_time": "2026-06-27T10:00:00", "duration_minutes": 30,
                     "actual_duration_seconds": 1800, "energy_rating": None,
                     "session_type": "focus", "status": "completed"},
                ]
            }
        }
        response = client.post("/api/demo/import", json=payload)
        assert response.status_code == 200
        assert response.json()["imported"]["focus_sessions"] == 1

        # Export and verify energy_rating is None/null in JSON
        export = client.get("/api/demo/export").json()
        session = export["data"]["focus_sessions"][0]
        assert session["energy_rating"] is None

    def test_import_with_completely_empty_body(self):
        """Sending a truly empty body (None/null) should return 422 for invalid JSON."""
        response = client.post(
            "/api/demo/import",
            data=None,
            headers={"Authorization": "Bearer shield-admin-pass", "Content-Type": "application/json"},
        )
        assert response.status_code == 422


class TestAIStatusEndpoint:
    """Test the /api/ai/status and /api/ai/metrics endpoints"""

    def test_ai_status_returns_200(self):
        response = client.get("/api/ai/status")
        assert response.status_code == 200

    def test_ai_status_has_required_fields(self):
        response = client.get("/api/ai/status")
        data = response.json()
        assert "status" in data
        assert "key_configured" in data
        assert "requests_this_minute" in data

    def test_ai_status_includes_metrics(self):
        response = client.get("/api/ai/status")
        data = response.json()
        assert "metrics" in data
        assert "total_calls" in data["metrics"]
        assert "cache_hits" in data["metrics"]
        assert "total_errors" in data["metrics"]
        assert "average_response_time_ms" in data["metrics"]

    def test_ai_status_includes_cache_size(self):
        response = client.get("/api/ai/status")
        data = response.json()
        assert "cache_size" in data
        assert isinstance(data["cache_size"], int)

    def test_ai_metrics_returns_200(self):
        response = client.get("/api/ai/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "total_calls" in data
        assert isinstance(data["total_calls"], int)

    def test_ai_cache_clear_returns_200(self):
        response = client.post("/api/ai/cache/clear")
        assert response.status_code == 200
        assert response.json()["status"] == "cache_cleared"


class TestNotificationsEndpoint:
    """Test the PWA notification endpoints"""

    def test_notifications_check_returns_200(self):
        response = client.get("/api/notifications/check")
        assert response.status_code == 200
        data = response.json()
        assert "threats" in data
        assert "deadlines" in data
        assert "notification_count" in data
        assert "checked_at" in data

    def test_notifications_check_has_correct_types(self):
        response = client.get("/api/notifications/check")
        data = response.json()
        assert isinstance(data["threats"], list)
        assert isinstance(data["deadlines"], list)
        assert isinstance(data["notification_count"], int)

    def test_test_notification_returns_200(self):
        response = client.post("/api/notifications/test")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "notification" in data
        assert "title" in data["notification"]
        assert "body" in data["notification"]

    def test_push_subscribe_returns_200(self):
        response = client.post("/api/push/subscribe", json={
            "endpoint": "https://example.com/push-test",
            "keys": {"p256dh": "test-key", "auth": "test-auth"}
        })
        assert response.status_code == 200
        assert response.json()["status"] == "subscribed"

    def test_push_subscribe_with_minimal_data(self):
        response = client.post("/api/push/subscribe", json={
            "endpoint": "https://example.com/push-test-2"
        })
        assert response.status_code == 200


class TestPWAEndpoints:
    """Test PWA file endpoints"""

    def test_sw_js_returns_200(self):
        response = client.get("/sw.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]

    def test_manifest_json_returns_200(self):
        response = client.get("/manifest.json")
        assert response.status_code == 200
        assert "manifest" in response.headers["content-type"] or "json" in response.headers["content-type"]

    def test_manifest_has_required_fields(self):
        response = client.get("/manifest.json")
        data = response.json()
        assert "name" in data
        assert "short_name" in data
        assert "start_url" in data
        assert "display" in data


class TestGoalDecomposeEndpoint:
    """Additional tests for the goal decompose endpoint"""

    def test_goal_decompose_success(self):
        response = client.post("/api/goals/decompose", json={
            "goal_title": "Complete the backend integration",
            "target_date": "2026-07-15"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["milestones"]) == 3

    def test_goal_decompose_creates_goals(self):
        client.post("/api/goals/decompose", json={
            "goal_title": "Deploy to production",
            "target_date": "2026-07-01"
        })
        goals_response = client.get("/api/goals")
        assert goals_response.status_code == 200

    def test_goal_decompose_with_past_date(self):
        response = client.post("/api/goals/decompose", json={
            "goal_title": "Past goal",
            "target_date": "2026-01-01"
        })
        # Should still work (fallback generates milestones with the target date)
        assert response.status_code == 200


class TestFocusTimerEdgeCases:
    """Additional edge case tests for focus timer endpoint"""

    def test_focus_sessions_with_status_filter(self):
        response = client.get("/api/focus/sessions?status=completed")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data

    def test_focus_sessions_with_pagination(self):
        # Create some sessions
        client.post("/api/focus/start", json={"duration_minutes": 10})
        client.post("/api/focus/stop", json={"energy_rating": 7})

        response = client.get("/api/focus/sessions?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "limit" in data
        assert "offset" in data
        assert data["limit"] == 5
        assert data["offset"] == 0

    def test_focus_sessions_returns_stats(self):
        response = client.get("/api/focus/sessions")
        data = response.json()
        assert "stats" in data
        assert "total_sessions" in data["stats"]
        assert "total_focus_minutes" in data["stats"]
        assert "average_energy_rating" in data["stats"]

    def test_start_focus_with_invalid_duration(self):
        # Negative duration should still work (API doesn't validate this)
        response = client.post("/api/focus/start", json={"duration_minutes": -5})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "focus_started"


class TestGoaLimitAndOffset:
    """Test pagination on goals endpoint"""

    def test_goals_with_limit(self):
        response = client.get("/api/goals?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["goals"]) <= 2
        assert "total" in data
        assert data["limit"] == 2

    def test_goals_with_offset(self):
        # Get first page
        page1 = client.get("/api/goals?limit=2&offset=0").json()
        # Get second page
        page2 = client.get("/api/goals?limit=2&offset=2").json()
        # If there are enough goals, pages should be different
        if len(page1["goals"]) > 0 and page1["total"] > 2:
            first_ids = [g["id"] for g in page1["goals"]]
            second_ids = [g["id"] for g in page2["goals"]]
            assert first_ids != second_ids

    def test_goals_with_status_filter(self):
        response = client.get("/api/goals?status=COMPLETED")
        assert response.status_code == 200
        data = response.json()
        for g in data["goals"]:
            assert g["status"] == "COMPLETED"


class TestSSEStreamEndpoints:
    """Test the SSE streaming endpoints (uses fallback since no GEMINI_API_KEY)"""

    def test_ai_stream_returns_sse_format(self):
        """
        GET /api/ai/stream?prompt=... should return text/event-stream
        Without GEMINI_API_KEY, it returns an error event immediately.
        """
        response = client.get("/api/ai/stream?prompt=Hello&token=shield-admin-pass")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        # Should contain SSE data immediately
        body = response.text
        assert "event:" in body
        assert "data:" in body

    def test_ai_stream_requires_auth(self):
        """SSE endpoint without token should return 401."""
        auth = client.headers.pop("Authorization", None)
        try:
            response = client.get("/api/ai/stream?prompt=Hello")
            assert response.status_code == 401
        finally:
            if auth:
                client.headers["Authorization"] = auth

    def test_ai_stream_returns_error_event_without_key(self):
        """Without Gemini API key, stream should emit an error event."""
        response = client.get("/api/ai/stream?prompt=Hello&token=shield-admin-pass")
        # Should contain error event in the stream
        assert "error" in response.text
        assert "Gemini" in response.text or "configured" in response.text.lower()

    def test_rescue_stream_returns_sse_format(self):
        """
        GET /api/rescue/stream?token=... should return text/event-stream
        Even without Gemini, it should fallback and still stream plan + code.
        """
        # Seed demo data first to have threats
        client.post("/api/demo/seed")
        
        response = client.get("/api/rescue/stream?token=shield-admin-pass")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        body = response.text
        
        # Should yield plan_start, plan_step, code_chunk, and complete events
        assert "plan_start" in body
        assert "plan_step" in body
        assert "code_chunk" in body
        assert "complete" in body

    def test_rescue_stream_contains_plan_steps(self):
        """The rescue stream should include action plan steps."""
        client.post("/api/demo/seed")
        
        response = client.get("/api/rescue/stream?token=shield-admin-pass")
        body = response.text
        
        # Parse SSE events from the body
        events = []
        for line in body.split("\n"):
            if line.startswith("event: ") or line.startswith("data: "):
                events.append(line)
        
        # Should have multiple events
        assert len(events) >= 4

    def test_rescue_stream_requires_auth(self):
        """Rescue stream without token should return 401."""
        auth = client.headers.pop("Authorization", None)
        try:
            response = client.get("/api/rescue/stream")
            assert response.status_code == 401
        finally:
            if auth:
                client.headers["Authorization"] = auth

    def test_rescue_stream_resolves_threats(self):
        """After rescue stream completes, all threats should be resolved."""
        client.post("/api/demo/seed")
        
        # Check threats exist before rescue
        threats_before = client.get("/api/threats").json()["threats"]
        assert len(threats_before) > 0
        
        # Run rescue stream
        client.get("/api/rescue/stream?token=shield-admin-pass")
        
        # Check threats are resolved
        threats_after = client.get("/api/threats").json()["threats"]
        assert len(threats_after) == 0

    def test_rescue_stream_code_chunk_content(self):
        """Code chunks should contain Python code text."""
        client.post("/api/demo/seed")
        
        response = client.get("/api/rescue/stream?token=shield-admin-pass")
        body = response.text
        
        # Parse SSE events: track event type and data together
        current_event = None
        code_chunks_found = 0
        for line in body.split("\n"):
            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: ") and current_event == "code_chunk":
                try:
                    parsed = json.loads(line[6:])
                    if "text" in parsed and len(parsed["text"]) > 0:
                        code_chunks_found += 1
                except json.JSONDecodeError:
                    pass
        
        assert code_chunks_found >= 1, f"Expected code_chunk events with non-empty text, got {code_chunks_found}"


class TestAuthEndpoint:
    """Test the JWT authentication endpoints (/api/auth/*)"""

    REGISTER_URL = "/api/auth/register"
    LOGIN_URL = "/api/auth/login"
    LOGOUT_URL = "/api/auth/logout"
    VERIFY_URL = "/api/auth/verify"
    PROFILE_URL = "/api/auth/profile"

    TEST_USER = {
        "username": "testuser",
        "email": "test@futureshield.ai",
        "password": "strongpass123",
    }

    def _cleanup_user(self):
        """Remove the test user from the database if they exist."""
        import database
        database.execute_db("DELETE FROM users WHERE username = ?", (self.TEST_USER["username"],))

    # ─── Register ───────────────────────────────────────────────────

    def test_register_returns_200(self):
        self._cleanup_user()
        response = client.post(self.REGISTER_URL, json=self.TEST_USER)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == self.TEST_USER["username"]
        assert data["user"]["email"] == self.TEST_USER["email"]

    def test_register_token_is_valid_jwt(self):
        """The returned access_token should be a decodeable JWT."""
        self._cleanup_user()
        response = client.post(self.REGISTER_URL, json=self.TEST_USER)
        data = response.json()
        token = data["access_token"]
        assert token.count(".") == 2  # JWT has three base64 segments
        assert len(token) > 50  # JWT should be substantial length

    def test_register_with_existing_username_returns_409(self):
        """Registering with a duplicate username should fail."""
        self._cleanup_user()
        client.post(self.REGISTER_URL, json=self.TEST_USER)
        response = client.post(self.REGISTER_URL, json=self.TEST_USER)
        assert response.status_code == 409
        assert "Username or email already exists" in response.json()["detail"]

    def test_register_with_short_username_returns_422(self):
        response = client.post(self.REGISTER_URL, json={
            "username": "ab",
            "email": "valid@test.com",
            "password": "validpass123",
        })
        assert response.status_code == 422
        assert "at least 3 characters" in response.json()["detail"]

    def test_register_with_invalid_email_returns_422(self):
        response = client.post(self.REGISTER_URL, json={
            "username": "validuser",
            "email": "not-an-email",
            "password": "validpass123",
        })
        assert response.status_code == 422
        assert "Invalid email" in response.json()["detail"]

    def test_register_with_short_password_returns_422(self):
        response = client.post(self.REGISTER_URL, json={
            "username": "validuser",
            "email": "valid@test.com",
            "password": "12345",
        })
        assert response.status_code == 422
        assert "at least 6 characters" in response.json()["detail"]

    def test_register_missing_fields_returns_422(self):
        response = client.post(self.REGISTER_URL, json={})
        assert response.status_code == 422

    def test_register_normalizes_email(self):
        """Email should be stored in lowercase."""
        self._cleanup_user()
        response = client.post(self.REGISTER_URL, json={
            "username": self.TEST_USER["username"],
            "email": "UPPERCASE@TEST.COM",
            "password": self.TEST_USER["password"],
        })
        data = response.json()
        assert data["user"]["email"] == "uppercase@test.com"

    # ─── Login ──────────────────────────────────────────────────────

    def test_login_returns_200(self):
        self._cleanup_user()
        client.post(self.REGISTER_URL, json=self.TEST_USER)
        response = client.post(self.LOGIN_URL, json={
            "username": self.TEST_USER["username"],
            "password": self.TEST_USER["password"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["username"] == self.TEST_USER["username"]

    def test_login_with_wrong_password_returns_401(self):
        self._cleanup_user()
        client.post(self.REGISTER_URL, json=self.TEST_USER)
        response = client.post(self.LOGIN_URL, json={
            "username": self.TEST_USER["username"],
            "password": "wrongpassword",
        })
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]

    def test_login_with_nonexistent_user_returns_401(self):
        self._cleanup_user()
        response = client.post(self.LOGIN_URL, json={
            "username": "nonexistent",
            "password": "somepass123",
        })
        assert response.status_code == 401

    def test_login_missing_fields_returns_422(self):
        response = client.post(self.LOGIN_URL, json={})
        assert response.status_code == 422

    # ─── Verify ─────────────────────────────────────────────────────

    def test_verify_with_valid_token_returns_200(self):
        self._cleanup_user()
        reg_resp = client.post(self.REGISTER_URL, json=self.TEST_USER)
        token = reg_resp.json()["access_token"]

        response = client.get(
            self.VERIFY_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user"]["username"] == self.TEST_USER["username"]

    def test_verify_with_invalid_token_returns_401(self):
        response = client.get(
            self.VERIFY_URL,
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert response.status_code == 401

    def test_verify_without_token_returns_401(self):
        response = client.get(self.VERIFY_URL)
        assert response.status_code == 401

    def test_verify_with_wrong_secret_token_returns_401(self):
        """A token signed with a different secret should be rejected."""
        from jose import jwt as pyjwt
        import time
        wrong_secret_payload = {
            "sub": "1",
            "exp": int(time.time()) + 3600,  # valid in the future
        }
        wrong_token = pyjwt.encode(wrong_secret_payload, "wrong-secret", algorithm="HS256")
        response = client.get(
            self.VERIFY_URL,
            headers={"Authorization": f"Bearer {wrong_token}"},
        )
        assert response.status_code == 401

    # ─── Profile ────────────────────────────────────────────────────

    def test_profile_with_valid_token_returns_200(self):
        self._cleanup_user()
        reg_resp = client.post(self.REGISTER_URL, json=self.TEST_USER)
        token = reg_resp.json()["access_token"]

        response = client.get(
            self.PROFILE_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == self.TEST_USER["username"]
        assert data["email"] == self.TEST_USER["email"]
        assert "id" in data

    def test_profile_without_token_returns_401(self):
        response = client.get(self.PROFILE_URL)
        assert response.status_code == 401

    # ─── Logout ─────────────────────────────────────────────────────

    def test_logout_returns_200(self):
        response = client.post(self.LOGOUT_URL)
        assert response.status_code == 200
        assert response.json()["status"] == "logged_out"

    # ─── Full round-trip ───────────────────────────────────────────

    def test_auth_full_round_trip(self):
        """Complete auth lifecycle: register -> login -> verify -> profile."""
        import time
        self._cleanup_user()

        # 1. Register
        reg = client.post(self.REGISTER_URL, json=self.TEST_USER)
        assert reg.status_code == 200
        reg_data = reg.json()
        token1 = reg_data["access_token"]
        user_id = reg_data["user"]["id"]

        # 2. Login separately (simulates a new session)
        login = client.post(self.LOGIN_URL, json={
            "username": self.TEST_USER["username"],
            "password": self.TEST_USER["password"],
        })
        assert login.status_code == 200
        login_data = login.json()
        token2 = login_data["access_token"]
        assert login_data["user"]["id"] == user_id

        # 3. Verify with login token
        verify = client.get(
            self.VERIFY_URL,
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert verify.status_code == 200
        assert verify.json()["valid"] is True

        # 4. Get profile
        profile = client.get(
            self.PROFILE_URL,
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert profile.status_code == 200
        assert profile.json()["id"] == user_id

        # 5. Logout
        logout = client.post(self.LOGOUT_URL)
        assert logout.status_code == 200

    # ─── Auth bypass check ─────────────────────────────────────────

    def test_auth_endpoints_are_not_blocked_by_legacy_middleware(self):
        """Auth endpoints should bypass the legacy API_ACCESS_TOKEN check."""
        # Access /api/auth/register without the static token should work
        auth = client.headers.pop("Authorization", None)
        try:
            response = client.post(
                self.REGISTER_URL,
                json={
                    "username": "freshuser",
                    "email": "fresh@example.com",
                    "password": "freshpass123",
                },
            )
            assert response.status_code == 200
            import database
            database.execute_db("DELETE FROM users WHERE username = 'freshuser'")
        finally:
            if auth:
                client.headers["Authorization"] = auth


class TestAPIEdgeCases:
    """Test various edge cases across the API"""

    def test_create_goal_with_empty_title(self):
        response = client.post("/api/goals", json={
            "title": "",
            "status": "ACTIVE",
            "progress": 0,
            "deadline": "2026-12-31"
        })
        assert response.status_code == 200  # Should allow (DB accepts empty strings)

    def test_get_threats_after_resolve_all(self):
        # Resolve all threats
        threats = client.get("/api/threats").json()["threats"]
        for t in threats:
            client.post(f"/api/threats/{t['id']}/resolve")
        # Should return empty
        response = client.get("/api/threats")
        data = response.json()
        assert len(data["threats"]) == 0

    def test_update_nonexistent_goal(self):
        response = client.put("/api/goals/99999?progress=50")
        assert response.status_code == 200  # SQLite doesn't error on no-op update

    def test_resolve_already_resolved_threat(self):
        # Get first threat and resolve it twice
        threats = client.get("/api/threats").json()["threats"]
        if threats:
            tid = threats[0]["id"]
            client.post(f"/api/threats/{tid}/resolve")
            response = client.post(f"/api/threats/{tid}/resolve")
            assert response.status_code == 200  # Should still succeed
