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
