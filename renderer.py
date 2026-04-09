"""
renderer.py -- HTML template injection + Playwright PNG rendering.

Pipeline
--------
  1. inject_slide(index, slide, total)  -> HTML string
  2. render_slides(slides)              -> (png_paths, run_id)

Template mapping
----------------
  index 0          -> slide-first.html
  index 1 to n-2   -> slide-content.html or slide-translate.html
  index n-1        -> slide-last.html

Placeholders
------------
  {{TEXT}}        -- raw HTML; bold/italic markdown converted before injection
  {{LEFT_TEXT}}   -- translate slide left column
  {{RIGHT_TEXT}}  -- translate slide right column
  {{FLAG_BLOCK}}  -- content slide flag element (language-driven); empty string when no flag

Output
------
  PNG files are written to /tmp/renders/<run_id>/slide-{n}.png.
  The run_id is returned so the caller can build /renders/<run_id>/slide-n.png URLs.
"""

import logging
import os
import re
import shutil
import uuid
from pathlib import Path

logger = logging.getLogger("carousel.renderer")

_ROOT = Path(__file__).parent   # project root (templates live here)

_FLAG_MAP = {
    "spanish": "spain.png",
    "italian": "italy.png",
}

_LAST_SLIDE_DEFAULT = (
    '<div class="title">'
    'Follow along and start sounding '
    '<div class="accent">native</div>'
    '</div>'
)


# ---------------------------------------------------------------------------
# Markdown → HTML (bold + italic)
# ---------------------------------------------------------------------------

def _md_to_html(text: str) -> str:
    """Convert markdown bold/italic markers to inline HTML.

    **text** → <strong>text</strong>
    *text*   → <em>text</em>

    Bold is processed first so the double-asterisks in **bold** are consumed
    before the single-asterisk italic pass runs.
    """
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*]+?)\*',   r'<em>\1</em>',        text)
    return text


# ---------------------------------------------------------------------------
# Step 1: HTML injection
# ---------------------------------------------------------------------------

def _normalise_slide(slide: dict) -> dict:
    """Map new schema fields (text_main/text_secondary) to legacy heading/description.

    Accepts both old schema (heading/description) and new schema (text_main/...).
    Old-schema dicts pass through unchanged for backward compatibility.
    """
    if "text_main" in slide:
        return {
            **slide,
            "heading":     slide.get("text_main", ""),
            "description": slide.get("text_secondary", ""),
        }
    return slide


def inject_slide(index: int, slide: dict, total: int) -> str:
    """Inject slide data into the appropriate HTML template.

    Parameters
    ----------
    index : int   0-based position in the slide list.
    slide : dict  Must contain "heading" for standard slides, or
                  "left_text"/"right_text" for translate slides.
    total : int   Total number of slides (determines which index is the last).
    """
    slide      = _normalise_slide(slide)
    last_index = total - 1

    # --- Translate slide ---
    if slide.get("type") == "translate":
        left_text  = (slide.get("left_text")  or "").strip()
        right_text = (slide.get("right_text") or "").strip()

        template_path = _ROOT / "slide-translate.html"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        html = template_path.read_text(encoding="utf-8")
        html = html.replace("{{LEFT_TEXT}}", left_text)
        html = html.replace("{{RIGHT_TEXT}}", right_text)
        return html

    # --- Standard slides (first / content / last) ---
    heading     = (slide.get("heading")     or "").strip()
    description = (slide.get("description") or "").strip()

    if description:
        text = f"{_md_to_html(heading)}<br>{_md_to_html(description)}"
    else:
        text = _md_to_html(heading)

    if index == 0:
        template_name = "slide-first.html"
    elif index == last_index:
        template_name = "slide-last.html"
        # Default content when the user left the last slide empty
        if not text:
            text = _LAST_SLIDE_DEFAULT
    else:
        template_name = "slide-content.html"

    template_path = _ROOT / template_name
    if not template_path.exists():
        raise FileNotFoundError(
            f"Template not found: {template_path}. "
            "Ensure slide-first.html, slide-content.html, and slide-last.html "
            "exist in the project root."
        )

    html = template_path.read_text(encoding="utf-8")
    html = html.replace("{{TEXT}}", text)

    # Inject flag block for content slides
    if template_name == "slide-content.html":
        lang     = (slide.get("language") or "").lower()
        flag_src = _FLAG_MAP.get(lang, "")
        if flag_src:
            flag_block = f'<div class="flag"><img src="{flag_src}" alt="flag"></div>'
        else:
            flag_block = ""
        html = html.replace("{{FLAG_BLOCK}}", flag_block)

    return html


# ---------------------------------------------------------------------------
# Step 2: Playwright rendering
# ---------------------------------------------------------------------------

def render_slides(
    slides: list[dict],
    renders_base: str = "/tmp/renders",
) -> tuple[list[str], str]:
    """
    Render slides to PNG files using Playwright (Chromium headless).

    Returns
    -------
    png_paths : list[str]   Absolute paths to the rendered PNGs, in order.
    run_id    : str         UUID subdir name (for building /renders/<id>/ URLs).
    """
    from playwright.sync_api import sync_playwright, Error as PlaywrightError

    n = len(slides)
    if not (4 <= n <= 10):
        raise ValueError(f"Expected 4–10 slides, got {n}")

    run_id  = uuid.uuid4().hex
    out_dir = Path(renders_base) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Render run %s -> %s", run_id, out_dir)

    # Copy static assets so relative paths in templates resolve correctly
    for asset in ["logo.png", "spain.png", "italy.png"]:
        src = _ROOT / asset
        if src.exists():
            shutil.copy2(src, out_dir / asset)
        else:
            logger.warning("Asset not found: %s", src)

    # Write HTML files
    html_paths: list[Path] = []
    for i, slide in enumerate(slides):
        html      = inject_slide(i, slide, total=n)
        html_path = out_dir / f"slide-{i + 1}.html"
        html_path.write_text(html, encoding="utf-8")
        html_paths.append(html_path)
        slide_role = "first" if i == 0 else ("last" if i == n - 1 else "content")
        logger.debug(
            "Slide %d/%d (%s) — type: %s | text: %r | file: %s",
            i + 1, n, slide_role,
            slide.get("type", "unknown"),
            (slide.get("text_main") or slide.get("heading", ""))[:60],
            html_path.name,
        )

    # Screenshot each slide
    png_paths: list[str] = []
    try:
        with sync_playwright() as pw:
            # --no-sandbox / --disable-setuid-sandbox: required in Railway/Docker
            #   because the process runs as root inside the container.
            # --disable-dev-shm-usage: /dev/shm is often only 64 MB in containers;
            #   without this flag Chromium crashes on memory-intensive pages.
            browser = pw.chromium.launch(
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            try:
                context = browser.new_context(
                    viewport={"width": 1080, "height": 1080},
                    device_scale_factor=2,
                )
                for i, html_path in enumerate(html_paths):
                    page = context.new_page()
                    try:
                        url = f"file://{html_path.absolute()}"
                        logger.debug("Loading slide %d — %s", i + 1, url)
                        # Use domcontentloaded (not networkidle) — networkidle blocks on
                        # Google Fonts CDN URLs which contain @ and ; characters that
                        # trigger Playwright's internal URL pattern matcher.
                        page.goto(url, wait_until="domcontentloaded", timeout=15_000)
                        # Wait for fonts — resolves even if CDN is unreachable,
                        # falling back to the system font stack defined in the templates.
                        try:
                            page.evaluate("document.fonts.ready")
                        except Exception as font_exc:
                            logger.warning(
                                "Slide %d: font loading skipped (%s) — "
                                "fallback fonts will be used",
                                i + 1, font_exc,
                            )
                        png_path = out_dir / f"slide-{i + 1}.png"
                        logger.debug("Screenshotting slide %d → %s", i + 1, png_path.name)
                        # Target the .slide element directly — avoids any body/viewport
                        # whitespace and guarantees a clean 1080×1080 crop.
                        slide_el = page.query_selector(".slide")
                        if slide_el is None:
                            raise RuntimeError(f"Slide {i + 1}: .slide element not found in template")
                        slide_el.screenshot(path=str(png_path))
                        png_paths.append(str(png_path))
                        logger.info("Rendered slide %d/%d", i + 1, len(slides))
                    except PlaywrightError as exc:
                        raise RuntimeError(f"Playwright error on slide {i + 1}: {exc}") from exc
                    finally:
                        page.close()
            finally:
                browser.close()
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Rendering failed: {exc}") from exc

    # Clean up HTML intermediates (keep only PNGs)
    for hp in html_paths:
        try:
            hp.unlink()
        except OSError:
            pass

    logger.info("Render complete: %d PNGs in run %s", len(png_paths), run_id)
    return png_paths, run_id
