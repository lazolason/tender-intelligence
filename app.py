# ==========================================================
# TENDER INTELLIGENCE SYSTEM — FLASK API
# Flask API for tender intelligence dashboard
# ==========================================================

from flask import Flask, jsonify, request
from datetime import datetime
from functools import wraps
import os
import json
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# ----------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------
ENABLE_SELENIUM = os.environ.get("ENABLE_SELENIUM", "false").lower() == "true"
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./output")
API_KEY = os.environ.get("API_KEY", "").strip()  # Set in environment or .env file

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------------------------------------------------
# API KEY AUTHENTICATION DECORATOR
# ----------------------------------------------------------
def require_api_key(f):
    """Decorator to require API key for protected endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip auth if no API_KEY is configured (optional security)
        if not API_KEY:
            return f(*args, **kwargs)

        # Check Authorization header (Bearer token)
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            if token == API_KEY:
                return f(*args, **kwargs)

        # Check X-API-Key header (alternative)
        api_key_header = request.headers.get('X-API-Key', '')
        if api_key_header == API_KEY:
            return f(*args, **kwargs)

        # Unauthorized
        return jsonify({
            "error": "Unauthorized",
            "message": "Valid API key required. Use 'Authorization: Bearer YOUR_KEY' or 'X-API-Key: YOUR_KEY' header."
        }), 401

    return decorated_function

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

@app.route("/api/summarize", methods=["POST", "OPTIONS"])
@require_api_key
def api_summarize():
    """
    Server-side proxy for OpenAI summarization.
    Requires API key authentication.
    """
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200

    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY not configured on server"}), 501

    try:
        data = request.get_json()
        tender = data.get("tender", {})
        
        title = tender.get("title", "")
        description = tender.get("description", "")
        
        prompt = f"""
        Summarize this tender in 3 bullet points.
        Focus on: scope of work, key requirements, and deadlines.
        
        Title: {title}
        Description: {description}
        """

        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {api_key}",
            },
            json={
                "model": "gpt-4o-mini",
                "temperature": 0.2,
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30
        )

        if res.status_code >= 400:
            return jsonify({"error": "OpenAI API error", "details": res.text}), 502

        data = res.json()
        summary = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        ) or "No summary generated."

        return jsonify({"summary": summary, "ts": datetime.utcnow().isoformat() + "Z"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/run/daily")
@require_api_key
def run_daily():
    """Trigger daily scan via API. Requires API key authentication."""
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
@require_api_key
def run_weekly():
    """Trigger weekly report via API. Requires API key authentication."""
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
@require_api_key
def cron_daily():
    """Endpoint for cron job to hit. Requires API key authentication."""
    return run_daily()

@app.route("/cron/weekly")
@require_api_key
def cron_weekly():
    """Endpoint for cron job to hit. Requires API key authentication."""
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
# ----------------------------------------------------------
# MAIN
# ----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
