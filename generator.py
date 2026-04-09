"""
generator.py — AI hook generation for MFL Instagram carousels.

Public API
----------
generate_hooks(content_summary, language) → list[str]
    Returns 3-5 short hook options in MFL style (MISTAKE, REVEAL, CONTRAST,
    PHRASE, SCENARIO) based on the user-provided slide content.
"""

import json
import logging
import os

logger = logging.getLogger("carousel.generator")

# ---------------------------------------------------------------------------
# Anthropic client
# ---------------------------------------------------------------------------

def _get_anthropic_client():
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    return anthropic.Anthropic(api_key=api_key)


def _generate_anthropic(system_prompt: str, user_message: str) -> str:
    """Call Claude and return the raw text response."""
    client = _get_anthropic_client()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text.strip()


# ---------------------------------------------------------------------------
# Hook generation
# ---------------------------------------------------------------------------

_HOOKS_SYSTEM_PROMPT = """\
You are a content strategist for MFL Media, an Instagram account that teaches \
Spanish and Italian to English speakers. You write punchy, scroll-stopping hooks \
for educational carousels.

Your task: given a summary of a carousel's content and the target language, \
return exactly 5 hook options — one for each of these styles:

1. MISTAKE   — Call out the common error English speakers make. Make the reader \
feel they've been saying it wrong.
   Example: "English speakers say this **wrong** in Spanish every time"

2. REVEAL    — Tease a phrase or pattern most learners don't know. Create a gap \
the reader wants to close.
   Example: "There's a phrase every Spanish shopper uses — most learners **never** learn it"

3. CONTRAST  — Contrast what learners are taught vs. what natives actually say.
   Example: "Your Spanish teacher taught you **wrong**"

4. PHRASE    — Lead with the target-language phrase itself as the hook.
   Example: "Solo estoy mirando — say **this** next time"

5. SCENARIO  — Drop the reader into a real situation where they'd need this phrase.
   Example: "You're in a Spanish café — do you know what to say?"

Rules:
- Each hook must be under 10 words
- Use **word** markdown for one bold emphasis per hook (optional but encouraged)
- Hooks must be specific to the content summary — no generic filler
- Match the target language (Spanish or Italian) in tone and any embedded phrases

Return ONLY a valid JSON array of 5 strings, no wrapper object, no explanation:
["hook 1", "hook 2", "hook 3", "hook 4", "hook 5"]
"""


def generate_hooks(content_summary: str, language: str) -> list[str]:
    """Return 3-5 short hook options in MFL style.

    Parameters
    ----------
    content_summary : str   The combined slide content or topic description.
    language        : str   "spanish" or "italian".

    Returns
    -------
    list[str]   5 hook strings (one per style), each under 10 words.
    """
    user_message = (
        f"Content summary: {content_summary}\n"
        f"Target language: {language.capitalize()}\n\n"
        "Return 5 hook options as a JSON array."
    )

    raw = _generate_anthropic(_HOOKS_SYSTEM_PROMPT, user_message)

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        hooks = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse hooks response as JSON: {exc}\nRaw: {raw[:200]}") from exc

    if not isinstance(hooks, list) or not all(isinstance(h, str) for h in hooks):
        raise ValueError(f"Expected a JSON array of strings, got: {type(hooks)}")

    return hooks


# ---------------------------------------------------------------------------
# Caption generation
# ---------------------------------------------------------------------------

_CAPTION_SYSTEM_PROMPT = """\
You write Instagram captions for MFL Media, an account that teaches Spanish and \
Italian to English speakers. Your captions are warm, encouraging, and teacher-like — \
never cold, robotic, or salesy.

Structure every caption exactly like this:
1. One strong, friendly hook line (curiosity or relatable moment)
2. One or two short lines explaining what the learner will get from this post
3. An optional gentle CTA (save, share, or come back to it)
4. A blank line, then 3–5 relevant hashtags on one line
5. A blank line, then exactly: "Follow @tutor_mia_mfl for daily phrases"

Rules:
- Keep it concise — no more than 6 lines before the hashtags
- Tone: warm, human, educational (like a friendly tutor, not a brand)
- Use "you" to speak directly to the learner
- Hashtags: choose from #languagelearning #spanish #italian #learnlanguages \
  #learningspanish #learningitalian #mfl — do NOT use #french
- End line must be exactly: Follow @tutor_mia_mfl for daily phrases
- Return plain text only — no markdown, no labels, no preamble
"""


def generate_caption(slides: list[dict]) -> str:
    """Generate an Instagram caption from the slide content.

    Parameters
    ----------
    slides : list[dict]   Slide dicts (new text_main schema or legacy heading schema).

    Returns
    -------
    str   Ready-to-post Instagram caption.
    """
    parts = []
    for s in slides:
        slide_type = s.get("type", "")
        if slide_type == "translate":
            left  = (s.get("left_text")  or "").strip()
            right = (s.get("right_text") or "").strip()
            if left or right:
                parts.append(f"{left} / {right}")
        else:
            text = (s.get("text_main") or s.get("heading") or "").strip()
            if text:
                parts.append(text)

    content_summary = "\n".join(parts) if parts else "language learning tips"

    return _generate_anthropic(
        _CAPTION_SYSTEM_PROMPT,
        f"Write a caption for this carousel:\n\n{content_summary}",
    )
