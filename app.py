# ==========================================================
# TENDER INTELLIGENCE SYSTEM — FLASK API
# Flask API for tender intelligence dashboard
# ==========================================================

from flask import Flask, jsonify, request
from datetime import datetime
import os
import json
import requests

app = Flask(__name__)

# ----------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------
ENABLE_SELENIUM = os.environ.get("ENABLE_SELENIUM", "false").lower() == "true"
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./output")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------------------------------------------------
# ROUTES
# ----------------------------------------------------------
@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "tender-intelligence",
        "version": "2.0",
        "timestamp": datetime.now().isoformat(),
        "selenium_enabled": ENABLE_SELENIUM
    })

@app.route("/api/run/daily")
def run_daily():
    """Trigger daily scan via API"""
    try:
        from daily_runner import run_daily
        result = run_daily()
        return jsonify({
            "status": "success",
            "message": "Daily scan completed",
            "timestamp": datetime.now().isoformat(),
            "result": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/api/run/weekly")
def run_weekly():
    """Trigger weekly report via API"""
    try:
        from weekly_report import run_weekly
        result = run_weekly()
        return jsonify({
            "status": "success",
            "message": "Weekly report generated",
            "timestamp": datetime.now().isoformat(),
            "result": result
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/cron/daily")
def cron_daily():
    """Endpoint for cron job to hit"""
    return run_daily()

@app.route("/cron/weekly")
def cron_weekly():
    """Endpoint for cron job to hit"""
    return run_weekly()

@app.route("/api/tenders")
def api_tenders():
    """JSON API for tenders"""
    try:
        json_path = os.path.join(OUTPUT_DIR, "new_tenders.json")
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                return jsonify(json.load(f))
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/summarize", methods=["POST", "OPTIONS"])
def api_summarize():
    """
    Server-side proxy for tender summarization service.
    Keep the API key on the server (do NOT call external APIs directly from the browser).

    Env vars:
      - SUMMARIZATION_API_KEY: required
      - SUMMARIZATION_MODEL: optional (default: claude-sonnet-4-20250514)
      - CORS_ORIGIN: optional (default: *)
    """
    cors_origin = os.environ.get("CORS_ORIGIN", "*")

    if request.method == "OPTIONS":
        resp = jsonify({"ok": True})
        resp.headers["Access-Control-Allow-Origin"] = cors_origin
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return resp

    api_key = (os.environ.get("SUMMARIZATION_API_KEY") or "").strip()
    if not api_key:
        resp = jsonify({"error": "SUMMARIZATION_API_KEY not configured on server"})
        resp.status_code = 501
        resp.headers["Access-Control-Allow-Origin"] = cors_origin
        return resp

    try:
        payload = request.get_json(silent=True) or {}
        tender = payload.get("tender") if isinstance(payload, dict) else None
        if not isinstance(tender, dict):
            # Backwards compatible: accept tender fields at top-level
            tender = payload if isinstance(payload, dict) else {}

        title = (tender.get("title") or "").strip()
        description = (tender.get("description") or "").strip()
        category = (tender.get("category") or "").strip()
        client = (tender.get("client") or "").strip()
        closing = (tender.get("closing_date") or "").strip()

        if not title and not description:
            resp = jsonify({"error": "Missing tender title/description"})
            resp.status_code = 400
            resp.headers["Access-Control-Allow-Origin"] = cors_origin
            return resp

        # Priority: request payload > env var > default
        model = (payload.get("model") or os.environ.get("SUMMARIZATION_MODEL") or "claude-sonnet-4-20250514").strip()

        prompt = (
            "Summarize this tender in 3 bullet points.\n"
            "Focus on: scope of work, key requirements, and deadlines.\n\n"
            f"Title: {title}\n"
            f"Description: {description}\n"
            f"Category: {category}\n"
            f"Client: {client}\n"
            f"Closing date: {closing}\n"
        )

        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "content-type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": model,
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )

        if res.status_code >= 400:
            try:
                err_json = res.json()
            except Exception:
                err_json = {"error": res.text}
            resp = jsonify({"error": "Summarization API error", "details": err_json})
            resp.status_code = 502
            resp.headers["Access-Control-Allow-Origin"] = cors_origin
            return resp

        data = res.json() or {}
        content = data.get("content") or []
        summary = ""
        if isinstance(content, list) and content:
            first = content[0] if isinstance(content[0], dict) else {}
            summary = (first.get("text") or "").strip()

        resp = jsonify({"summary": summary, "ts": datetime.utcnow().isoformat() + "Z"})
        resp.headers["Access-Control-Allow-Origin"] = cors_origin
        return resp
    except Exception as e:
        resp = jsonify({"error": str(e)})
        resp.status_code = 500
        resp.headers["Access-Control-Allow-Origin"] = cors_origin
        return resp

# ----------------------------------------------------------
# MAIN
# ----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
