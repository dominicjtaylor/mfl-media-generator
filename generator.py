"""
generator.py — LLM-powered slide generation for MFL Instagram carousels.

Supports both Anthropic (default) and OpenAI backends, selected via the
LLM_PROVIDER env var ("anthropic" | "openai").

Public API
----------
generate_slides(topic) → (list[dict], str)
    Returns (slides, caption) where slides is a list of dicts with
    "type", "heading", and "description" keys (4–7 slides), and caption
    is a ready-to-post Instagram caption string.
    "type" is one of: "hook", "content", "translate", "cta".
"""

import json
import logging
import os
import random
import re
import time
from typing import Optional

logger = logging.getLogger("carousel.generator")

# ---------------------------------------------------------------------------
# Word limits by slide type
# ---------------------------------------------------------------------------

WORD_LIMITS = {
    "hook":      8,
    "content":  22,   # allows complete sentences with examples and "because" explanations
    "translate":  8,  # per column — kept short and clean
    "cta":       12,
}

# ---------------------------------------------------------------------------
# Hook style catalogue — MFL edition
# Each entry: (NAME, instruction, example)
# One is picked at random per generation call so hooks vary across posts.
# ---------------------------------------------------------------------------

_HOOK_STYLES: list[tuple[str, str, str]] = [
    (
        "MISTAKE",
        "Call out the common mistake English speakers make with this topic. Make the reader feel they've been saying it wrong.",
        'Topic "saying I\'m hot in Spanish" → "English speakers say this **wrong** in Spanish every time"',
    ),
    (
        "REVEAL",
        "Tease a phrase or pattern that most learners don't know. Use a keyword from the topic. End with a gap the reader wants to close.",
        'Topic "shopping phrases in Spanish" → "There\'s a phrase every Spanish shopper uses — most learners **never** learn it"',
    ),
    (
        "CONTRAST",
        "Contrast what learners are taught in school vs. what natives actually say. Create an instant recognition moment.",
        'Topic "expressing hunger in Spanish" → "Your Spanish teacher taught you **wrong**"',
    ),
    (
        "PHRASE",
        "Lead with the target language phrase itself as the hook. Make it feel immediate and useful right now.",
        'Topic "I\'m just looking in Spanish" → "Solo estoy mirando — say **this** next time"',
    ),
    (
        "SCENARIO",
        "Drop the reader into a real situation where they'd need this phrase. Create urgency through context.",
        'Topic "ordering coffee in Spanish" → "You\'re in a Spanish café — do you know what to say?"',
    ),
]


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Carousel arc templates — MFL edition
# Three named arc types, one chosen at random per generation call.
# ---------------------------------------------------------------------------

_ARC_TYPES = ["PHRASE", "MISTAKE", "NATIVE"]


def _build_carousel_arc(num_slides: int) -> tuple[str, str]:
    """Return (arc_name, arc_text) for the chosen MFL arc pattern.

    Three arc types cover the core MFL content strategies:
      PHRASE  — teaching how to say something
      MISTAKE — correcting a common error
      NATIVE  — school Spanish vs. real native usage

    Extra content slots are inserted before the CTA for carousels > 5 slides.
    """
    arc_type = random.choice(_ARC_TYPES)

    # Base arcs for 5 slides — extended below for longer carousels
    if arc_type == "PHRASE":
        slots = [
            "Slide 1: HOOK — tease the phrase or situation; create instant relevance",
            "Slide 2: TRANSLATE — LEFT: English phrase | RIGHT: Spanish phrase (clean, no explanation)",
            "Slide 3: CONTENT — context: when/where to use this phrase naturally",
            "Slide 4: CONTENT — example: the phrase used in a real conversation or sentence",
        ]
    elif arc_type == "MISTAKE":
        slots = [
            "Slide 1: HOOK — name the mistake; make readers recognise they've said this",
            "Slide 2: CONTENT — show the mistake in context; why English speakers make it",
            "Slide 3: TRANSLATE — LEFT: the wrong/literal version | RIGHT: the correct native version",
            "Slide 4: CONTENT — brief explanation of WHY the correct form works",
        ]
    else:  # NATIVE
        slots = [
            "Slide 1: HOOK — contrast what learners are taught vs. what natives actually say",
            "Slide 2: TRANSLATE — LEFT: textbook phrase | RIGHT: native/natural phrase",
            "Slide 3: CONTENT — context: register, tone, or situation where native phrase fits",
            "Slide 4: CONTENT — example: native phrase used naturally in conversation",
        ]

    # Extend for carousels > 5 slides — insert extra content before CTA
    extra_slots = [
        "CONTENT — extra example: the phrase in a different real-world context",
        "CONTENT — contrast or tip: a related phrase or common variation",
        "CONTENT — deeper insight: cultural note or register difference",
    ]
    extra_needed = num_slides - 5  # 5 = 4 content slots + 1 CTA
    for i in range(extra_needed):
        slots.append(f"Slide {len(slots) + 1}: {extra_slots[i % len(extra_slots)]}")

    slots.append(f"Slide {num_slides}: CTA — save/follow prompt, include @tutor_mia_mfl")

    return arc_type, "\n".join(slots)


def _build_system_prompt(num_slides: int) -> str:
    """Return the MFL generation system prompt with the exact slide count baked in."""
    hook_name, hook_instruction, hook_example = random.choice(_HOOK_STYLES)
    arc_type, carousel_arc = _build_carousel_arc(num_slides)

    return f"""\
You are an API that generates Instagram carousel slides teaching everyday Spanish phrases to English speakers.

You MUST return ONLY valid JSON.
Do NOT include any text before or after the JSON.
Do NOT explain anything.
Do NOT use markdown or code blocks.

---

CONTENT STRATEGY:

You are NOT building classroom lessons.
You ARE building carousels that teach ONE clear, practical idea:
  - A daily usable phrase
  - A common mistake (and the fix)
  - How natives actually say something

Rules:
  - Natural phrasing OVER literal translation
  - Real usage OVER grammar theory
  - ONE idea per carousel — do not cram multiple topics
  - Never produce a vocabulary list
  - If showing a mistake, always show the correct version

---

SLIDE COUNT (CRITICAL):

Generate EXACTLY {num_slides} slides. No more. No less.

Slide types available:
  "hook"      — opening slide only (Slide 1)
  "content"   — explanation, mistake, context, or example (middle slides)
  "translate" — English ↔ Spanish split layout (middle slides)
  "cta"       — final slide only (Slide {num_slides})

---

HOOK STYLE — use this style for Slide 1:

Style: {hook_name}
Rule:  {hook_instruction}
e.g.   {hook_example}

REQUIREMENTS:
  - Must reference a specific phrase, situation, or mistake from the topic
  - Complete sentence — no dangling ending, no trailing em-dash
  - Max 8 words
  - Must create recognition, curiosity, or tension

BAD (generic — could apply to any language topic):
  "Most people say this wrong in Spanish"
GOOD (specific — reader knows exactly what this is about):
  "English speakers say this **wrong** in every Spanish shop"

---

CAROUSEL ARC — arc type: {arc_type}

Follow this exact arc:

{carousel_arc}

FLOW RULES:
  - Each slide must build on the previous one
  - TRANSLATE slide must appear in EVERY carousel — it is mandatory, not optional
  - Do NOT write disconnected tips — every slide must earn the next

---

TRANSLATE SLIDE RULES (CRITICAL):

The translate slide is a TWO-COLUMN layout. LEFT = English, RIGHT = Spanish.

Use a translate slide for:
  - "How to say X" → show the phrase directly
  - Mistake → correction (LEFT: what they say wrong, RIGHT: what to say)
  - Textbook vs native (LEFT: textbook phrase, RIGHT: natural phrase)

RULES:
  - LEFT text: English only — plain, no explanation
  - RIGHT text: Spanish only — the phrase itself
  - Keep both sides SHORT and PARALLEL (matched rhythm, matched length)
  - Max 8 words per side
  - Do NOT add explanations inside the translate slide
  - The RIGHT side is the star — make it memorable

VALID examples:
  LEFT: "I'm just looking"       RIGHT: "Solo estoy mirando"
  LEFT: "I am hot (wrong)"       RIGHT: "Estoy caliente ❌ / Tengo calor ✅"
  LEFT: "I have hunger"          RIGHT: "Tengo hambre"

INVALID (too much explanation):
  ✗ LEFT: "When you want to say you're just browsing"
  ✗ RIGHT: "You would say Solo estoy mirando which literally means..."

---

CONTENT SLIDE PATTERNS:

Each content slide MUST use one of these patterns.
Use at LEAST 2 DIFFERENT patterns across the carousel.

  MISTAKE    — "Don't say [X] — say [Y]" (brief, punchy)
    e.g. "Don't say 'Estoy caliente' — it means something else entirely"

  CONTEXT    — when, where, or how to use the phrase naturally
    e.g. "Use this in any shop, market, or stall — it's always polite"

  EXPLANATION — why the phrase works the way it does (1–2 lines max)
    e.g. "Tengo = I have — Spanish uses 'have hunger' instead of 'am hungry'"

  EXAMPLE    — the phrase in a real sentence or mini-dialogue
    e.g. "'¿Le puedo ayudar?' — 'Solo estoy mirando, **gracias**'"

  CONTRAST   — textbook/literal vs natural/native (with both versions explicit)
    e.g. "School Spanish: 'Estoy hambriento' — Natives say: '**Tengo hambre**'"

---

WORD LIMITS:

  - Hook: max 8 words
  - Content slides: 8–22 words
  - Translate slides: max 8 words PER SIDE (left and right independently)
  - CTA: max 12 words

---

COMPLETENESS (CRITICAL):

Every content/hook/cta slide MUST be a complete, self-contained sentence.

NEVER end a slide with:
  ✗ "Because"   ✗ "And"   ✗ "Or"   ✗ "→"   ✗ "Instead"

---

CTA RULE (MANDATORY):

The final slide MUST include "@tutor_mia_mfl" and a clear action verb.

✓ VALID:   "Save this — follow @tutor_mia_mfl for daily Spanish phrases"
           "Follow @tutor_mia_mfl for more phrases like this"
           "**Save** this post — @tutor_mia_mfl posts daily Spanish tips"

✗ INVALID: "Save this" / "Follow for more" (missing handle)

---

EMPHASIS (bold using **word**):

  - 1–2 bold words per content/hook/cta slide only
  - Bold the KEY Spanish phrase, the correction, or the contrast word
  - NEVER bold filler words
  - Do NOT bold text inside translate slides

---

SELF-CORRECTION:

If you receive an error with the topic, fix the specific issue:
  - "Incorrect number of slides"        → regenerate EXACTLY {num_slides} slides
  - "No translate slide found"          → add a translate slide to the middle of the carousel
  - "Slides lack depth"                 → add a context or explanation slide
  - "Incomplete slide text"             → rewrite named slide(s) as complete sentences
  - "CTA missing @tutor_mia_mfl"        → add "@tutor_mia_mfl" to the final slide
  - "Invalid JSON"                      → fix JSON formatting
Do NOT repeat the same mistake.

---

OUTPUT FORMAT (STRICT JSON):

Content/hook/cta slide:
  {{"type": "hook",    "text": "English speakers say this **wrong** in every Spanish shop"}}
  {{"type": "content", "text": "Don't say 'Estoy caliente' — it means something very different"}}
  {{"type": "cta",     "text": "Save this — follow @tutor_mia_mfl for daily Spanish phrases"}}

Translate slide:
  {{"type": "translate", "left_text": "I'm just looking", "right_text": "Solo estoy mirando"}}

Full example output ({num_slides} slides):
{{
  "slides": [
    {{"type": "hook",      "text": "English speakers say this **wrong** in every Spanish shop"}},
    {{"type": "content",   "text": "Most people say 'Estoy caliente' — but this means something **very** different"}},
    {{"type": "translate", "left_text": "I'm just looking", "right_text": "Solo estoy mirando"}},
    {{"type": "content",   "text": "Use this in any shop — it's polite and natural, never rude"}},
    {{"type": "cta",       "text": "Save this — follow @tutor_mia_mfl for daily Spanish phrases"}}
  ]
}}

The "slides" array MUST contain EXACTLY {num_slides} objects.
Every carousel MUST include at least one "translate" slide.
If your output does not meet ALL rules, regenerate internally until it does.\
"""


# ---------------------------------------------------------------------------
# Incomplete-ending detection — shared by enforce_word_limit and validators
# ---------------------------------------------------------------------------

# Words and tokens that, when they appear at the end of a slide, indicate
# an incomplete sentence.  Used both when choosing truncation cutpoints and
# when validating the finished output.
_INCOMPLETE_TERMINALS: frozenset[str] = frozenset({
    "try", "try:", "instead", "instead:", "because", "because:",
    "then", "then:", "next", "next:", "now", "now:",
    "first", "first:", "and", "or", "but", "→", "->",
    "better:", "bad:", "with", "for", "of", "in", "at", "to",
    "the", "a", "an",
})


# ---------------------------------------------------------------------------
# Word-limit enforcement (applied in code — never rely on LLM to obey)
# ---------------------------------------------------------------------------

def enforce_word_limit(text: str, max_words: int) -> str:
    """Truncate *text* to at most *max_words* words, ending at a natural boundary.

    After a hard word-count cut the function walks backwards to find the last
    sentence-final punctuation (.!?"), and if not found, the last clause
    boundary (em-dash, colon, comma) that is at least 60% into the text.
    This prevents mid-clause truncation that makes slides feel cut off.

    Also strips any unclosed **marker so the HTML renderer never sees a
    dangling opening bold tag.
    """
    words = text.split()
    if len(words) <= max_words:
        return text

    truncated = " ".join(words[:max_words])

    # Fix unclosed **marker (odd count = dangling open tag)
    if truncated.count("**") % 2 != 0:
        truncated = truncated.rsplit("**", 1)[0].rstrip()

    # If already ends with sentence-final punctuation, we're done
    stripped = truncated.rstrip()
    if stripped and stripped[-1] in '.!?"':
        return stripped

    def _ends_with_incomplete(text: str) -> bool:
        """True if the last meaningful word is a dangling terminal."""
        last = text.rstrip().split()[-1].lower().rstrip('.,!?:"\'') if text.strip() else ""
        return last in _INCOMPLETE_TERMINALS

    # Try to end at the last clause boundary in the second half.
    # Skip any cutpoint that would leave a dangling terminal (e.g. "Try")
    # because that produces exactly the broken "→ Try" fragments we want to
    # prevent.
    min_pos = int(len(stripped) * 0.55)  # must keep at least 55% of the text
    for punct in ('—', ':', ','):
        last_pos = stripped.rfind(punct)
        if last_pos >= min_pos:
            candidate = stripped[:last_pos].rstrip()
            if not _ends_with_incomplete(candidate):
                return candidate

    # If no clean boundary found, return the hard-truncated form as-is — the
    # slide completeness validator will catch it and trigger a retry.
    return stripped


def _enforce_slide_limits(slides: list[dict]) -> list[dict]:
    """Ensure every slide's text respects the word limit for its type.

    Translate slides have two columns (left_text / right_text) — the limit
    is applied independently to each side.  All other slide types use heading.
    """
    result = []
    for slide in slides:
        slide_type = slide["type"]
        max_words  = WORD_LIMITS.get(slide_type, 15)

        if slide_type == "translate":
            left  = slide.get("left_text",  "")
            right = slide.get("right_text", "")
            new_left  = enforce_word_limit(left,  max_words)
            new_right = enforce_word_limit(right, max_words)
            if new_left != left or new_right != right:
                logger.info("Truncated translate slide columns: %r / %r", left, right)
            result.append({**slide, "left_text": new_left, "right_text": new_right})
        else:
            heading  = slide["heading"]
            enforced = enforce_word_limit(heading, max_words)
            if enforced != heading:
                logger.info(
                    "Truncated %s slide from %d words to %d: %r → %r",
                    slide_type, len(heading.split()), max_words, heading, enforced,
                )
            result.append({**slide, "heading": enforced})
    return result


# ---------------------------------------------------------------------------
# Bold phrase cap (max 3 per slide)
# ---------------------------------------------------------------------------

def _cap_bold_phrases(text: str, max_bold: int = 2) -> str:
    """Strip **..** markers beyond the first *max_bold* occurrences."""
    count = 0
    def _replacer(m: re.Match) -> str:
        nonlocal count
        count += 1
        return f"**{m.group(1)}**" if count <= max_bold else m.group(1)
    return re.sub(r'\*\*(.*?)\*\*', _replacer, text)


def _enforce_bold_caps(slides: list[dict]) -> list[dict]:
    result = []
    for slide in slides:
        if slide["type"] == "translate":
            result.append(slide)  # translate columns use plain text — no bold markers
            continue
        capped = _cap_bold_phrases(slide["heading"])
        if capped != slide["heading"]:
            logger.info("Capped bold phrases on %s slide: %r", slide["type"], slide["heading"])
        result.append({**slide, "heading": capped})
    return result


# ---------------------------------------------------------------------------
# Hook completeness validation
# ---------------------------------------------------------------------------

# Words that signal a dangling / unfinished thought when they land last
_DANGLING_ENDINGS = {
    "if", "but", "and", "or", "so", "yet", "when", "unless", "because",
    "although", "though", "while", "as", "since", "until", "than",
    "the", "a", "an", "to", "for", "of", "in", "on", "at", "by",
    "with", "about", "into", "know", "use", "do", "get", "have", "be",
}


def _is_complete_hook(text: str) -> bool:
    """Return True if the hook text reads as a complete thought.

    Rejects hooks that:
    - End with a dangling conjunction, preposition, or verb
    - End with an em-dash (—) suggesting a continuation that was cut off
    - Contain an em-dash but fewer than 2 words after it (payoff too thin)
    """
    # Strip **markers** for plain-text analysis
    plain = re.sub(r'\*\*(.*?)\*\*', r'\1', text).strip()

    # Ends with em-dash → clearly unfinished
    if plain.endswith("—") or plain.endswith("-"):
        return False

    # Last word is a dangling word
    last_word = re.split(r'[\s—]+', plain)[-1].lower().rstrip(".,!?")
    if last_word in _DANGLING_ENDINGS:
        return False

    # Em-dash present but payoff (words after it) is < 2 words → incomplete contrast
    if "—" in plain:
        after_dash = plain.split("—")[-1].strip()
        if len(after_dash.split()) < 2:
            return False

    return True


# ---------------------------------------------------------------------------
# MFL-specific content validators
# ---------------------------------------------------------------------------

def _has_translate_slide(slides: list[dict]) -> bool:
    """Return True if at least one slide is of type 'translate'."""
    return any(s["type"] == "translate" for s in slides)


# ---------------------------------------------------------------------------
# Slide completeness validation
# ---------------------------------------------------------------------------

def _is_complete_slide(text: str) -> bool:
    """Return True if *text* reads as a finished thought.

    Catches two failure modes:
    1. The last meaningful word is a known incomplete terminal (e.g. "Try",
       "Because", "→") — meaning the sentence was cut before its payload.
    2. A "→ Try" or "→ Try:" pattern appears at the very end with nothing
       after it — the contrast was started but never completed.
    """
    # Strip bold markers for plain-text analysis
    plain = re.sub(r'\*\*(.*?)\*\*', r'\1', text).strip()
    if not plain:
        return False

    # Pattern 1: last meaningful token is a known incomplete terminal
    last_word = plain.split()[-1].lower().rstrip('.,!?:"\'')
    if last_word in _INCOMPLETE_TERMINALS:
        return False

    # Pattern 2: "→ Try" or "→ Try:" at the end with no content after it
    if re.search(r'[→\->\s][Tt]ry\s*:?\s*$', plain):
        return False

    return True


def _validate_completeness(slides: list[dict]) -> None:
    """Raise ValueError listing every slide whose text is incomplete.

    Translate slides are skipped — they use left_text/right_text columns,
    not heading, and are validated separately for non-empty content.
    """
    broken = [
        f"[{s['type']}] {s['heading']!r}"
        for s in slides
        if s["type"] != "translate" and not _is_complete_slide(s["heading"])
    ]
    if broken:
        raise ValueError(
            "Incomplete slide text detected — the following slides end abruptly:\n"
            + "\n".join(broken)
            + "\nRewrite each slide as a complete sentence."
        )


# ---------------------------------------------------------------------------
# CTA handle validation
# ---------------------------------------------------------------------------

def _has_cta_handle(slides: list[dict]) -> bool:
    """Return True if the CTA slide contains @tutor_mia_mfl."""
    cta_slides = [s for s in slides if s["type"] == "cta"]
    if not cta_slides:
        return False
    return "@tutor_mia_mfl" in cta_slides[-1]["heading"]


# ---------------------------------------------------------------------------
# Depth validation — at least one phrase example and one context/explanation
# ---------------------------------------------------------------------------

# Markers indicating a real language example or phrase usage
_MFL_EXAMPLE_MARKERS = (
    "'", "\u2018", "\u2019", "\u201c", "\u201d",  # any quoted phrase
    "say ", "says ", "said ", "use ", "instead", "don't say", "not ",
    "e.g.", "for example", "→", "->",
)

# Markers indicating context, explanation, or insight
_MFL_INSIGHT_MARKERS = (
    "because", "means ", "—", " — ", "when ", "where ", "use this",
    "in spain", "in spanish", "native", "natural", "sounds",
)


def _has_depth(slides: list[dict]) -> bool:
    """Return True if the carousel has ≥1 phrase/example content slide AND
    ≥1 context or explanation content slide."""
    has_example = False
    has_insight = False
    for slide in slides:
        if slide["type"] not in ("content", "translate"):
            continue
        # For translate slides, the left/right columns count as an example
        if slide["type"] == "translate":
            has_example = True
            continue
        text_lower = slide["heading"].lower()
        if any(m in text_lower for m in _MFL_EXAMPLE_MARKERS):
            has_example = True
        if any(m in text_lower for m in _MFL_INSIGHT_MARKERS):
            has_insight = True
    return has_example and has_insight


# ---------------------------------------------------------------------------
# Backend: Anthropic
# ---------------------------------------------------------------------------

def _generate_anthropic(topic: str, num_slides: int, error_context: str = "") -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError(
            "anthropic package not installed. Run: pip install anthropic"
        ) from exc

    api_key = os.environ.get("ANTHROPIC_API_KEY")

    print("=== ANTHROPIC DEBUG ===")
    print("KEY EXISTS:", api_key is not None)
    print("KEY LENGTH:", len(api_key) if api_key else None)
    print("KEY PREFIX:", api_key[:10] if api_key else None)
    print("=======================")

    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")

    client = anthropic.Anthropic(api_key=api_key)
    logger.info("Calling Anthropic API for topic: %r (num_slides=%d)", topic, num_slides)

    user_content = f"Topic: {topic}"
    if error_context:
        user_content += f"\n\nPREVIOUS ATTEMPT FAILED — fix this error:\n{error_context}"

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=_build_system_prompt(num_slides),
        messages=[{"role": "user", "content": user_content}],
    )
    return message.content[0].text


# ---------------------------------------------------------------------------
# Backend: OpenAI
# ---------------------------------------------------------------------------

def _generate_openai(topic: str, num_slides: int, error_context: str = "") -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "openai package not installed. Run: pip install openai"
        ) from exc

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment")

    client = OpenAI(api_key=api_key)
    logger.info("Calling OpenAI API for topic: %r (num_slides=%d)", topic, num_slides)

    user_content = f"Topic: {topic}"
    if error_context:
        user_content += f"\n\nPREVIOUS ATTEMPT FAILED — fix this error:\n{error_context}"

    response = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        messages=[
            {"role": "system", "content": _build_system_prompt(num_slides)},
            {"role": "user", "content": user_content},
        ],
        max_tokens=1024,
        temperature=0.7,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def _parse_json_slides(raw: str, num_slides: int = 5) -> list[dict]:
    """Parse LLM JSON output into a validated list of slide dicts."""
    text = raw.strip()

    # Strip markdown code fences if the model wrapped output anyway
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1].strip()
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}\nRaw output:\n{raw[:500]}") from exc

    # Accept both wrapper object {"slides": [...]} and bare array [...]
    if isinstance(parsed, dict):
        if "slides" not in parsed:
            raise ValueError(f"JSON object has no 'slides' key. Keys found: {list(parsed.keys())}")
        slides = parsed["slides"]
    elif isinstance(parsed, list):
        slides = parsed
    else:
        raise ValueError(f"Expected JSON object or array, got {type(parsed).__name__}")

    if not (4 <= len(slides) <= 10):
        raise ValueError(f"Expected 4–10 slides, got {len(slides)}")
    if len(slides) != num_slides:
        raise ValueError(
            f"Requested {num_slides} slides but got {len(slides)}. Retrying for exact count."
        )

    valid_types = {"hook", "content", "translate", "cta"}
    result = []
    for i, s in enumerate(slides):
        if not isinstance(s, dict):
            raise ValueError(f"Slide {i} is not a JSON object")

        slide_type = (s.get("type") or "").strip().lower()

        if slide_type not in valid_types:
            raise ValueError(
                f"Slide {i} has invalid type {slide_type!r}. "
                f"Must be one of: {sorted(valid_types)}"
            )

        if slide_type == "translate":
            left_text  = (s.get("left_text")  or "").strip()
            right_text = (s.get("right_text") or "").strip()
            if not left_text or not right_text:
                raise ValueError(
                    f"Translate slide {i} is missing left_text or right_text"
                )
            result.append({
                "type":        "translate",
                "heading":     "",   # unused for translate
                "left_text":   left_text,
                "right_text":  right_text,
                "description": "",
            })
        else:
            text_val = (s.get("text") or "").strip()
            if not text_val:
                raise ValueError(f"Slide {i} ({slide_type}) has empty 'text'")
            result.append({
                "type":        slide_type,
                "heading":     text_val,
                "description": "",
            })

    # Validate structure: first=hook, last=cta
    if result[0]["type"] != "hook":
        raise ValueError(f"First slide must be 'hook', got {result[0]['type']!r}")
    if result[-1]["type"] != "cta":
        raise ValueError(f"Last slide must be 'cta', got {result[-1]['type']!r}")

    return result


# ---------------------------------------------------------------------------
# Review & improve pass
# ---------------------------------------------------------------------------

REVIEW_PROMPT = """\
You are an expert MFL Instagram content editor. You will receive a set of Spanish
learning carousel slides and return an IMPROVED version that is sharper, clearer,
and more useful for English learners of Spanish.

APPLY THESE FIXES:

1. HOOK — must be specific to the phrase or mistake being taught
   BAD:  "Most people say this wrong"   ← too generic
   GOOD: "English speakers say this **wrong** in every Spanish shop"

2. TRANSLATE SLIDES — must be clean, parallel, and punchy
   BAD:  LEFT: "When you want to say you are just looking around in a shop"
   GOOD: LEFT: "I'm just looking"  |  RIGHT: "Solo estoy mirando"
   Keep both sides short and matched in rhythm.

3. CONTENT SLIDES — every slide must do ONE of these:
   A) Show a real phrase or example in context
   B) Explain WHY — one short sentence using "because" or "—"
   C) Show a mistake → correction (explicit both sides)
   NEVER write abstract claims like "this sounds natural" without showing HOW.

4. STRUCTURE: Hook → Translate → Context/Explanation → Example → CTA

5. WORD LIMITS (hard):
   hook:      max 8 words
   content:   max 22 words
   translate: max 8 words PER SIDE
   cta:       max 12 words

6. EMPHASIS — use **word** markdown bold for 1–2 words per non-translate slide:
   ✓ Bold: the Spanish phrase, the correction word, the key contrast
   ✗ Never bold: filler words, generic nouns
   ✗ Never bold text inside translate slides

7. CTA must include @tutor_mia_mfl

Return ONLY a JSON array in the same format as the input — no extra text.
Translate slides use left_text/right_text. All other slides use text.

Example:
[
  { "type": "hook",      "text": "..." },
  { "type": "translate", "left_text": "...", "right_text": "..." },
  { "type": "content",   "text": "..." },
  { "type": "cta",       "text": "..." }
]\
"""


def _slides_to_review_input(slides: list[dict]) -> str:
    """Format slides into a numbered list for the review LLM."""
    lines = ["Current carousel slides:"]
    for i, s in enumerate(slides):
        lines.append(f"  {i + 1}. [{s['type'].upper()}] {s['heading']}")
    return "\n".join(lines)


def _review_anthropic(slides: list[dict]) -> str:
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=REVIEW_PROMPT,
        messages=[{"role": "user", "content": _slides_to_review_input(slides)}],
    )
    return msg.content[0].text.strip()


def _review_openai(slides: list[dict]) -> str:
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        messages=[
            {"role": "system", "content": REVIEW_PROMPT},
            {"role": "user",   "content": _slides_to_review_input(slides)},
        ],
        max_tokens=1024,
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


def review_and_improve(slides: list[dict]) -> list[dict]:
    """Run a second LLM pass to improve slide quality.

    Returns the improved slides parsed back into internal dict format.
    On any failure returns the original slides unchanged so the pipeline
    always has output to render.

    Controlled by the REVIEW_ENABLED env var (default: true).
    Set REVIEW_ENABLED=false to skip this step and save an LLM call.
    """
    if os.environ.get("REVIEW_ENABLED", "true").lower() == "false":
        logger.info("Review pass disabled (REVIEW_ENABLED=false)")
        return slides

    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    review_fn = _review_anthropic if provider == "anthropic" else _review_openai

    try:
        logger.info("Running review pass on %d slides", len(slides))
        raw      = review_fn(slides)
        # Pass the original count so the validator enforces the same slide count
        # as the primary generation pass — without this the default of 5 silently
        # replaces a correctly-generated 7-slide carousel with a 5-slide one.
        improved = _parse_json_slides(raw, num_slides=len(slides))
        improved = _enforce_slide_limits(improved)
        improved = _enforce_bold_caps(improved)
        logger.info("Review pass complete — %d slides returned", len(improved))
        return improved
    except Exception as exc:
        logger.warning("Review pass failed (%s) — using original slides", exc)
        return slides


# ---------------------------------------------------------------------------
# Caption generation
# ---------------------------------------------------------------------------

CAPTION_PROMPT = """\
You write high-performing Instagram captions for MFL carousel posts teaching Spanish phrases.

Given the carousel slides below, write a caption that matches this EXACT format:

---
[Hook line — rephrase or reinforce the opening slide; make it feel immediately useful]

[Key phrase or mistake line — reference the Spanish phrase taught]
[Brief context line — when or why to use it]

[Encouragement or relatable line — the reader has probably made this mistake]
[Value or takeaway line]

Save this post — follow @tutor_mia_mfl for a new phrase every day

#LearnSpanish #SpanishPhrases #SpanishTips
---

SPACING RULES (critical):
  - Separate each thematic block with ONE blank line (\\n\\n)
  - The CTA line ("Save this...") must be on its OWN line
  - Hashtags must be on their OWN line, separated from CTA by a blank line (\\n\\n)
  - NEVER place hashtags on the same line as the CTA
  - NEVER run hashtags directly after CTA without a blank line

STYLE:
  - One sentence per line
  - Separate EVERY line with a blank line (\\n\\n) — never single line breaks
  - Conversational, encouraging, relatable tone
  - No fluff or filler words
  - 5–8 lines of body text (excluding hashtag line)

HASHTAGS:
  - 3–5 relevant hashtags
  - Use: #LearnSpanish #SpanishPhrases #SpanishTips #MFL #LanguageLearning or similar

OUTPUT:
  Return ONLY the caption text — no JSON, no quotes, no extra commentary.\
"""


def _build_caption_user_message(slides: list[dict]) -> str:
    """Format slides into a compact message for the caption LLM call."""
    lines = ["Carousel slides:"]
    for i, s in enumerate(slides):
        if s["type"] == "translate":
            lines.append(
                f"  {i + 1}. [TRANSLATE] "
                f"EN: {s.get('left_text', '')} | ES: {s.get('right_text', '')}"
            )
        else:
            plain = re.sub(r'\*\*(.*?)\*\*', r'\1', s["heading"])
            lines.append(f"  {i + 1}. [{s['type'].upper()}] {plain}")
    return "\n".join(lines)


def _generate_caption_anthropic(slides: list[dict]) -> str:
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=CAPTION_PROMPT,
        messages=[{"role": "user", "content": _build_caption_user_message(slides)}],
    )
    return message.content[0].text.strip()


def _generate_caption_openai(slides: list[dict]) -> str:
    from openai import OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        messages=[
            {"role": "system", "content": CAPTION_PROMPT},
            {"role": "user",   "content": _build_caption_user_message(slides)},
        ],
        max_tokens=512,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def _format_caption(caption: str) -> str:
    """Enforce correct caption spacing regardless of LLM output.

    Rules applied deterministically:
    - Hashtag tokens (#word) are collected and moved to their own block
    - CTA line (contains @tutor_mia_mfl) is ensured to be on its own line
    - Body and hashtag block are separated by exactly two newlines
    - Trailing/leading whitespace is stripped
    """
    lines = [l.rstrip() for l in caption.splitlines()]

    # Separate hashtag lines from body lines
    hashtag_tokens: list[str] = []
    body_lines:     list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # A line is treated as a hashtag line if ALL non-empty tokens start with #
        tokens = stripped.split()
        if tokens and all(t.startswith('#') for t in tokens):
            hashtag_tokens.extend(tokens)
        else:
            # Inline hashtags mixed with text: split them out
            text_parts = [t for t in tokens if not t.startswith('#')]
            hash_parts = [t for t in tokens if t.startswith('#')]
            if text_parts:
                body_lines.append(" ".join(text_parts))
            hashtag_tokens.extend(hash_parts)

    # Deduplicate hashtags while preserving order
    seen: set[str] = set()
    unique_hashtags: list[str] = []
    for h in hashtag_tokens:
        if h.lower() not in seen:
            seen.add(h.lower())
            unique_hashtags.append(h)

    # Build final caption — double newline between every line for Instagram spacing
    body     = "\n\n".join(body_lines).strip()
    hashtags = " ".join(unique_hashtags)

    if hashtags:
        return f"{body}\n\n{hashtags}"
    return body


def _validate_caption(caption: str) -> None:
    """Raise ValueError if the caption is missing required elements."""
    lower = caption.lower()
    if "@tutor_mia_mfl" not in lower:
        raise ValueError("Caption missing @tutor_mia_mfl CTA — retrying.")
    lines = [l for l in caption.splitlines() if l.strip()]
    if len(lines) < 4:
        raise ValueError(f"Caption too short ({len(lines)} lines) — retrying.")


def generate_caption(slides: list[dict], max_retries: int = 2) -> str:
    """Generate an Instagram caption aligned with the given slides."""
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    gen_fn   = _generate_caption_anthropic if provider == "anthropic" else _generate_caption_openai
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            caption = gen_fn(slides)
            caption = _format_caption(caption)
            _validate_caption(caption)
            logger.info("Caption generated (%d lines)", len([l for l in caption.splitlines() if l.strip()]))
            return caption
        except Exception as exc:
            logger.warning("Caption attempt %d/%d failed: %s", attempt, max_retries, exc)
            last_err = exc
    # Non-fatal: return a safe fallback rather than crashing the whole pipeline
    logger.error("Caption generation failed after %d attempts — using fallback", max_retries)
    return "Save this — follow @tutor_mia_mfl for a new Spanish phrase every day\n\n#LearnSpanish #SpanishPhrases #MFL"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_slides(
    topic: str,
    num_slides: int = 5,
    max_retries: int = 3,
) -> tuple[list[dict], str]:
    """
    Generate carousel slides for *topic* using the configured LLM.

    Parameters
    ----------
    topic : str      The subject of the carousel (user input).
    num_slides : int Exact number of slides to generate (4–7). Default 5.

    Returns
    -------
    slides : list[dict]
        Each dict has "type", "heading", and "description" keys.
        Word limits are enforced in code regardless of LLM output.
    caption : str
        Ready-to-post Instagram caption aligned with the slides.
        Falls back to a minimal CTA string if caption generation fails.
    """
    if not (4 <= num_slides <= 10):
        raise ValueError(f"num_slides must be between 4 and 10, got {num_slides}")

    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    backends = {
        "anthropic": _generate_anthropic,
        "openai":    _generate_openai,
    }

    if provider not in backends:
        raise ValueError(
            f"Unknown LLM_PROVIDER {provider!r}. Choose 'anthropic' or 'openai'."
        )

    backend      = backends[provider]
    last_error: Optional[Exception] = None
    error_context: str              = ""

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Slide generation attempt %d/%d (num_slides=%d)", attempt, max_retries, num_slides)
            raw    = backend(topic, num_slides, error_context)
            logger.debug("Raw LLM output: %s", raw[:500])
            slides = _parse_json_slides(raw, num_slides)
            slides = _enforce_slide_limits(slides)
            slides = _enforce_bold_caps(slides)
            hook_text = slides[0]["heading"]
            if not _is_complete_hook(hook_text):
                raise ValueError(
                    f"Hook is not a complete thought: {hook_text!r}. "
                    "Retrying for a hook with a full payoff."
                )
            if not _has_translate_slide(slides):
                raise ValueError(
                    "No translate slide found. Every carousel MUST include at least one "
                    "translate slide (type: 'translate') with left_text and right_text. "
                    "Add a translate slide showing the English phrase on the left and "
                    "the Spanish phrase on the right."
                )
            if not _has_depth(slides):
                raise ValueError(
                    "Slides lack depth: need at least one phrase/example slide "
                    "AND one context or explanation slide. "
                    "Add a content slide that explains when/why to use the phrase."
                )
            _validate_completeness(slides)   # raises if any slide ends abruptly
            if not _has_cta_handle(slides):
                raise ValueError(
                    "CTA slide is missing @tutor_mia_mfl. "
                    "The final slide MUST include '@tutor_mia_mfl'."
                )
            logger.info("Generated %d slides (validated: translate slide, depth, completeness, CTA handle)", len(slides))
            slides  = review_and_improve(slides)
            caption = generate_caption(slides)
            return slides, caption
        except Exception as exc:
            logger.warning("Attempt %d/%d failed: %s", attempt, max_retries, exc)
            last_error    = exc
            error_context = str(exc)   # fed back into the next LLM call
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.info("Waiting %ds before retry…", wait)
                time.sleep(wait)

    raise RuntimeError(
        f"Slide generation failed after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
