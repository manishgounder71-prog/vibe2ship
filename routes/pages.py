"""FutureShield AI — HTML page routing and static file serving."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates

import os
from routes import _PROJECT_ROOT

router = APIRouter(tags=["Pages"])

TEMPLATES_DIR = os.path.join(_PROJECT_ROOT, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Pass config to all templates so base.html can check USE_VITE_BUNDLE
DIST_DIR = os.path.join(_PROJECT_ROOT, "dist")
USE_VITE_BUNDLE = os.path.exists(os.path.join(DIST_DIR, "assets", "fs-shared.js"))
templates.env.globals["config"] = {
    "USE_VITE_BUNDLE": USE_VITE_BUNDLE,
}

VALID_PAGES = {"index", "dashboard", "radar", "twin", "simulation", "rescue", "rag", "timeline", "analytics"}


@router.get("/")
def get_index(request: Request) -> Response:
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/{page}.html")
def get_html_page(page: str, request: Request) -> Response:
    if page not in VALID_PAGES:
        raise HTTPException(status_code=404, detail="Page not found")
    return templates.TemplateResponse(f"{page}.html", {"request": request})


@router.get("/sw.js")
def get_service_worker() -> "FileResponse":
    return FileResponse(
        os.path.join(_PROJECT_ROOT, "sw.js"),
        media_type="application/javascript",
        headers={
            "Service-Worker-Allowed": "/",
            "Cache-Control": "no-cache",
        },
    )


@router.get("/manifest.json")
def get_manifest() -> "FileResponse":
    return FileResponse(
        os.path.join(_PROJECT_ROOT, "manifest.json"),
        media_type="application/manifest+json",
    )


@router.get("/icon.svg")
def get_icon() -> "FileResponse":
    return FileResponse(
        os.path.join(_PROJECT_ROOT, "icon.svg"),
        media_type="image/svg+xml",
    )
