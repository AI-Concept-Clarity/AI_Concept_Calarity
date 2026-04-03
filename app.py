"""
app.py — ConceptClarity v2.1
Production-ready Flask backend with proper error handling, CSRF awareness,
and clean PRG pattern.
"""

import os
import uuid
from datetime import date, timedelta

from flask import (
    Flask, render_template, request,
    session, redirect, url_for, jsonify,
)
from ai_explainer import (
    generate_explanation,
    generate_related_terms,
    generate_followup_answer,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "conceptclarity-secret-key-2024")

# ── Trending concepts shown in the sidebar ────────────────────────────────
TRENDING_CONCEPTS = [
    "CRISPR", "Quantum Entanglement", "Neuroplasticity",
    "Dark Matter", "Epigenetics", "Blockchain", "Mitochondria",
    "String Theory", "Osmosis", "Entropy",
]


# ── Helpers ───────────────────────────────────────────────────────────────

def group_history(history: list) -> dict:
    today     = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    grouped   = {"Today": [], "Yesterday": [], "Earlier": []}
    for item in history:
        d = item.get("date", today)
        if d == today:
            grouped["Today"].append(item)
        elif d == yesterday:
            grouped["Yesterday"].append(item)
        else:
            grouped["Earlier"].append(item)
    return grouped


def _ensure_session():
    """Initialise session keys safely."""
    if "history" not in session or not isinstance(session["history"], list):
        session["history"] = []
    # Back-fill missing date/id fields from old sessions
    for item in session["history"]:
        if "date" not in item:
            item["date"] = date.today().isoformat()
        if "id" not in item:
            item["id"] = str(uuid.uuid4())


# ── Routes ────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def home():
    _ensure_session()

    if request.method == "POST":
        term       = request.form.get("term", "").strip()
        difficulty = request.form.get("difficulty", "intermediate")
        language   = request.form.get("language", "English")

        if not term:
            session["last_error"]   = "Please enter a scientific term."
            session["last_success"] = ""
        else:
            try:
                result = generate_explanation(term, difficulty, language)
                # Deduplicate & push to front
                session["history"] = [
                    h for h in session["history"]
                    if h["term"].lower() != term.lower()
                ]
                session["history"].insert(0, {
                    "id":         str(uuid.uuid4()),
                    "term":       term,
                    "date":       date.today().isoformat(),
                    "difficulty": difficulty,
                    "language":   language,
                })
                # Keep history bounded
                session["history"] = session["history"][:50]
                session["last_success"] = result["explanation"]
                session["last_error"]   = ""
            except Exception as e:
                session["last_error"]   = str(e)
                session["last_success"] = ""

        session.modified = True
        return redirect(url_for("home"))   # PRG pattern

    return render_template(
        "index.html",
        success_message=session.pop("last_success", ""),
        error_message=session.pop("last_error", ""),
        history=group_history(session["history"]),
        trending=TRENDING_CONCEPTS,
    )


@app.route("/delete/<item_id>", methods=["DELETE"])
def delete_history(item_id):
    _ensure_session()
    session["history"] = [h for h in session["history"] if h["id"] != item_id]
    session.modified = True
    return ("", 204)


@app.route("/rename/<item_id>", methods=["POST"])
def rename_history(item_id):
    _ensure_session()
    new_name = request.form.get("new_name", "").strip()
    if not new_name:
        return ("", 400)
    for item in session["history"]:
        if item["id"] == item_id:
            item["term"] = new_name[:100]   # clamp length
            break
    session.modified = True
    return ("", 204)


@app.route("/api/explain", methods=["POST"])
def api_explain():
    if not request.is_json:
        return jsonify({"status": "error", "message": "JSON required"}), 400

    data       = request.get_json(silent=True) or {}
    term       = data.get("term", "").strip()
    difficulty = data.get("difficulty", "intermediate")
    language   = data.get("language", "English")

    if not term:
        return jsonify({"status": "error", "message": "Term is required"}), 400
    if difficulty not in ("beginner", "intermediate", "expert"):
        difficulty = "intermediate"
    if language not in ("English", "Hindi", "Telugu", "French", "German"):
        language = "English"

    try:
        result = generate_explanation(term, difficulty, language)

        _ensure_session()
        session["history"] = [
            h for h in session["history"]
            if h["term"].lower() != term.lower()
        ]
        session["history"].insert(0, {
            "id":         str(uuid.uuid4()),
            "term":       term,
            "date":       date.today().isoformat(),
            "difficulty": difficulty,
            "language":   language,
        })
        session["history"] = session["history"][:50]
        session.modified = True

        related_terms = generate_related_terms(term)
        grouped       = group_history(session["history"])

        return jsonify({
            "status":        "success",
            "term":          result["term"],
            "difficulty":    difficulty,
            "language":      language,
            "tag":           result["tag"],
            "explanation":   result["explanation"],
            "example":       result["example"],
            "key_insight":   result["key_insight"],
            "related_terms": related_terms,
            "history":       grouped,
        })

    except ValueError as e:
        # Validation errors → 400
        return jsonify({"status": "error", "message": str(e)}), 400
    except RuntimeError as e:
        # AI / service errors → 503
        print(f"API RUNTIME ERROR: {e}")
        return jsonify({"status": "error", "message": str(e)}), 503
    except Exception as e:
        print(f"API UNEXPECTED ERROR: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred. Please try again."}), 500


@app.route("/api/followup", methods=["POST"])
def api_followup():
    if not request.is_json:
        return jsonify({"status": "error", "message": "JSON required"}), 400

    data       = request.get_json(silent=True) or {}
    term       = data.get("term", "").strip()
    question   = data.get("question", "").strip()
    difficulty = data.get("difficulty", "intermediate")
    language   = data.get("language", "English")
    context    = data.get("context", "")

    if not term or not question:
        return jsonify({"status": "error", "message": "Term and question are required"}), 400

    try:
        answer = generate_followup_answer(term, question, difficulty, context, language)
        return jsonify({"status": "success", "answer": answer})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"status": "error", "message": str(e)}), 503
    except Exception as e:
        print(f"FOLLOWUP ERROR: {e}")
        return jsonify({"status": "error", "message": "Could not generate follow-up answer."}), 500


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    if not request.is_json:
        return jsonify({"status": "error"}), 400
    data = request.get_json(silent=True) or {}
    # In production you'd persist this; for now just log it
    print(f"FEEDBACK — term: {data.get('term')!r}, rating: {data.get('rating')!r}")
    return jsonify({"status": "success"})


# ── Error handlers ────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"status": "error", "message": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"status": "error", "message": "Internal server error"}), 500


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug)