# ==========================================================
# TENDER INTELLIGENCE SYSTEM — FLASK API
# Flask API for tender intelligence dashboard
# ==========================================================

from flask import Flask, jsonify, request
from datetime import datetime
import os
import json

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
# ----------------------------------------------------------
# MAIN
# ----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
