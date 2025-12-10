# ==========================================================
# TENDER INTELLIGENCE SYSTEM — FLASK API
# Cloud-ready with Render deployment
# ==========================================================

from flask import Flask, jsonify, render_template_string
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
# HTML TEMPLATES
# ----------------------------------------------------------
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Tender Intelligence Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #fff; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { font-size: 2.5rem; margin-bottom: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { color: #888; margin-bottom: 30px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 40px; }
        .stat-card { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 16px; padding: 25px; border: 1px solid #333; }
        .stat-value { font-size: 2.5rem; font-weight: 700; margin-bottom: 5px; }
        .stat-label { color: #888; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }
        .high { color: #ff6b6b; }
        .medium { color: #feca57; }
        .low { color: #48dbfb; }
        .tenders { background: #111; border-radius: 16px; padding: 25px; border: 1px solid #333; }
        .tender-item { padding: 15px; border-bottom: 1px solid #222; display: flex; justify-content: space-between; align-items: center; }
        .tender-item:last-child { border-bottom: none; }
        .tender-title { flex: 1; }
        .tender-ref { color: #667eea; font-weight: 600; }
        .tender-name { color: #ccc; font-size: 0.9rem; margin-top: 5px; }
        .priority-badge { padding: 5px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
        .priority-HIGH { background: rgba(255, 107, 107, 0.2); color: #ff6b6b; }
        .priority-MEDIUM { background: rgba(254, 202, 87, 0.2); color: #feca57; }
        .priority-LOW { background: rgba(72, 219, 251, 0.2); color: #48dbfb; }
        .score { font-size: 1.5rem; font-weight: 700; margin-left: 20px; }
        .actions { margin-top: 30px; display: flex; gap: 15px; }
        .btn { padding: 12px 25px; border-radius: 8px; font-weight: 600; cursor: pointer; border: none; text-decoration: none; }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .btn-secondary { background: #222; color: #fff; border: 1px solid #444; }
        .last-run { color: #666; font-size: 0.85rem; margin-top: 20px; }
        .status { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
        .status-online { background: #00ff88; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Tender Intelligence</h1>
        <p class="subtitle"><span class="status status-online"></span>TES & Phakathi Automation Engine</p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{{ total_tenders }}</div>
                <div class="stat-label">Total Tenders</div>
            </div>
            <div class="stat-card">
                <div class="stat-value high">{{ high_priority }}</div>
                <div class="stat-label">🔥 High Priority</div>
            </div>
            <div class="stat-card">
                <div class="stat-value medium">{{ medium_priority }}</div>
                <div class="stat-label">✅ Medium Priority</div>
            </div>
            <div class="stat-card">
                <div class="stat-value low">{{ low_priority }}</div>
                <div class="stat-label">📝 Low Priority</div>
            </div>
        </div>
        
        <div class="tenders">
            <h2 style="margin-bottom: 20px;">Recent Tenders</h2>
            {% for tender in tenders %}
            <div class="tender-item">
                <div class="tender-title">
                    <div class="tender-ref">{{ tender.ref }}</div>
                    <div class="tender-name">{{ tender.title[:80] }}...</div>
                </div>
                <span class="priority-badge priority-{{ tender.priority }}">{{ tender.priority }}</span>
                <div class="score">{{ tender.score }}</div>
            </div>
            {% endfor %}
            {% if not tenders %}
            <p style="color: #666; text-align: center; padding: 40px;">No tenders found. Run a scan to populate.</p>
            {% endif %}
        </div>
        
        <div class="actions">
            <a href="/api/run/daily" class="btn btn-primary">🚀 Run Daily Scan</a>
            <a href="/api/run/weekly" class="btn btn-secondary">�� Generate Report</a>
            <a href="/health" class="btn btn-secondary">💚 Health Check</a>
        </div>
        
        <p class="last-run">Last updated: {{ last_run }}</p>
    </div>
</body>
</html>
"""

# ----------------------------------------------------------
# ROUTES
# ----------------------------------------------------------
@app.route("/")
def index():
    return dashboard()

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "service": "tender-intelligence",
        "version": "2.0",
        "timestamp": datetime.now().isoformat(),
        "selenium_enabled": ENABLE_SELENIUM
    })

@app.route("/dashboard")
def dashboard():
    # Load recent tenders from output
    tenders = []
    total = high = medium = low = 0
    last_run = "No runs yet"
    
    try:
        json_path = os.path.join(OUTPUT_DIR, "new_tenders.json")
        if os.path.exists(json_path):
            mtime = datetime.fromtimestamp(os.path.getmtime(json_path))
            last_run = mtime.strftime("%Y-%m-%d %H:%M:%S")
            with open(json_path, "r") as f:
                raw_tenders = json.load(f)
                for t in raw_tenders:
                    scores = t.get("scores", {})
                    tenders.append({
                        "ref": t.get("ref", "N/A"),
                        "title": t.get("title", "Unknown"),
                        "priority": scores.get("priority", "LOW"),
                        "score": scores.get("composite", 0)
                    })
                
                total = len(tenders)
                high = sum(1 for t in tenders if t["priority"] == "HIGH")
                medium = sum(1 for t in tenders if t["priority"] == "MEDIUM")
                low = sum(1 for t in tenders if t["priority"] == "LOW")
    except Exception as e:
        print(f"Error loading tenders: {e}")
    
    return render_template_string(
        DASHBOARD_HTML,
        total_tenders=total,
        high_priority=high,
        medium_priority=medium,
        low_priority=low,
        tenders=tenders[:10],  # Show top 10
        last_run=last_run
    )

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
