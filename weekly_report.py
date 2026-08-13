#!/usr/bin/env python3
# ==========================================================
# WEEKLY TENDER DASHBOARD REPORT
# Generates comprehensive weekly summary with analytics
# ==========================================================

import os
import sys
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml
from utils.scraper_monitor import load_scraper_health

# Load config
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
with open(config_path, "r") as f:
    CONFIG = yaml.safe_load(f)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = (CONFIG.get("paths", {}) or {}).get("output_dir", os.path.join(PROJECT_DIR, "output"))
REPORTS_DIR = os.path.join(PROJECT_DIR, "reports")

def _get_env(*names, default=""):
    """Return the first non-empty environment variable from `names`."""
    for name in names:
        value = os.environ.get(name)
        if value not in (None, ""):
            return value
    return default


def _get_bool_env(*names, default=False):
    """Read a boolean environment variable using common truthy values."""
    value = _get_env(*names, default=str(default))
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _get_list_env(*names):
    """Split a comma-separated environment variable into a clean list."""
    value = _get_env(*names, default="")
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


DB_PATH = _get_env("DB_PATH", default=os.path.join(PROJECT_DIR, "data", "tenders.db"))


# Email settings
EMAIL_CONFIG = CONFIG.get("email", {}) or {}
EMAIL_ENABLED = _get_bool_env(
    "EMAIL_ENABLED",
    "TENDERSCAN_EMAIL_ENABLED",
    default=EMAIL_CONFIG.get("enabled", False),
)
SMTP_SERVER = _get_env(
    "SMTP_SERVER",
    "TENDERSCAN_SMTP_SERVER",
    default=EMAIL_CONFIG.get("smtp_server", "smtp.gmail.com"),
)
SMTP_PORT = int(
    _get_env(
        "SMTP_PORT",
        "TENDERSCAN_SMTP_PORT",
        default=str(EMAIL_CONFIG.get("smtp_port", 587)),
    )
)
SMTP_USER = _get_env("SMTP_USER", "TENDERSCAN_SMTP_USER", default="")
SMTP_PASSWORD = _get_env("SMTP_PASSWORD", "TENDERSCAN_SMTP_PASSWORD", default="")
EMAIL_TO = _get_list_env("EMAIL_TO", "TENDERSCAN_EMAIL_TO") or list(
    EMAIL_CONFIG.get("to_addresses", [])
)
EMAIL_FROM = _get_env(
    "EMAIL_FROM",
    "TENDERSCAN_EMAIL_FROM",
    default=EMAIL_CONFIG.get("from_address", SMTP_USER),
)


def _parse_datetime(value):
    """Parse a SQLite timestamp or ISO-like string into a datetime."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d %b %Y",
        "%d %B %Y",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _parse_date(value):
    """Parse a date-like value into a date object."""
    parsed = _parse_datetime(value)
    return parsed.date() if parsed else None


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """Return True when a table exists in the connected SQLite database."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _default_weekly_stats():
    """Create the default weekly report payload."""
    return {
        "total": 0,
        "this_week": 0,
        "by_type": {"MEXEL": 0, "Unknown": 0},
        "by_priority": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
        "by_status": {},
        "closing_soon": [],
        "high_priority": [],
        "top_sources": {},
    }


def get_weekly_stats():
    """Extract weekly reporting stats from SQLite."""
    if not os.path.exists(DB_PATH):
        return None

    stats = _default_weekly_stats()
    now = datetime.now()
    today = now.date()
    week_ago = now - timedelta(days=7)

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ref, title, client, category, source, composite_score,
                       priority, closing_date, status, created_at
                FROM tenders
                ORDER BY created_at DESC
                """
            )
            rows = [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as exc:
        print(f"❌ Failed to read SQLite weekly stats: {exc}")
        return None

    for row in rows:
        stats["total"] += 1

        title = row.get("title") or ""
        client = row.get("client") or ""
        tender_type = (row.get("category") or "Unknown").strip() or "Unknown"
        source = (row.get("source") or "Unknown").strip() or "Unknown"
        status = (row.get("status") or "Open").strip() or "Open"
        priority = (row.get("priority") or "LOW").strip().upper() or "LOW"
        ref = row.get("ref") or ""

        try:
            score = float(row.get("composite_score") or 0)
        except (TypeError, ValueError):
            score = 0.0

        stats["by_type"][tender_type] = stats["by_type"].get(tender_type, 0) + 1
        stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        stats["top_sources"][source] = stats["top_sources"].get(source, 0) + 1

        created_at = _parse_datetime(row.get("created_at"))
        if created_at and created_at >= week_ago:
            stats["this_week"] += 1

        closing_date = _parse_date(row.get("closing_date"))
        if closing_date:
            days_left = (closing_date - today).days
            if 0 <= days_left <= 7 and status.lower() == "open":
                stats["closing_soon"].append(
                    {
                        "ref": ref,
                        "title": title[:50],
                        "client": client,
                        "days_left": days_left,
                        "priority": priority,
                    }
                )

        if priority == "HIGH" and status.lower() == "open":
            stats["high_priority"].append(
                {
                    "ref": ref,
                    "title": title[:50],
                    "client": client,
                    "type": tender_type,
                    "score": score,
                }
            )

    stats["closing_soon"] = sorted(stats["closing_soon"], key=lambda x: x["days_left"])[:10]
    stats["high_priority"] = sorted(
        stats["high_priority"],
        key=lambda x: x.get("score", 0),
        reverse=True,
    )[:10]
    stats["top_sources"] = dict(
        sorted(stats["top_sources"].items(), key=lambda x: x[1], reverse=True)[:5]
    )

    return stats


def _load_scraper_health():
    """Load scraper health, preferring the persisted SQLite run history."""
    return load_scraper_health(output_dir=OUTPUT_DIR, db_path=DB_PATH, prefer_db=True)


def generate_weekly_html(stats: dict) -> str:
    """Generate weekly dashboard HTML"""
    
    if not stats:
        return "<html><body><h1>No data available</h1></body></html>"
    
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; max-width: 900px; margin: 0 auto; }}
            h1 {{ color: #1565C0; border-bottom: 3px solid #1565C0; padding-bottom: 10px; }}
            h2 {{ color: #2E7D32; margin-top: 30px; }}
            .dashboard {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
            .card {{ background: #f5f5f5; padding: 20px; border-radius: 8px; text-align: center; }}
            .card.highlight {{ background: #E3F2FD; border: 2px solid #1565C0; }}
            .card h3 {{ margin: 0; font-size: 2em; color: #1565C0; }}
            .card p {{ margin: 5px 0 0 0; color: #666; }}
            .priority-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }}
            .priority-card {{ padding: 15px; border-radius: 8px; text-align: center; }}
            .priority-card.high {{ background: #FFEBEE; color: #C62828; }}
            .priority-card.medium {{ background: #FFF8E1; color: #F57F17; }}
            .priority-card.low {{ background: #E8F5E9; color: #2E7D32; }}
            .priority-card h3 {{ font-size: 2.5em; margin: 0; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th {{ background: #1565C0; color: white; padding: 12px; text-align: left; }}
            td {{ border: 1px solid #ddd; padding: 10px; }}
            tr:nth-child(even) {{ background: #f9f9f9; }}
            .urgent {{ background: #FFEBEE; }}
            .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }}
            .badge-high {{ background: #F44336; color: white; }}
            .badge-medium {{ background: #FFC107; color: black; }}
            .badge-mexel {{ background: #2196F3; color: white; }}
            .chart-container {{ margin: 20px 0; }}
            .bar {{ height: 25px; background: #1565C0; margin: 5px 0; border-radius: 3px; color: white; padding: 3px 10px; }}
        </style>
    </head>
    <body>
        <h1>📊 Weekly Tender Dashboard</h1>
        <p><strong>Report Period:</strong> {week_ago.strftime("%Y-%m-%d")} to {now.strftime("%Y-%m-%d")}</p>
        
        <div class="dashboard">
            <div class="card highlight">
                <h3>{stats['total']}</h3>
                <p>Total Tenders</p>
            </div>
            <div class="card">
                <h3>{stats['this_week']}</h3>
                <p>Added This Week</p>
            </div>
            <div class="card">
                <h3>{len(stats['closing_soon'])}</h3>
                <p>Closing Soon</p>
            </div>
            <div class="card">
                <h3>{len(stats['high_priority'])}</h3>
                <p>High Priority Open</p>
            </div>
        </div>
        
        <h2>🎯 Priority Distribution</h2>
        <div class="priority-grid">
            <div class="priority-card high">
                <h3>{stats['by_priority']['HIGH']}</h3>
                <p>🔥 HIGH</p>
            </div>
            <div class="priority-card medium">
                <h3>{stats['by_priority']['MEDIUM']}</h3>
                <p>✅ MEDIUM</p>
            </div>
            <div class="priority-card low">
                <h3>{stats['by_priority']['LOW']}</h3>
                <p>📝 LOW</p>
            </div>
        </div>
        
        <h2>📁 By Category</h2>
        <div class="chart-container">
    """
    
    max_type = max(stats['by_type'].values()) if stats['by_type'] else 1
    for t_type, count in stats['by_type'].items():
        width = int((count / max_type) * 100) if max_type > 0 else 0
        html += f'<div class="bar" style="width: {max(width, 10)}%">{t_type}: {count}</div>'
    
    html += """
        </div>
        
        <h2>⚠️ Closing Soon (Next 7 Days)</h2>
    """
    
    if stats['closing_soon']:
        html += """
        <table>
            <tr><th>Ref</th><th>Tender</th><th>Client</th><th>Days Left</th><th>Priority</th></tr>
        """
        for t in stats['closing_soon']:
            urgent = "urgent" if t['days_left'] <= 3 else ""
            badge = "badge-high" if t['priority'] == "HIGH" else "badge-medium"
            html += f"""
            <tr class="{urgent}">
                <td>{t['ref']}</td>
                <td>{t['title']}...</td>
                <td>{t['client']}</td>
                <td><strong>{t['days_left']} days</strong></td>
                <td><span class="badge {badge}">{t['priority']}</span></td>
            </tr>
            """
        html += "</table>"
    else:
        html += "<p>No tenders closing in the next 7 days.</p>"
    
    html += """
        <h2>🔥 Top High Priority Opportunities</h2>
    """
    
    if stats['high_priority']:
        html += """
        <table>
            <tr><th>Ref</th><th>Tender</th><th>Client</th><th>Type</th><th>Score</th></tr>
        """
        for t in stats['high_priority'][:5]:
            type_badge = "badge-mexel"
            html += f"""
            <tr>
                <td>{t['ref']}</td>
                <td>{t['title']}...</td>
                <td>{t['client']}</td>
                <td><span class="badge {type_badge}">{t['type']}</span></td>
                <td><strong>{t['score']}/10</strong></td>
            </tr>
            """
        html += "</table>"
    else:
        html += "<p>No high priority open tenders.</p>"
    
    # ----------------------------------------------------------
    # Scraper Health (reliability tracking)
    # ----------------------------------------------------------
    html += """
        <h2>🩺 Scraper Health</h2>
    """

    health = _load_scraper_health()

    if isinstance(health, dict) and health:
        html += """
        <table>
            <tr>
                <th>Source</th>
                <th>Status</th>
                <th>Success Rate</th>
                <th>Avg Tenders</th>
                <th>Avg Duration</th>
                <th>Consecutive Failures</th>
            </tr>
        """

        def _key(item):
            src, data = item
            data = data or {}
            cf = int(data.get("consecutive_failures") or 0)
            sr = float(data.get("success_rate") or 0.0)
            return (-cf, sr, src)

        for source, data in sorted(health.items(), key=_key):
            data = data or {}
            status = data.get("status", "unknown")
            sr = float(data.get("success_rate") or 0.0)
            avg_tenders = data.get("avg_tenders", 0.0)
            avg_dur = data.get("avg_duration", 0.0)
            cf = int(data.get("consecutive_failures") or 0)
            row_style = " style=\"background: #FFEBEE;\"" if cf >= 3 else ""
            html += f"""
            <tr{row_style}>
                <td>{source}</td>
                <td>{status}</td>
                <td>{sr:.0%}</td>
                <td>{avg_tenders}</td>
                <td>{avg_dur}s</td>
                <td><strong>{cf}</strong></td>
            </tr>
            """

        html += "</table>"

        problem_sources = [s for s, d in health.items() if int((d or {}).get("consecutive_failures") or 0) >= 3]
        if problem_sources:
            html += "<p><strong>Recommendation:</strong> Consider disabling or investigating: " + ", ".join(problem_sources) + "</p>"
    else:
        html += "<p>No scraper health data found.</p>"

    html += """
        <h2>🏭 Top Sources</h2>
        <div class="chart-container">
    """
    
    max_ind = max(stats['top_sources'].values()) if stats['top_sources'] else 1
    for ind, count in stats['top_sources'].items():
        width = int((count / max_ind) * 100) if max_ind > 0 else 0
        html += f'<div class="bar" style="width: {max(width, 10)}%">{ind}: {count}</div>'
    
    html += f"""
        </div>
        
        <hr>
        <p style="color: #666; font-size: 0.8em; text-align: center;">
            Generated by TenderScan Engine | {now.strftime("%Y-%m-%d %H:%M")}
        </p>
    </body>
    </html>
    """
    
    return html


def save_weekly_report(html: str) -> str:
    """Save weekly report as HTML file"""
    
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    filename = f"weekly_report_{datetime.now().strftime('%Y%m%d')}.html"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    
    return filepath


def send_weekly_email(html: str, report_path: str) -> bool:
    """Send the weekly report via email and attach the generated HTML report."""
    
    if not EMAIL_ENABLED:
        print("📧 Email disabled - skipping")
        return False
    
    if not SMTP_USER or not SMTP_PASSWORD or not EMAIL_TO:
        print("❌ Email configuration incomplete")
        return False
    
    try:
        msg = MIMEMultipart()
        msg["Subject"] = f"📊 Weekly Tender Dashboard - {datetime.now().strftime('%Y-%m-%d')}"
        msg["From"] = EMAIL_FROM
        msg["To"] = ", ".join(EMAIL_TO)
        
        msg.attach(MIMEText(html, "html"))
        
        if report_path and os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as file_obj:
                attachment = MIMEText(file_obj.read(), "html", "utf-8")
            attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=os.path.basename(report_path),
            )
            msg.attach(attachment)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        
        print(f"✅ Weekly report sent to {', '.join(EMAIL_TO)}")
        return True
        
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False


def run_weekly():
    """Main weekly report function"""
    
    print(f"\n📊 TenderScan Weekly Report - {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 50)
    
    print("\n📈 Extracting statistics...")
    stats = get_weekly_stats()
    
    if not stats:
        print("❌ No data available")
        return
    
    print("📝 Generating report...")
    html = generate_weekly_html(stats)
    
    report_path = save_weekly_report(html)
    print(f"💾 Report saved: {report_path}")
    
    send_weekly_email(html, report_path)
    
    print("\n" + "=" * 50)
    print("📊 WEEKLY SUMMARY")
    print(f"   Total tenders:    {stats['total']}")
    print(f"   Added this week:  {stats['this_week']}")
    print(f"   Closing soon:     {len(stats['closing_soon'])}")
    print(f"   HIGH priority:    {stats['by_priority']['HIGH']}")
    print(f"   Mexel tenders:    {stats['by_type']['MEXEL']}")
    print("=" * 50)
    
    return stats


if __name__ == "__main__":
    run_weekly()
