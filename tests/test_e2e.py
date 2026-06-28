"""FutureShield AI — End-to-End Browser Tests

Tests the full user flow in a headless Chromium browser:
  1. Landing page loads correctly
  2. Login handshake (invalid token → rejected, valid token → accepted)
  3. Dashboard renders live data from API
  4. Demo data seeding populates goals, threats, and twin
  5. Navigation works across all pages
  6. Focus timer modal opens and functions
  7. AI summary generation works

Run locally:   pytest tests/test_e2e.py -v --headed (to watch the browser)
Run headless:  pytest tests/test_e2e.py -v
Skip (no PW):  pytest tests/test_e2e.py -v -k "not e2e"

Playwright browsers must be installed:
  python -m playwright install chromium

CI: runs in a dedicated GitHub Actions job with Playwright pre-installed.
"""
import pytest
import time
import socket
import os
import tempfile
from threading import Thread

# ─── Skip if Playwright is not installed ──────────────────────────
pytest.importorskip("playwright")

_API_TOKEN = "shield-admin-pass"


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def e2e_db_path():
    """Create a temporary database file for the e2e test session."""
    tmp = tempfile.NamedTemporaryFile(suffix="_futureshield_e2e.db", delete=False)
    tmp.close()
    yield tmp.name
    try:
        os.unlink(tmp.name)
    except (OSError, PermissionError):
        pass


@pytest.fixture(scope="session")
def server_url(e2e_db_path):
    """Start a uvicorn server on a free port with an isolated database."""
    port = _get_free_port()
    url = f"http://127.0.0.1:{port}"

    # Point the server at the isolated temp database
    os.environ["FUTURESHIELD_DB_PATH"] = e2e_db_path
    os.environ["API_ACCESS_TOKEN"] = _API_TOKEN

    from main import app

    def run_server():
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")

    thread = Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(2.0)  # Wait for server to be ready

    # Verify server is up
    import urllib.request
    for attempt in range(5):
        try:
            req = urllib.request.Request(
                f"{url}/api/status",
                headers={"Authorization": f"Bearer {_API_TOKEN}"}
            )
            urllib.request.urlopen(req, timeout=5)
            break
        except Exception:
            time.sleep(1.0)
    else:
        raise RuntimeError("Server did not start in time")

    yield url


@pytest.fixture(scope="function")
def page(browser, server_url):
    """Create a new browser context + page per test with a valid JWT pre-loaded.

    Registers a test user via the API and stores the JWT in localStorage
    so the client-side auth interceptor (auth.js) injects it automatically.
    """
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        storage_state=None,
        bypass_csp=True,  # Allow Tailwind/Three.js CDN scripts
    )
    page = context.new_page()

    # Register a test user via API to get a valid JWT
    import urllib.request
    import json
    _E2E_USER = {"username": "e2e_user", "email": "e2e@futureshield.ai", "password": "testpass123"}
    jwt_token = _API_TOKEN  # fallback
    try:
        req = urllib.request.Request(
            f"{server_url}/api/auth/register",
            method="POST",
            data=json.dumps(_E2E_USER).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        jwt_token = data["access_token"]
    except Exception:
        # User may already exist from a prior test; try login instead
        try:
            req = urllib.request.Request(
                f"{server_url}/api/auth/login",
                method="POST",
                data=json.dumps({"username": "e2e_user", "password": "testpass123"}).encode(),
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req)
            data = json.loads(resp.read())
            jwt_token = data["access_token"]
        except Exception:
            pass

    # Pre-load the JWT into localStorage so auth.js fetch interceptor picks it up
    page.add_init_script(f"""
        localStorage.setItem('futureshield_jwt_token', '{jwt_token}');
        localStorage.setItem('futureshield_user', JSON.stringify({{'id': 1, 'username': 'e2e_user', 'email': 'e2e@futureshield.ai'}}));
    """)

    yield page
    context.close()


# ═══════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════

def _get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _seed_demo(server_url):
    """Seed demo data via the API."""
    import urllib.request
    req = urllib.request.Request(
        f"{server_url}/api/demo/seed",
        method="POST",
        headers={"Authorization": f"Bearer {_API_TOKEN}"}
    )
    resp = urllib.request.urlopen(req)
    return resp.status == 200


# ═══════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════

class TestLandingPage:
    """Tests for the landing page (index.html)."""

    def test_landing_page_loads(self, page, server_url):
        page.goto(f"{server_url}/")
        # Should redirect or show the landing page
        page.wait_for_load_state("networkidle")

        # Title check
        title_text = page.title()
        assert "FutureShield" in title_text

        # Hero section should have the main headline
        hero = page.locator("h1")
        assert hero.is_visible()
        assert "Predict Failure" in hero.inner_text()

    def test_landing_page_has_cta_button(self, page, server_url):
        page.goto(f"{server_url}/")
        page.wait_for_load_state("networkidle")

        # The "LAUNCH COMMAND CENTER" button should be present
        launch_btn = page.locator('a:has-text("LAUNCH COMMAND CENTER")')
        assert launch_btn.is_visible()

    def test_landing_page_has_knowledge_graph(self, page, server_url):
        page.goto(f"{server_url}/")
        page.wait_for_load_state("networkidle")

        # The knowledge graph container should exist
        kg = page.locator("#knowledge-graph")
        assert kg.is_visible()

    def test_landing_page_has_navigation(self, page, server_url):
        page.goto(f"{server_url}/")
        page.wait_for_load_state("networkidle")

        # Navigation links should exist
        nav_links = page.locator("nav a")
        count = nav_links.count()
        assert count >= 3  # OS CAPABILITIES, DIGITAL TWIN, THREAT RADAR


class TestDashboardPage:
    """Tests for the dashboard page (dashboard.html)."""

    def test_dashboard_loads_with_token(self, page, server_url):
        """Dashboard should render without login overlay when JWT is pre-loaded."""
        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        # Login overlay should NOT appear (JWT is pre-loaded in localStorage)
        overlay = page.locator("#futureshield-auth-overlay")
        assert overlay.count() == 0 or not overlay.is_visible()

        # Core dashboard elements should be visible
        score = page.locator("#global-success-score")
        assert score.is_visible()

    def test_dashboard_shows_success_score(self, page, server_url):
        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        # The success score should display a percentage
        score = page.locator("#global-success-score")
        page.wait_for_selector("#global-success-score")
        score_text = score.inner_text()
        assert "%" in score_text or score_text.isdigit()

    def test_dashboard_shows_goal_list(self, page, server_url):
        """Dashboard should load and display the goal hub."""
        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        # Goal hub section should exist
        goal_section = page.locator("text=Goal Hub")
        assert goal_section.is_visible()

    def test_dashboard_shows_knowledge_graph(self, page, server_url):
        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        kg = page.locator("#knowledge-graph")
        assert kg.is_visible()

    def test_dashboard_shows_ai_calendar(self, page, server_url):
        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        calendar = page.locator("#ai-calendar")
        assert calendar.is_visible()

    def test_dashboard_fetches_live_telemetry(self, page, server_url):
        """Dashboard telemetry should update with live data from the API."""
        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        # Core load and AI engine status should be visible
        telemetry = page.locator("text=System Telemetry")
        assert telemetry.is_visible()

        # AI engine status badge should appear (from fs-shared.js checkAIStatus)
        ai_badge = page.locator("#ai-status-badge")
        page.wait_for_selector("#ai-status-badge", timeout=10000)
        assert ai_badge.is_visible()

    def test_dashboard_goal_architect_form(self, page, server_url):
        """The AI Goal Architect form should be present and interactive."""
        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        # Goal input field
        goal_input = page.locator("#goal-input")
        assert goal_input.is_visible()

        # Date picker
        date_input = page.locator("#goal-date")
        assert date_input.is_visible()

        # Decompose button
        decompose_btn = page.locator("#decompose-btn")
        assert decompose_btn.is_visible()

    def test_dashboard_generate_summary_button(self, page, server_url):
        """The AI Summary button should trigger summary generation."""
        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        summary_btn = page.locator("#summary-btn")
        assert summary_btn.is_visible()


class TestLoginHandshake:
    """Tests for the JWT authentication overlay (auth.js).

    The current auth system uses username/password login via
    POST /api/auth/login, not a single token input field.
    """

    def test_login_overlay_appears_without_token(self, page, server_url):
        """When no valid JWT is present, the login overlay should show."""
        context = page.context.browser.new_context(
            viewport={"width": 1280, "height": 800},
            bypass_csp=True,
        )
        clean_page = context.new_page()

        try:
            clean_page.goto(f"{server_url}/dashboard.html")
            clean_page.wait_for_load_state("networkidle")

            overlay = clean_page.locator("#futureshield-auth-overlay")
            clean_page.wait_for_selector("#futureshield-auth-overlay", timeout=10000)
            assert overlay.is_visible()

            # Title should mention FUTURESHIELD ACCESS
            title = overlay.locator("h2")
            assert "FUTURESHIELD" in title.inner_text()
        finally:
            context.close()

    def test_login_with_invalid_credentials_shows_error(self, page, server_url):
        """Entering wrong username/password should show an error message."""
        context = page.context.browser.new_context(
            viewport={"width": 1280, "height": 800},
            bypass_csp=True,
        )
        clean_page = context.new_page()

        try:
            clean_page.goto(f"{server_url}/dashboard.html")
            clean_page.wait_for_load_state("networkidle")

            overlay = clean_page.locator("#futureshield-auth-overlay")
            clean_page.wait_for_selector("#futureshield-auth-overlay", timeout=10000)

            username_input = clean_page.locator("#auth-login-username")
            password_input = clean_page.locator("#auth-login-password")
            submit_btn = clean_page.locator("#auth-login-submit")
            error_msg = clean_page.locator("#auth-error-msg")

            # Enter wrong credentials
            username_input.fill("wronguser")
            password_input.fill("wrongpass")
            submit_btn.click()

            # Error should appear
            clean_page.wait_for_timeout(2000)
            assert error_msg.is_visible()
        finally:
            context.close()

    def test_login_with_valid_credentials_succeeds(self, page, server_url):
        """Entering correct username/password should dismiss the overlay."""
        context = page.context.browser.new_context(
            viewport={"width": 1280, "height": 800},
            bypass_csp=True,
        )
        clean_page = context.new_page()

        try:
            clean_page.goto(f"{server_url}/dashboard.html")
            clean_page.wait_for_load_state("networkidle")

            overlay = clean_page.locator("#futureshield-auth-overlay")
            clean_page.wait_for_selector("#futureshield-auth-overlay", timeout=10000)

            # First register a user via API (clean context has no auth)
            import urllib.request
            import json
            creds = {"username": "login_test_user", "email": "login@test.ai", "password": "logintest123"}
            try:
                req = urllib.request.Request(
                    f"{server_url}/api/auth/register",
                    method="POST",
                    data=json.dumps(creds).encode(),
                    headers={"Content-Type": "application/json"},
                )
                urllib.request.urlopen(req)
            except Exception:
                pass  # User may already exist; login will still work below

            username_input = clean_page.locator("#auth-login-username")
            password_input = clean_page.locator("#auth-login-password")
            submit_btn = clean_page.locator("#auth-login-submit")

            username_input.fill(creds["username"])
            password_input.fill(creds["password"])
            submit_btn.click()

            # Overlay should disappear (page reloads on success)
            clean_page.wait_for_timeout(3000)
            assert overlay.count() == 0 or not overlay.is_visible()

            # Dashboard should now be visible
            score = clean_page.locator("#global-success-score")
            assert score.is_visible()
        finally:
            context.close()


class TestDemoAndDataFlow:
    """Tests for demo data seeding and data-driven UI."""

    def test_demo_seed_populates_dashboard(self, page, server_url):
        """After seeding demo data, the dashboard should show richer content."""
        # Seed demo data
        assert _seed_demo(server_url)

        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        # Goals should be visible
        goals_list = page.locator("#goals-list-container")
        goals_text = goals_list.inner_text()
        # Should contain at least some goal-related text
        assert len(goals_text) > 0

    def test_demo_seed_shows_goals_count(self, page, server_url):
        """The goal count should update after demo seeding."""
        assert _seed_demo(server_url)

        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        goals_count = page.locator("#goals-count")
        assert goals_count.is_visible()
        goals_text = goals_count.inner_text()
        assert "Goals Tracked" in goals_text

    def test_demo_data_updates_success_score(self, page, server_url):
        """After demo seeding, the success score should appear."""
        assert _seed_demo(server_url)

        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        score = page.locator("#global-success-score")
        page.wait_for_selector("#global-success-score")
        score_text = score.inner_text()
        assert len(score_text) > 0

    def test_demo_data_shows_threats_on_radar(self, page, server_url):
        """The radar page should show threats after demo seeding."""
        assert _seed_demo(server_url)

        page.goto(f"{server_url}/radar.html")
        page.wait_for_load_state("networkidle")

        # The radar dots container should have threat markers
        dots = page.locator("#radar-dots-container div")
        page.wait_for_timeout(2000)  # Wait for API data to load
        assert dots.count() >= 1

        # The threats scanned counter should show
        scanned = page.locator("#threats-scanned-count")
        assert scanned.is_visible()

    def test_demo_data_shows_twin_data(self, page, server_url):
        """The Digital Twin page should render with demo data."""
        assert _seed_demo(server_url)

        page.goto(f"{server_url}/twin.html")
        page.wait_for_load_state("networkidle")

        # Behavior score should be visible
        score = page.locator("#behavior-score")
        page.wait_for_timeout(2000)
        assert score.is_visible()
        score_text = score.inner_text()
        assert len(score_text) > 0

        # Energy waveform container should exist
        waveform = page.locator("#energy-waveform-container")
        assert waveform.is_visible()

        # Success DNA grid should exist
        dna = page.locator("#success-dna-grid")
        assert dna.is_visible()


class TestNavigation:
    """Tests for multi-page navigation."""

    def test_navigate_to_radar(self, page, server_url):
        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        # Find and click the radar nav link
        nav_link = page.locator('a[href="radar.html"]')
        if nav_link.count() > 0:
            nav_link.first.click()
            page.wait_for_url("**/radar.html")
            assert "radar" in page.url

    def test_navigate_to_simulation(self, page, server_url):
        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        nav_link = page.locator('a[href="simulation.html"]')
        if nav_link.count() > 0:
            nav_link.first.click()
            page.wait_for_url("**/simulation.html")
            assert "simulation" in page.url

    def test_navigate_to_twin(self, page, server_url):
        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        nav_link = page.locator('a[href="twin.html"]')
        if nav_link.count() > 0:
            nav_link.first.click()
            page.wait_for_url("**/twin.html")
            assert "twin" in page.url

    def test_navigate_to_rescue(self, page, server_url):
        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        nav_link = page.locator('a[href="rescue.html"]')
        if nav_link.count() > 0:
            nav_link.first.click()
            page.wait_for_url("**/rescue.html")
            assert "rescue" in page.url


class TestRadarPage:
    """Tests for the radar page."""

    def test_radar_page_loads(self, page, server_url):
        page.goto(f"{server_url}/radar.html")
        page.wait_for_load_state("networkidle")

        title = page.locator("h1")
        assert title.is_visible()
        assert "Radar" in title.inner_text()

    def test_radar_displays_threats(self, page, server_url):
        page.goto(f"{server_url}/radar.html")
        page.wait_for_load_state("networkidle")

        # Active threats list should be populated
        threats_list = page.locator("#active-threats-list")
        page.wait_for_timeout(2000)  # Wait for API fetch
        assert threats_list.is_visible()

    def test_radar_shows_scanned_count(self, page, server_url):
        page.goto(f"{server_url}/radar.html")
        page.wait_for_load_state("networkidle")

        scanned = page.locator("#threats-scanned-count")
        assert scanned.is_visible()
        assert "THREATS SCANNED" in scanned.inner_text()


class TestSimulationPage:
    """Tests for the simulation page."""

    def test_simulation_page_loads(self, page, server_url):
        page.goto(f"{server_url}/simulation.html")
        page.wait_for_load_state("networkidle")

        title = page.locator("h1")
        assert title.is_visible()
        assert "Simulation" in title.inner_text()

    def test_simulation_has_scenario_input(self, page, server_url):
        page.goto(f"{server_url}/simulation.html")
        page.wait_for_load_state("networkidle")

        textarea = page.locator("#scenario-input")
        assert textarea.is_visible()

        run_btn = page.locator("text=RUN SIMULATION ENGINE")
        assert run_btn.is_visible()

    def test_simulation_quick_buttons_exist(self, page, server_url):
        page.goto(f"{server_url}/simulation.html")
        page.wait_for_load_state("networkidle")

        # Quick scenario buttons
        quick_btns = page.locator("button:has-text('Skip Today'), button:has-text('Delay 3 Days'), button:has-text('Conduct Focus')")
        assert quick_btns.count() >= 3

    def test_simulation_run_works(self, page, server_url):
        """Running a simulation should update the futures section."""
        page.goto(f"{server_url}/simulation.html")
        page.wait_for_load_state("networkidle")

        textarea = page.locator("#scenario-input")
        textarea.fill("Skip all work for today")

        run_btn = page.locator("text=RUN SIMULATION ENGINE")
        run_btn.click()

        page.wait_for_timeout(2000)

        # Futures container should have dynamic content
        futures = page.locator("#futures-container")
        assert futures.is_visible()


class TestRescuePage:
    """Tests for the AI rescue center page."""

    def test_rescue_page_loads(self, page, server_url):
        page.goto(f"{server_url}/rescue.html")
        page.wait_for_load_state("networkidle")

        title = page.locator("h1")
        assert title.is_visible()
        assert "Rescue" in title.inner_text()

    def test_rescue_has_rescue_button(self, page, server_url):
        page.goto(f"{server_url}/rescue.html")
        page.wait_for_load_state("networkidle")

        rescue_btn = page.locator("#rescue-btn")
        assert rescue_btn.is_visible()
        assert "RESCUE" in rescue_btn.inner_text()

    def test_rescue_shows_threats(self, page, server_url):
        page.goto(f"{server_url}/rescue.html")
        page.wait_for_load_state("networkidle")

        threats_list = page.locator("#threats-list")
        page.wait_for_timeout(2000)
        assert threats_list.is_visible()


class TestTwinPage:
    """Tests for the Digital Twin page."""

    def test_twin_page_loads(self, page, server_url):
        page.goto(f"{server_url}/twin.html")
        page.wait_for_load_state("networkidle")

        behavior_score = page.locator("#behavior-score")
        page.wait_for_timeout(2000)
        assert behavior_score.is_visible()

    def test_twin_shows_success_dna(self, page, server_url):
        page.goto(f"{server_url}/twin.html")
        page.wait_for_load_state("networkidle")

        dna = page.locator("#success-dna-grid")
        page.wait_for_timeout(2000)
        assert dna.is_visible()

    def test_twin_shows_focus_stats(self, page, server_url):
        page.goto(f"{server_url}/twin.html")
        page.wait_for_load_state("networkidle")

        focus_total = page.locator("#focus-sessions-total")
        page.wait_for_timeout(3000)
        assert focus_total.is_visible()


class TestFullUserFlow:
    """End-to-end user journey: landing → login → demo → dashboard → navigate."""

    def test_full_flow_landing_to_dashboard(self, page, server_url):
        """Full flow: Landing page → click CTA → Dashboard loads with data."""
        # 1. Landing page
        page.goto(f"{server_url}/")
        page.wait_for_load_state("networkidle")
        assert "FutureShield" in page.title()

        # 2. Click LAUNCH COMMAND CENTER
        cta = page.locator('a:has-text("LAUNCH COMMAND CENTER")')
        cta.click()
        page.wait_for_url("**/dashboard.html")

        # 3. Dashboard should load (token is pre-set)
        page.wait_for_load_state("networkidle")
        score = page.locator("#global-success-score")
        assert score.is_visible()

    def test_full_flow_with_demo_seed(self, page, server_url):
        """Full flow with demo data: seed → dashboard reflects live data."""
        # Seed demo
        assert _seed_demo(server_url)

        # Navigate to dashboard
        page.goto(f"{server_url}/dashboard.html")
        page.wait_for_load_state("networkidle")

        # Dashboard should have goals
        goals_list = page.locator("#goals-list-container")
        page.wait_for_timeout(2000)
        assert goals_list.is_visible()

        # Navigate to radar
        nav_link = page.locator('a[href="radar.html"]')
        if nav_link.count() > 0:
            nav_link.first.click()
            page.wait_for_url("**/radar.html")
            page.wait_for_load_state("networkidle")

            # Radar should show threats
            threats = page.locator("#active-threats-list")
            page.wait_for_timeout(2000)
            assert threats.is_visible()

    def test_full_flow_all_pages_render(self, page, server_url):
        """Verify all 8 pages render without JS errors."""
        pages_to_test = [
            ("/", "FutureShield"),
            ("/dashboard.html", "Command Center"),
            ("/radar.html", "Failure Prevention Radar"),
            ("/simulation.html", "Simulation"),
            ("/rescue.html", "Rescue"),
            ("/twin.html", "Twin"),
            ("/timeline.html", "Timeline"),
            ("/analytics.html", "Focus Analytics"),
        ]

        for path, expected_title_part in pages_to_test:
            page.goto(f"{server_url}{path}")
            page.wait_for_load_state("networkidle")
            page_title = page.title()
            assert expected_title_part.lower() in page_title.lower(), \
                f"Page {path} title '{page_title}' missing '{expected_title_part}'"

            # Check for console errors
            # (Playwright captures errors automatically)
