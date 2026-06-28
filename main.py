"""
FutureShield AI — FastAPI Application Factory

Assembles the app by importing all route modules, adding middleware,
and running startup initialization.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

# Load local environment variables BEFORE importing routes
load_dotenv()

from routes import API_ACCESS_TOKEN, _PROJECT_ROOT

# =========================================================================
# App creation
# =========================================================================

app = FastAPI(title="FutureShield AI Backend")

# CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================================
# API Access Token middleware (legacy backward compat & non-auth endpoints)
# =========================================================================

@app.middleware("http")
async def validate_api_access_token(request: Request, call_next):
    if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/auth/"):
        if request.method == "OPTIONS":
            return await call_next(request)

        # SSE endpoints accept token via query param (EventSource can't set headers)
        if request.method == "GET":
            token_qs = request.query_params.get("token", "")
            if token_qs and token_qs == API_ACCESS_TOKEN:
                return await call_next(request)

        auth_header = request.headers.get("Authorization")
        valid = False
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            # Check shared API token first (legacy/backward compat)
            if token == API_ACCESS_TOKEN:
                valid = True
            else:
                # Also accept valid JWT tokens (user-authenticated requests)
                try:
                    from routes.auth import _decode_token
                    _decode_token(token)
                    valid = True
                except Exception:
                    valid = False

        if not valid:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing FutureShield security token."},
            )

    return await call_next(request)


# =========================================================================
# Static files mount
# =========================================================================

app.mount("/shared", StaticFiles(directory=os.path.join(_PROJECT_ROOT, "shared")), name="shared")

# Vite build output (served from dist/ at /dist/assets/)
dist_dir = os.path.join(_PROJECT_ROOT, "dist")
if os.path.exists(dist_dir):
    app.mount("/dist", StaticFiles(directory=dist_dir), name="dist")

# =========================================================================
# Import and register route modules
# =========================================================================

from routes.ai import router as ai_router
from routes.auth import router as auth_router
from routes.status import router as status_router
from routes.threats import router as threats_router
from routes.twin import router as twin_router
from routes.demo import router as demo_router
from routes.goals import router as goals_router
from routes.simulation import router as simulation_router
from routes.rescue import router as rescue_router
from routes.focus import router as focus_router
from routes.notifications import router as notifications_router
from routes.pages import router as pages_router
from routes.summary import router as summary_router
from routes.rag import router as rag_router
from routes.timeline import router as timeline_router
from routes.analytics import router as analytics_router

app.include_router(ai_router)
app.include_router(auth_router)
app.include_router(status_router)
app.include_router(threats_router)
app.include_router(twin_router)
app.include_router(demo_router)
app.include_router(goals_router)
app.include_router(simulation_router)
app.include_router(rescue_router)
app.include_router(focus_router)
app.include_router(notifications_router)
app.include_router(pages_router)
app.include_router(summary_router)
app.include_router(rag_router)
app.include_router(timeline_router)
app.include_router(analytics_router)

# =========================================================================
# Startup
# =========================================================================

import database
import rag


@app.on_event("startup")
def startup_event():
    database.init_db()
    rag_engine = rag.init_engine()
    if rag_engine:
        print("[INFO] RAG engine initialized with vector store")
    else:
        print("[INFO] RAG engine not available (chromadb may not be installed)")
