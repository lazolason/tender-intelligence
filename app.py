# ==========================================================
# TENDER INTELLIGENCE SYSTEM — FLASK API
# Flask API for tender intelligence dashboard
# ==========================================================

from collections import defaultdict, deque
from flask import Flask, abort, jsonify, request, send_from_directory
from werkzeug.exceptions import RequestEntityTooLarge
from datetime import datetime, timezone
from functools import wraps
import hmac
import logging
import os
import json
import requests
import sqlite3
import threading
import time
from typing import Any, Dict, Optional
from flask_cors import CORS
from dotenv import load_dotenv

from utils.db_writer import DatabaseWriter
from utils.config_validator import load_and_validate_config, ConfigValidationError
from utils.dashboard_snapshot import inspect_dashboard_snapshot
from utils.launchd_validator import inspect_default_launchd_jobs
from utils.run_status import inspect_daily_run_status
from utils.scraper_monitor import load_scraper_health, summarize_scraper_health_status

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp without microseconds."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _env_flag(name: str, default: Optional[bool] = None) -> Optional[bool]:
    """Read an optional boolean flag from the environment."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

# ----------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_DIR, ".env"))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_REQUEST_BYTES", "65536"))

DASHBOARD_DIR = os.path.join(PROJECT_DIR, "dashboard")
DB_PATH = os.environ.get("DB_PATH", os.path.join(PROJECT_DIR, "data", "tenders.db"))
db_writer = DatabaseWriter(DB_PATH)
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./output")
API_KEY = os.environ.get("API_KEY", "").strip()
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if CORS_ORIGINS:
    CORS(
        app,
        resources={r"/api/*": {"origins": CORS_ORIGINS}, r"/cron/*": {"origins": CORS_ORIGINS}},
        methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
        supports_credentials=False,
        max_age=600,
    )
OPENAI_TIMEOUT = int(os.environ.get("OPENAI_TIMEOUT", "30"))
RATE_LIMIT_STATE: dict[str, deque] = defaultdict(deque)
RATE_LIMIT_LOCK = threading.Lock()
ALLOWED_BID_OUTCOMES = {"won", "lost", "withdrawn", "no_bid"}
APP_CONFIG = {}
DASHBOARD_SNAPSHOT_PATH = os.path.join(PROJECT_DIR, "dashboard", "tenders.json")
DAILY_RUN_STATUS_PATH = os.path.join(PROJECT_DIR, "output", "last_daily_run.json")
DASHBOARD_SHOW_ALL = os.environ.get("DASHBOARD_SHOW_ALL", "").strip().lower() in ("1", "true", "yes")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://localhost:5001/").strip() or "http://localhost:5001/"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)
try:
    APP_CONFIG = load_and_validate_config()
except (FileNotFoundError, ConfigValidationError) as exc:
    logger.warning("App config unavailable for API startup: %s", exc)
    APP_CONFIG = {}

ENABLE_SELENIUM = _env_flag(
    "ENABLE_SELENIUM",
    default=bool((APP_CONFIG.get("scrapers") or {}).get("enable_selenium", False)),
)


def _json_error(message: str, status_code: int = 400, **extra):
    """Create a consistent JSON error response."""
    payload = {"error": message}
    payload.update(extra)
    return jsonify(payload), status_code


def _get_client_ip() -> str:
    """Return the socket peer IP; untrusted forwarding headers are ignored."""
    return request.remote_addr or "unknown"


def rate_limit(limit: int, window_seconds: int):
    """Apply a simple in-memory rate limit per route and client IP."""

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if request.method == "OPTIONS":
                return f(*args, **kwargs)

            now = time.time()
            key = f"{request.endpoint}:{_get_client_ip()}"

            with RATE_LIMIT_LOCK:
                bucket = RATE_LIMIT_STATE[key]
                while bucket and bucket[0] <= now - window_seconds:
                    bucket.popleft()
                if len(bucket) >= limit:
                    retry_after = max(1, int(window_seconds - (now - bucket[0])))
                    return _json_error(
                        "Rate limit exceeded",
                        429,
                        limit=limit,
                        window_seconds=window_seconds,
                        retry_after=retry_after,
                    )
                bucket.append(now)

            return f(*args, **kwargs)

        return wrapped

    return decorator


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """Return True when a table exists in the SQLite database."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _safe_table_count(conn: sqlite3.Connection, table_name: str) -> Optional[int]:
    """Return table count when the table exists, otherwise None."""
    if not _table_exists(conn, table_name):
        return None
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return int(cursor.fetchone()[0])


def _expected_dashboard_record_count(conn: sqlite3.Connection) -> Optional[int]:
    """Return the DB count that should back the current dashboard snapshot."""
    if not _table_exists(conn, "tenders"):
        return None

    mexel_only = bool((APP_CONFIG.get("classification", {}) or {}).get("mexel_only", False))
    query = """
        SELECT COUNT(*)
        FROM tenders
        WHERE status IN ('Open', 'Active', 'In Progress')
    """
    params = []
    if mexel_only and not DASHBOARD_SHOW_ALL:
        query += " AND category = ?"
        params.append("MEXEL")

    cursor = conn.cursor()
    cursor.execute(query, params)
    return int(cursor.fetchone()[0])


def _load_health_metrics() -> Optional[Dict[str, Any]]:
    """Load scraper health, preferring the persisted SQLite run history."""
    payload = load_scraper_health(output_dir=OUTPUT_DIR, db_path=DB_PATH, prefer_db=True)
    return payload if isinstance(payload, dict) else None


def _get_json_payload() -> Dict[str, Any]:
    """Read and validate a JSON request body."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object")
    return data


def _require_string(
    value: Any,
    field_name: str,
    *,
    max_length: int,
    required: bool = False,
) -> str:
    """Validate and normalize a string field."""
    if value is None:
        if required:
            raise ValueError(f"Missing {field_name}")
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    normalized = value.strip()
    if required and not normalized:
        raise ValueError(f"Missing {field_name}")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} exceeds {max_length} characters")
    return normalized


def _optional_float(value: Any, field_name: str) -> Optional[float]:
    """Parse an optional numeric field."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be numeric")


def _optional_bool(value: Any, field_name: str) -> bool:
    """Parse an optional boolean field with a strict contract."""
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return False
    raise ValueError(f"{field_name} must be a boolean")


def _optional_date(value: Any, field_name: str) -> Optional[str]:
    """Parse an optional date and normalize it to YYYY-MM-DD."""
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string in YYYY-MM-DD format")
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"{field_name} must use YYYY-MM-DD format")


def _resolve_dashboard_asset(path: str) -> Optional[str]:
    """Return a safe dashboard asset path to serve from the repo dashboard directory."""
    requested = (path or "").lstrip("/")
    if not requested:
        requested = "index.html"

    candidate = os.path.join(DASHBOARD_DIR, requested)
    if os.path.isfile(candidate):
        return requested

    # Future-proof simple client-side routes by serving the shell for extensionless paths.
    if "." not in os.path.basename(requested):
        index_path = os.path.join(DASHBOARD_DIR, "index.html")
        if os.path.isfile(index_path):
            return "index.html"

    return None


def _validate_summarize_payload(data: Dict[str, Any]) -> Dict[str, str]:
    """Validate the summarize endpoint payload."""
    tender = data.get("tender")
    if not isinstance(tender, dict):
        raise ValueError("tender must be an object")

    title = _require_string(tender.get("title"), "tender.title", max_length=500)
    description = _require_string(
        tender.get("description"),
        "tender.description",
        max_length=8000,
    )
    if not title and not description:
        raise ValueError("tender.title or tender.description is required")
    return {"title": title, "description": description}


def _validate_bid_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the bid recording endpoint payload."""
    ref = _require_string(data.get("ref"), "ref", max_length=120, required=True)
    company = _require_string(data.get("company"), "company", max_length=120) or "MEXEL"
    outcome = _require_string(data.get("outcome"), "outcome", max_length=32, required=True).lower()
    if outcome not in ALLOWED_BID_OUTCOMES:
        raise ValueError(f"outcome must be one of: {', '.join(sorted(ALLOWED_BID_OUTCOMES))}")

    payload = {
        "ref": ref,
        "company": company,
        "submitted": _optional_bool(data.get("submitted"), "submitted"),
        "outcome": outcome,
        "bid_amount": _optional_float(data.get("bid_amount"), "bid_amount"),
        "winner_name": _require_string(data.get("winner_name"), "winner_name", max_length=255),
        "winning_amount": _optional_float(data.get("winning_amount"), "winning_amount"),
        "bid_date": _optional_date(data.get("bid_date"), "bid_date"),
        "note": _require_string(data.get("note"), "note", max_length=4000),
    }
    return payload

# ----------------------------------------------------------
# API KEY AUTHENTICATION DECORATOR
# ----------------------------------------------------------
def _api_key_is_configured() -> bool:
    """Reject empty and documented placeholder credentials."""
    normalized = (API_KEY or "").strip()
    return bool(normalized) and normalized not in {
        "your-secure-api-key-here",
        "your-random-secret-key",
        "change-me",
    }


def require_api_key(f):
    """Require a configured API key; protected endpoints never fail open."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == "OPTIONS":
            return f(*args, **kwargs)

        if not _api_key_is_configured():
            logger.error("Protected endpoint called without a configured API key")
            return _json_error("Protected API is not configured", 503)

        token = ""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        if not token:
            token = request.headers.get("X-API-Key", "").strip()

        if token and hmac.compare_digest(token, API_KEY):
            return f(*args, **kwargs)

        return _json_error("Unauthorized", 401)

    return decorated_function


@app.errorhandler(RequestEntityTooLarge)
def request_too_large(_error):
    return _json_error("Request body too large", 413)


@app.after_request
def apply_security_headers(response):
    """Apply browser and cache security headers to every response."""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=(), payment=()",
    )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; "
        "form-action 'self'; frame-ancestors 'none'",
    )
    if request.path.startswith(("/api/", "/cron/")):
        response.headers.setdefault("Cache-Control", "no-store")
    if request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

# ----------------------------------------------------------
# ROUTES
# ----------------------------------------------------------
@app.route("/health")
def health():
    response = {
        "status": "healthy",
        "service": "tender-intelligence",
        "version": "2.1",
        "timestamp": _utc_now_iso(),
        "config": {
            "selenium_enabled": ENABLE_SELENIUM,
            "api_key_protected": _api_key_is_configured(),
            "openai_configured": bool((os.environ.get("OPENAI_API_KEY") or "").strip()),
            "output_dir": OUTPUT_DIR,
            "config_loaded": bool(APP_CONFIG),
            "dashboard_url": DASHBOARD_URL,
            "server_software": os.environ.get("SERVER_SOFTWARE", "flask-dev"),
        },
        "database": {
            "path": DB_PATH,
            "exists": os.path.exists(DB_PATH),
        },
    }

    try:
        with sqlite3.connect(DB_PATH) as conn:
            response["database"]["accessible"] = True
            table_counts = {
                "tenders": _safe_table_count(conn, "tenders"),
                "bid_outcomes": _safe_table_count(conn, "bid_outcomes"),
                "pdf_analysis": _safe_table_count(conn, "pdf_analysis"),
                "scraper_runs": _safe_table_count(conn, "scraper_runs"),
            }
            response["database"]["table_counts"] = table_counts
    except sqlite3.Error as exc:
        response["status"] = "degraded"
        response["database"]["accessible"] = False
        response["database"]["error"] = str(exc)

    snapshot_info = inspect_dashboard_snapshot(DASHBOARD_SNAPSHOT_PATH)
    if snapshot_info.get("exists"):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                db_count = _expected_dashboard_record_count(conn)
        except sqlite3.Error:
            db_count = None
        snapshot_count = snapshot_info.get("record_count")
        counts_match = (
            db_count is not None and snapshot_count is not None and int(db_count) == int(snapshot_count)
        )
        snapshot_info["counts_match_db"] = counts_match
        if snapshot_info.get("stale") or counts_match is False:
            response["status"] = "degraded"
    response["dashboard_snapshot"] = snapshot_info

    automation_info = inspect_daily_run_status(DAILY_RUN_STATUS_PATH)
    if automation_info.get("exists"):
        if (
            automation_info.get("stale")
            or automation_info.get("scan_status") == "error"
            or automation_info.get("sync_status") in {"error", "failed"}
        ):
            response["status"] = "degraded"
    response["automation"] = automation_info

    scheduler_jobs = inspect_default_launchd_jobs(PROJECT_DIR)
    if not all(job.get("valid") for job in scheduler_jobs.values()):
        response["status"] = "degraded"
    response["scheduler"] = scheduler_jobs

    health_metrics = _load_health_metrics()
    if isinstance(health_metrics, dict) and health_metrics:
        scraper_summary = summarize_scraper_health_status(health_metrics, problem_threshold=3)
        response["scrapers"] = scraper_summary
        if scraper_summary["problem_sources"] or scraper_summary["latest_failed_sources"]:
            response["status"] = "degraded"
    else:
        response["scrapers"] = {
            "sources_tracked": 0,
            "latest_failed_sources": [],
            "problem_sources": [],
        }

    status_code = 200 if response["status"] == "healthy" else 503
    return jsonify(response), status_code


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_dashboard(path: str):
    """Serve the static dashboard from Flask for single-origin local/prod use."""
    if path == "health" or path.startswith(("api/", "cron/")):
        abort(404)

    asset_path = _resolve_dashboard_asset(path)
    if not asset_path:
        abort(404)

    return send_from_directory(DASHBOARD_DIR, asset_path)

@app.route("/api/summarize", methods=["POST", "OPTIONS"])
@rate_limit(limit=10, window_seconds=60)
@require_api_key
def api_summarize():
    """
    Server-side proxy for OpenAI summarization.
    Requires API key authentication.
    """
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200

    try:
        data = _get_json_payload()
        tender = _validate_summarize_payload(data)
    except ValueError as exc:
        return _json_error(str(exc), 400)

    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY not configured on server"}), 501

    try:
        title = tender["title"]
        description = tender["description"]
        
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
            timeout=OPENAI_TIMEOUT
        )

        if res.status_code >= 400:
            logger.warning("OpenAI summarize request failed: status=%s", res.status_code)
            return _json_error("Summarization provider request failed", 502)

        data = res.json()
        summary = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        ) or "No summary generated."

        return jsonify({"summary": summary, "ts": _utc_now_iso()})
    except Exception:
        logger.exception("Unexpected summarize API failure")
        return _json_error("Unexpected summarization failure", 500)

def _run_daily_response():
    try:
        from daily_runner import run_daily as execute_daily_run

        result = execute_daily_run()
        return jsonify({
            "status": "success",
            "message": "Daily scan completed",
            "timestamp": _utc_now_iso(),
            "result": result,
        })
    except Exception:
        logger.exception("Daily scan API trigger failed")
        return _json_error("Daily scan failed", 500)


def _run_weekly_response():
    try:
        from weekly_report import run_weekly as execute_weekly_run

        result = execute_weekly_run()
        return jsonify({
            "status": "success",
            "message": "Weekly report generated",
            "timestamp": _utc_now_iso(),
            "result": result,
        })
    except Exception:
        logger.exception("Weekly report API trigger failed")
        return _json_error("Weekly report generation failed", 500)


@app.route("/api/run/daily", methods=["GET"])
@app.route("/api/run/weekly", methods=["GET"])
@app.route("/cron/daily", methods=["GET"])
@app.route("/cron/weekly", methods=["GET"])
def reject_get_trigger():
    """State-changing job triggers are never available through GET."""
    abort(405)


@app.route("/api/run/daily", methods=["POST"])
@rate_limit(limit=3, window_seconds=300)
@require_api_key
def run_daily():
    """Trigger the daily scan via an authenticated POST request."""
    return _run_daily_response()


@app.route("/api/run/weekly", methods=["POST"])
@rate_limit(limit=3, window_seconds=300)
@require_api_key
def run_weekly():
    """Trigger the weekly report via an authenticated POST request."""
    return _run_weekly_response()


@app.route("/cron/daily", methods=["POST"])
@rate_limit(limit=3, window_seconds=300)
@require_api_key
def cron_daily():
    """Authenticated scheduler endpoint for the daily scan."""
    return _run_daily_response()


@app.route("/cron/weekly", methods=["POST"])
@rate_limit(limit=3, window_seconds=300)
@require_api_key
def cron_weekly():
    """Authenticated scheduler endpoint for the weekly report."""
    return _run_weekly_response()

@app.route("/api/tenders")
@rate_limit(limit=60, window_seconds=60)
def api_tenders():
    """JSON API for tenders"""
    try:
        json_path = os.path.join(OUTPUT_DIR, "new_tenders.json")
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                return jsonify(json.load(f))
        return jsonify([])
    except Exception:
        logger.exception("Failed to load tender snapshot")
        return _json_error("Failed to load tender snapshot", 500)

@app.route("/api/bids", methods=["POST"])
@rate_limit(limit=20, window_seconds=60)
@require_api_key
def api_record_bid():
    """Record a bid outcome (won, lost, etc.)"""
    try:
        data = _get_json_payload()
        bid = _validate_bid_payload(data)
            
        success = db_writer.record_bid_outcome(
            bid["ref"],
            bid["company"],
            bid["submitted"],
            bid["outcome"],
            bid_amount=bid["bid_amount"],
            winner_name=bid["winner_name"],
            winning_amount=bid["winning_amount"],
            bid_date=bid["bid_date"],
        )
        
        if not success:
            return _json_error("Failed to persist bid outcome", 500)
        if bid["note"] and not db_writer.add_bid_note(bid["ref"], bid["company"], bid["note"]):
            return _json_error("Bid outcome saved but note persistence failed", 500)

        return jsonify({"status": "success"})
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except RequestEntityTooLarge:
        raise
    except Exception:
        logger.exception("Unexpected bid recording failure")
        return _json_error("Unexpected bid recording failure", 500)

@app.route("/api/stats/bids")
@rate_limit(limit=30, window_seconds=60)
def api_bid_stats():
    """Get bid win/loss statistics"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            if not _table_exists(conn, "bid_outcomes"):
                return jsonify({
                    "by_outcome": {},
                    "win_rate": 0.0,
                    "total_bids": 0,
                    "total_wins": 0,
                })
            cursor = conn.cursor()
            cursor.execute("""
                SELECT outcome, COUNT(*) as count 
                FROM bid_outcomes 
                GROUP BY outcome
            """)
            stats = dict(cursor.fetchall())
            
            cursor.execute("SELECT COUNT(*) FROM bid_outcomes WHERE outcome = 'won'")
            wins = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bid_outcomes WHERE bid_submitted = 1")
            total_bids = cursor.fetchone()[0]
            
            win_rate = (wins / total_bids * 100) if total_bids > 0 else 0
            
            return jsonify({
                "by_outcome": stats,
                "win_rate": round(win_rate, 1),
                "total_bids": total_bids,
                "total_wins": wins
            })
    except Exception:
        logger.exception("Failed to calculate bid statistics")
        return _json_error("Failed to calculate bid statistics", 500)

@app.route("/api/tenders/<path:ref>/analysis")
@rate_limit(limit=30, window_seconds=60)
def api_tender_analysis(ref):
    """Get PDF analysis for a specific tender"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            if not _table_exists(conn, "pdf_analysis"):
                return jsonify({"error": "Analysis not found"}), 404
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pdf_analysis WHERE tender_ref = ?", (ref,))
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                # Parse JSON fields
                for field in ["requirements", "deadlines", "values_extracted", "contact_info"]:
                    if result.get(field):
                        result[field] = json.loads(result[field])
                return jsonify(result)
            return jsonify({"error": "Analysis not found"}), 404
    except Exception:
        logger.exception("Failed to load tender analysis")
        return _json_error("Failed to load tender analysis", 500)
# ----------------------------------------------------------
# MAIN
# ----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("APP_HOST", "127.0.0.1").strip() or "127.0.0.1"
    app.run(host=host, port=port, debug=False)
