# Contributing to FutureShield AI

## Getting Started

```bash
# Clone and setup
git clone <repo-url>
cd FutureShieldAI
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Copy environment config (edit with your values)
cp .env.example .env

# Run the dev server
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

## Project Architecture

```
main.py              Entry point — FastAPI app, middleware, startup
routes/              12 route modules (status, threats, goals, twin, etc.)
database.py          SQLite wrapper with context manager
rag.py               RAG engine (ChromaDB + pure-Python fallback)
shared/              Frontend JS modules & CSS
templates/           Jinja2 HTML templates
tests/               pytest test suite (235+ tests)
```

## Frontend Script Modules

The `shared/` directory contains modular JavaScript files loaded in order by `base.html`:

| File | Purpose |
|------|---------|
| `fs-shared.js` | Core: WebGL shader, skeleton loader, parallax, init orchestrator |
| `auth.js` | Auth: fetch interceptor, token handshake, login overlay |
| `ui.js` | UI: toast notifications, confirm dialog, keyboard shortcuts, breadcrumb, AI status |
| `demo.js` | Demo: guided 5-step tour, CTA button |
| `voice-assistant.js` | Voice: Web Speech API command recognition |
| `focus-timer.js` | Timer: Pomodoro-style focus timer with energy rating |

All modules attach to the `window.FutureShield` namespace and are loaded **before** `DOMContentLoaded`, so `fs-shared.js`'s `init()` function can safely call any function defined in other modules.

## Making Changes

### Adding a new page
1. Create `templates/your-page.html` extending `base.html`
2. Add the route in `routes/pages.py`
3. Wire up API endpoints in a new `routes/your-module.py`

### Adding a new API endpoint
1. Create or edit a route file in `routes/`
2. Import `router` and register it via `app.include_router()` in `main.py`
3. Add tests in `tests/test_api.py`

## Testing

```bash
# Run all tests (CI equivalent)
pytest tests/ -v --tb=short

# Run only API tests (fastest feedback loop)
pytest tests/test_api.py -v --tb=short

# Run database unit tests
pytest tests/test_database.py -v

# Run RAG engine tests
pytest tests/test_rag.py -v

# Run end-to-end browser tests
pytest tests/test_e2e.py -v
```

### Test Conventions
- API tests use the `api_client` fixture (authenticated TestClient)
- Database tests get an isolated temp DB via `use_test_database` fixture
- RAG tests use fresh `RAGEngine` instances with the pure-Python fallback
- All tests run in CI on every push

## Code Conventions

- **Python**: Type annotations required on route functions, Pydantic models
- **JavaScript**: ES5-compatible syntax (no arrow functions, const/let sparingly)
- **CSS**: Use Tailwind utility classes; add custom styles to `shared/style.css`
- **HTML**: Jinja2 templates extending `base.html` with `{% block %}` overrides

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `API_ACCESS_TOKEN` | Yes | Bearer token for API auth |
| `GEMINI_API_KEY` | No | Google Gemini API key (AI features fall back gracefully) |
| `FUTURESHIELD_DB_PATH` | No | Custom SQLite path (defaults to `database.db`) |

**Important**: `load_dotenv()` in `main.py` must run before importing `routes` (the bootstrap race condition fix). The `.env.example` file documents this ordering.

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push:

1. **Test & Lint**: flake8 → mypy → pytest (skipping e2e)
2. **E2E Tests**: Playwright browser tests (depends on test job)
3. **Docker Build**: Builds container image with layer caching
4. **Deploy**: (main branch only) Pushes to Google Cloud Run
