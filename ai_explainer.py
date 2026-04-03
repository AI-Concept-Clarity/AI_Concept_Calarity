"""
ai_explainer.py — ConceptClarity v2.1
Fixes: "um um um" hallucination, empty responses, bad parsing, robustness.
"""

import re
import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL  = "llama-3.3-70b-versatile"   # More capable model → fewer hallucinations

DIFFICULTY_CONFIGS = {
    "beginner": {
        "audience":   "a curious 10-year-old with no prior knowledge",
        "rules": [
            "Use everyday analogies and comparisons to familiar objects",
            "Avoid ALL technical jargon — if a term is unavoidable, define it immediately",
            "Keep sentences short (under 20 words each)",
            "Use a friendly, encouraging tone",
        ],
        "max_tokens": 350,
    },
    "intermediate": {
        "audience":   "a high school or undergraduate student with basic science literacy",
        "rules": [
            "Use some technical vocabulary, but explain unfamiliar terms briefly",
            "Reference mechanisms and processes, not just outcomes",
            "Balance depth with clarity",
        ],
        "max_tokens": 420,
    },
    "expert": {
        "audience":   "a graduate-level researcher or professional in a STEM field",
        "rules": [
            "Use precise technical terminology without over-explaining basics",
            "Reference underlying mechanisms, edge cases, or current research",
            "Be concise but intellectually thorough",
        ],
        "max_tokens": 500,
    },
}

DIFFICULTY_TAGS = {
    "beginner":     {"label": "Foundational", "emoji": "🌱"},
    "intermediate": {"label": "Intermediate",  "emoji": "⚗️"},
    "expert":       {"label": "Advanced",      "emoji": "🔬"},
}

LANGUAGE_INSTRUCTIONS = {
    "English": "Respond entirely in English.",
    "Hindi":   "Respond entirely in Hindi (हिन्दी). Use Devanagari script.",
    "Telugu":  "Respond entirely in Telugu (తెలుగు). Use Telugu script.",
    "French":  "Respond entirely in French (Français).",
    "German":  "Respond entirely in German (Deutsch).",
}


# ─── helpers ────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    """Collapse whitespace and strip."""
    return re.sub(r"\s+", " ", text or "").strip()


def _sanitize_output(text: str) -> str:
    """
    Remove filler / hallucinated content:
    - Repeated 'um', 'uh', 'ah', 'er', 'hmm' etc.
    - Markdown artefacts the model sometimes leaks.
    """
    # Remove runs of filler words (case-insensitive)
    text = re.sub(r"\b(um|uh|ah|er|hmm|hm)\b[\s,]*", "", text, flags=re.IGNORECASE)
    # Collapse multiple commas / spaces left by the removal
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\s{2,}", " ", text)
    # Strip leading/trailing punctuation artefacts
    text = text.strip(" ,;.")
    return text


def _validate_term(term: str) -> str:
    term = _clean(term)
    if not term:
        raise ValueError("Please enter a scientific term.")
    # Must contain at least one alphabetic character from any script
    if not re.search(r"[A-Za-zÀ-ÿ\u0900-\u097F\u0C00-\u0C7F\u4E00-\u9FFF]", term):
        raise ValueError("Input must contain letters — please enter a real scientific term.")
    if re.fullmatch(r"[\d\s\W]+", term):
        raise ValueError("Numbers only are not valid. Please enter a scientific concept.")
    if len(term) > 200:
        raise ValueError("Term is too long. Please be more specific.")
    return term


def _parse_structured_response(text: str) -> dict:
    """Parse EXPLANATION / EXAMPLE / KEY INSIGHT blocks robustly."""
    result = {}
    patterns = {
        "explanation": r"EXPLANATION[:\s]+(.+?)(?=EXAMPLE[:\s]|KEY INSIGHT[:\s]|$)",
        "example":     r"EXAMPLE[:\s]+(.+?)(?=KEY INSIGHT[:\s]|$)",
        "key_insight": r"KEY INSIGHT[:\s]+(.+?)$",
    }
    for key, pat in patterns.items():
        match = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if match:
            result[key] = _sanitize_output(_clean(match.group(1)))
    return result


# ─── public API ─────────────────────────────────────────────────────────────

def generate_explanation(term: str, difficulty: str = "intermediate", language: str = "English") -> dict:
    term       = _validate_term(term)
    difficulty = difficulty if difficulty in DIFFICULTY_CONFIGS else "intermediate"
    language   = language   if language   in LANGUAGE_INSTRUCTIONS else "English"

    config     = DIFFICULTY_CONFIGS[difficulty]
    tag        = DIFFICULTY_TAGS[difficulty]
    lang_instr = LANGUAGE_INSTRUCTIONS[language]
    rules_block = "\n".join(f"  - {r}" for r in config["rules"])

    system_prompt = (
        "You are an expert science educator. "
        "You write clean, accurate, engaging explanations. "
        "You NEVER use filler words like 'um', 'uh', 'ah', 'er', or 'hmm'. "
        "You ALWAYS respond only in the language specified. "
        "You NEVER use markdown symbols like **, __, ## or bullet dashes inside the content sections."
    )

    user_prompt = f"""Explain the following scientific concept for {config['audience']}.

Language: {lang_instr}

Rules:
{rules_block}
  - Total response must be under 220 words
  - Do NOT use markdown headers, asterisks, or bullet dashes inside section content
  - Do NOT use any filler words (um, uh, ah, er, hmm)
  - Keep the three section labels (EXPLANATION, EXAMPLE, KEY INSIGHT) in English; write their content in the target language

Concept: {term}

Respond using EXACTLY this structure:
EXPLANATION: [2-3 sentences explaining what it is and why it matters]
EXAMPLE: [1 concrete real-world example]
KEY INSIGHT: [The single most important thing to understand about this concept]
"""

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=config["max_tokens"],
            stop=None,
        )
    except Exception as e:
        print(f"GROQ ERROR: {e}")
        raise RuntimeError("AI service temporarily unavailable. Please try again in a moment.")

    if not resp.choices:
        raise RuntimeError("No response received from the AI service.")

    raw = _clean(resp.choices[0].message.content or "")
    if not raw:
        raise RuntimeError("AI returned an empty response. Please try again.")

    # Guard against hallucinated filler-only responses
    cleaned_check = _sanitize_output(raw)
    if len(cleaned_check) < 30:
        raise RuntimeError("AI response was unusable. Please try a different term or try again.")

    parsed = _parse_structured_response(raw)

    # Fallback: if parsing completely fails, use the whole sanitized text as explanation
    explanation = parsed.get("explanation") or _sanitize_output(raw)

    return {
        "term":        term,
        "difficulty":  difficulty,
        "language":    language,
        "tag":         tag,
        "explanation": explanation,
        "example":     parsed.get("example", ""),
        "key_insight": parsed.get("key_insight", ""),
    }


def generate_related_terms(term: str) -> list:
    prompt = (
        f'List exactly 4 scientific concepts closely related to "{term}". '
        "Return ONLY a comma-separated list on a single line. "
        "No explanations, no numbering, no markdown. "
        "Example: Osmosis, Cell membrane, Diffusion, Active transport"
    )
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful science assistant. Output only the requested format."},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.2,
            max_tokens=60,
        )
        text  = _sanitize_output(resp.choices[0].message.content.strip())
        terms = [t.strip().strip(".,;\"'") for t in text.split(",") if t.strip()]
        # Filter out empty or obviously wrong entries
        terms = [t for t in terms if 2 < len(t) < 60]
        return terms[:4]
    except Exception as e:
        print(f"GROQ RELATED ERROR: {e}")
        return []


def generate_followup_answer(
    term: str,
    question: str,
    difficulty: str = "intermediate",
    context: str = "",
    language: str = "English",
) -> str:
    term       = _validate_term(term)
    question   = _clean(question)
    difficulty = difficulty if difficulty in DIFFICULTY_CONFIGS else "intermediate"
    language   = language   if language   in LANGUAGE_INSTRUCTIONS else "English"

    config     = DIFFICULTY_CONFIGS[difficulty]
    lang_instr = LANGUAGE_INSTRUCTIONS[language]
    ctx_block  = f"\nContext from earlier explanation:\n{context[:600]}" if context else ""

    system_prompt = (
        "You are a friendly science tutor continuing a tutoring session. "
        "You NEVER use filler words. You answer directly and concisely. "
        "You respond only in the specified language."
    )

    user_prompt = f"""A student just learned about "{term}" at the {difficulty} level.{ctx_block}

Language: {lang_instr}
Audience: {config['audience']}

Follow-up question: "{question}"

Answer directly in 2-3 sentences. No filler words. No markdown. Respond in the specified language only.
"""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=200,
        )
        return _sanitize_output(_clean(resp.choices[0].message.content or ""))
    except Exception as e:
        print(f"GROQ FOLLOWUP ERROR: {e}")
        raise RuntimeError("Could not generate follow-up answer. Please try again.")