"""
app.py — FastAPI carousel generator + React frontend.

API routes
  POST /generate-hooks  { "content": "...", "language": "spanish" }  → { "hooks": [...] }
  POST /render          { "slides": [...], "language": "spanish" }    → { "images": [...], "run_id": "..." }
  GET  /healthz         → { "status": "ok" }

Frontend (SPA)
  GET  /          → React app (index.html)
  GET  /assets/*  → JS/CSS bundles
  GET  /renders/* → rendered slide PNGs (served from /tmp/renders/)
"""

import logging
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, model_validator

load_dotenv()

from utils import setup_logging
from generator import generate_hooks, generate_caption
from renderer import render_slides

setup_logging(os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger("carousel.api")
print("Starting FastAPI server...")

app = FastAPI(title="Carousel Generator API", version="3.0.0")

DIST        = Path(__file__).parent / "frontend" / "dist"
RENDERS_DIR = Path("/tmp/renders")
RENDERS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SlideData(BaseModel):
    type: Literal["first", "content", "translate", "last"]
    text_main: str = ""
    text_cursive: str = ""
    text_secondary: str = ""
    underline: str = ""
    left_text: str = ""
    right_text: str = ""


class HooksRequest(BaseModel):
    content: str
    language: str = "spanish"


class HooksResponse(BaseModel):
    hooks: list[str]


class RenderRequest(BaseModel):
    slides: list[SlideData]
    language: str = "spanish"

    @model_validator(mode="after")
    def validate_slide_count(self):
        if not (4 <= len(self.slides) <= 10):
            raise ValueError("slides must contain between 4 and 10 items")
        return self


class RenderResponse(BaseModel):
    images: list[str]
    run_id: str
    caption: str = ""


# ---------------------------------------------------------------------------
# API routes  -- registered before static file mounts
# ---------------------------------------------------------------------------

@app.get("/healthz", tags=["meta"])
def healthz():
    return {"status": "ok"}


@app.post("/generate-hooks", response_model=HooksResponse, tags=["carousel"])
def generate_hooks_endpoint(req: HooksRequest):
    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="content must not be empty")

    try:
        hooks = generate_hooks(content, req.language)
    except Exception as exc:
        logger.error("Hook generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Hook generation failed: {exc}")

    return HooksResponse(hooks=hooks)


@app.post("/render", response_model=RenderResponse, tags=["carousel"])
def render_endpoint(req: RenderRequest):
    slides_dicts = [s.model_dump() for s in req.slides]
    # Propagate language into each slide so the renderer can select the correct flag
    for slide in slides_dicts:
        slide["language"] = req.language

    try:
        png_paths, run_id = render_slides(slides_dicts, renders_base=str(RENDERS_DIR))
    except Exception as exc:
        logger.error("Rendering failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Rendering failed: {exc}")

    # Generate caption (non-fatal — empty string on failure)
    caption = ""
    try:
        caption = generate_caption(slides_dicts)
    except Exception as exc:
        logger.warning("Caption generation failed (non-fatal): %s", exc)

    image_urls = [f"/renders/{run_id}/slide-{i + 1}.png" for i in range(len(png_paths))]
    logger.info("Render complete: %d images for run %s", len(image_urls), run_id)
    return RenderResponse(images=image_urls, run_id=run_id, caption=caption)


# ---------------------------------------------------------------------------
# Rendered PNGs  (/renders/<run_id>/slide-n.png)
# ---------------------------------------------------------------------------

app.mount("/renders", StaticFiles(directory=str(RENDERS_DIR)), name="renders")


# ---------------------------------------------------------------------------
# Frontend static assets (/assets/index-abc123.js, etc.)
# ---------------------------------------------------------------------------

_assets = DIST / "assets"
if _assets.exists():
    app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")
    logger.info("Serving frontend assets from %s", _assets)
else:
    logger.warning("frontend/dist/assets not found -- run: cd frontend && npm run build")


# ---------------------------------------------------------------------------
# SPA catch-all  (must be last -- after all mounts)
# ---------------------------------------------------------------------------

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    index = DIST / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return HTMLResponse(
        content=(
            "<h2>Frontend not built</h2>"
            "<p>Run <code>cd frontend &amp;&amp; npm run build</code> "
            "then restart the server.</p>"
            "<p>API docs: <a href='/docs'>/docs</a></p>"
        ),
        status_code=503,
    )


# ---------------------------------------------------------------------------
# Local dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port)
