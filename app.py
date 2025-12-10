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
        body { font-family: "SF Pro Display", "Segoe UI", "Helvetica Neue", Arial, sans-serif; background: radial-gradient(120% 120% at 10% 10%, #1c1a2e 0%, #090a12 40%, #05060d 100%); color: #f5f7fb; padding: 32px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .glass { background: linear-gradient(135deg, rgba(33, 35, 55, 0.85), rgba(18, 19, 32, 0.9)); border: 1px solid rgba(255,255,255,0.05); border-radius: 20px; box-shadow: 0 20px 50px rgba(0,0,0,0.35); }
        .hero { padding: 32px 40px; margin-bottom: 18px; }
        .hero-title { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; }
        .hero-icon { width: 42px; height: 42px; border-radius: 12px; background: radial-gradient(circle at 30% 30%, #7e6bf5, #5c4bd5); display: grid; place-items: center; font-size: 20px; }
        h1 { font-size: 2.5rem; font-weight: 800; letter-spacing: -0.5px; color: #c9c2ff; }
        .subtitle { color: #9ea3b5; margin-bottom: 14px; display: flex; align-items: center; gap: 10px; font-weight: 600; }
        .status-dot { width: 10px; height: 10px; border-radius: 50%; background: #27d17f; box-shadow: 0 0 10px rgba(39, 209, 127, 0.6); }
        .last-synced { background: rgba(88, 114, 255, 0.15); color: #d3ddff; border: 1px solid rgba(122, 143, 255, 0.45); padding: 8px 14px; border-radius: 12px; font-size: 0.9rem; display: inline-flex; align-items: center; gap: 8px; }
        .nav-pills { display: flex; gap: 10px; margin-top: 14px; }
        .pill { padding: 10px 18px; border-radius: 24px; border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.02); color: #c7d2f5; font-weight: 600; text-decoration: none; transition: all 0.2s ease; }
        .pill.active { background: linear-gradient(120deg, #7c6bf7, #5ec6ff); color: #0c0f1c; box-shadow: 0 10px 30px rgba(92, 137, 255, 0.35); }
        .pill:hover { border-color: rgba(255,255,255,0.18); transform: translateY(-1px); }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; margin-bottom: 18px; }
        .stat-card { padding: 18px 20px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.04); background: linear-gradient(145deg, rgba(20,22,36,0.9), rgba(12,14,24,0.9)); box-shadow: inset 0 1px 0 rgba(255,255,255,0.03), 0 12px 30px rgba(0,0,0,0.25); }
        .stat-label { color: #8d93a9; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        .stat-value { font-size: 2.1rem; font-weight: 800; }
        .pill-small { display: inline-flex; align-items: center; gap: 6px; padding: 5px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 700; }
        .pill-high { background: rgba(255, 92, 92, 0.12); color: #ff7b7b; border: 1px solid rgba(255, 92, 92, 0.2); }
        .pill-medium { background: rgba(255, 193, 71, 0.12); color: #f8c55c; border: 1px solid rgba(255, 193, 71, 0.2); }
        .pill-low { background: rgba(82, 196, 255, 0.12); color: #7fd2ff; border: 1px solid rgba(82, 196, 255, 0.2); }
        .pill-neutral { background: rgba(255,255,255,0.05); color: #cfd5e6; border: 1px solid rgba(255,255,255,0.08); }
        .section { padding: 22px 24px; }
        .section h2 { font-size: 1.2rem; margin-bottom: 16px; color: #e9ecf7; display: flex; align-items: center; gap: 10px; }
        .filter-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
        .filter { padding: 8px 14px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.08); color: #cdd4e9; font-weight: 700; background: rgba(255,255,255,0.03); }
        .filter.active { background: linear-gradient(120deg, #7c6bf7, #5ec6ff); color: #0c0f1c; }
        .tenders { margin-top: 4px; display: grid; gap: 12px; }
        .tender-card { border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); background: linear-gradient(140deg, rgba(20,22,36,0.95), rgba(9,11,20,0.9)); padding: 16px 18px; display: flex; align-items: center; justify-content: space-between; gap: 12px; box-shadow: 0 12px 30px rgba(0,0,0,0.2); }
        .tender-main { flex: 1; }
        .tender-ref { color: #8fa5ff; font-weight: 800; letter-spacing: 0.2px; margin-bottom: 6px; display: inline-flex; align-items: center; gap: 6px; }
        .tender-title { color: #eef2ff; font-weight: 700; margin-bottom: 8px; }
        .tender-meta { display: flex; flex-wrap: wrap; gap: 8px; color: #9aa3ba; font-size: 0.9rem; }
        .meta-chip { padding: 6px 10px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.04); display: inline-flex; align-items: center; gap: 6px; }
        .priority-badge { padding: 8px 14px; border-radius: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.3px; }
        .priority-HIGH { background: rgba(255, 92, 92, 0.18); color: #ff7b7b; border: 1px solid rgba(255, 92, 92, 0.35); }
        .priority-MEDIUM { background: rgba(255, 193, 71, 0.18); color: #f8c55c; border: 1px solid rgba(255, 193, 71, 0.35); }
        .priority-LOW { background: rgba(82, 196, 255, 0.18); color: #7fd2ff; border: 1px solid rgba(82, 196, 255, 0.35); }
        .score { display: flex; align-items: center; gap: 8px; font-weight: 800; color: #e5ecff; }
        .chip { padding: 8px 12px; border-radius: 12px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); color: #cfd5e6; font-weight: 700; }
        .action-bar { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }
        .action-btn { padding: 10px 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); background: linear-gradient(135deg, #7c6bf7, #5ec6ff); color: #0c0f1c; font-weight: 800; cursor: pointer; box-shadow: 0 10px 25px rgba(92, 137, 255, 0.3); }
        .action-btn.secondary { background: rgba(255,255,255,0.05); color: #d6dbec; border-color: rgba(255,255,255,0.12); box-shadow: none; }
        .action-btn:active { transform: translateY(1px); }
        .toast { position: fixed; bottom: 20px; right: 20px; padding: 12px 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); background: rgba(20, 22, 36, 0.95); color: #e9ecf7; box-shadow: 0 10px 30px rgba(0,0,0,0.3); display: none; }
        .toast.show { display: block; }
        @media (max-width: 768px) {
            body { padding: 18px; }
            .hero, .section { padding: 18px; }
            .tender-card { flex-direction: column; align-items: flex-start; }
            .score { width: 100%; justify-content: space-between; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="glass hero">
            <div class="hero-title">
                <div class="hero-icon">🎯</div>
                <div>
                    <h1>Tender Intelligence</h1>
                    <div class="subtitle"><span class="status-dot"></span>TES & Phakathi Automation Engine</div>
                    <div class="last-synced">⏱️ Last synced: {{ last_run }}</div>
                </div>
            </div>
            <div class="nav-pills">
                <a class="pill active" href="/dashboard">📊 Dashboard</a>
                <a class="pill" href="#">📅 Bid Calendar</a>
                <a class="pill" href="#">🗂️ Sources</a>
            </div>
            <div class="action-bar">
                <button class="action-btn" data-action="/api/run/daily">🚀 Run Daily Scan</button>
                <button class="action-btn secondary" data-action="/api/run/weekly">🗓️ Generate Weekly Report</button>
                <button class="action-btn secondary" data-action="/health">💚 Health Check</button>
            </div>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Total</div>
                <div class="stat-value">{{ total_tenders }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">High</div>
                <div class="stat-value"><span class="pill-small pill-high">🔥 {{ high_priority }}</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Medium</div>
                <div class="stat-value"><span class="pill-small pill-medium">⚡ {{ medium_priority }}</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Low</div>
                <div class="stat-value"><span class="pill-small pill-low">🧊 {{ low_priority }}</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">TES</div>
                <div class="stat-value"><span class="pill-small pill-neutral">💧 {{ tes_count }}</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Phakathi</div>
                <div class="stat-value"><span class="pill-small pill-neutral">🌐 {{ phakathi_count }}</span></div>
            </div>
        </div>

        <div class="glass section">
            <h2>📑 Active Tenders</h2>
            <div class="filter-row">
                <span class="filter active">All ({{ total_tenders }})</span>
                <span class="filter">TES ({{ tes_count }})</span>
                <span class="filter">Phakathi ({{ phakathi_count }})</span>
                <span class="filter">🔥 High ({{ high_priority }})</span>
                <span class="filter">⚡ Medium ({{ medium_priority }})</span>
                <span class="filter">🧊 Low ({{ low_priority }})</span>
            </div>
            <div class="tenders">
                {% for tender in tenders %}
                <div class="tender-card">
                    <div class="tender-main">
                        <div class="tender-ref">{{ tender.ref }}</div>
                        <div class="tender-title">{{ tender.title }}</div>
                        <div class="tender-meta">
                            <span class="meta-chip">🏷️ {{ tender.source or "Unknown source" }}</span>
                            <span class="meta-chip">📅 {{ tender.closing or "No close date" }}</span>
                            <span class="meta-chip">📍 {{ tender.client or "Unknown client" }}</span>
                            {% if tender.category %}<span class="meta-chip">🧭 {{ tender.category }}</span>{% endif %}
                        </div>
                    </div>
                    <span class="priority-badge priority-{{ tender.priority }}">{{ tender.priority }}</span>
                    <div class="score">
                        <span class="chip">Score</span>
                        <span>{{ tender.score }}</span>
                    </div>
                </div>
                {% endfor %}
                {% if not tenders %}
                <p style="color: #666; text-align: center; padding: 40px;">No tenders found. Run a scan to populate.</p>
                {% endif %}
            </div>
        </div>
        <div id="toast" class="toast"></div>
    </div>
    <script>
        const toast = document.getElementById('toast');
        function showToast(message) {
            toast.textContent = message;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2500);
        }
        async function triggerAction(url) {
            try {
                const res = await fetch(url);
                const data = await res.json();
                if (res.ok) {
                    showToast(data.message || 'Action completed');
                } else {
                    showToast(`Error: ${data.message || res.statusText}`);
                }
            } catch (err) {
                showToast(`Request failed: ${err.message}`);
            }
        }
        document.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', () => triggerAction(btn.dataset.action));
        });
    </script>
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
    tes = pakati = 0
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
                    source = t.get("source") or t.get("client") or ""
                    source_lower = source.lower()
                    if "tes" in source_lower:
                        tes += 1
                    if "phakathi" in source_lower:
                        pakati += 1
                    tenders.append({
                        "ref": t.get("ref", "N/A"),
                        "title": t.get("title", "Unknown"),
                        "client": t.get("client", ""),
                        "category": t.get("category", ""),
                        "closing": t.get("closing_date", ""),
                        "source": t.get("source", ""),
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
        tes_count=tes,
        phakathi_count=pakati,
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
