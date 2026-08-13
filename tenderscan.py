# ==========================================================
# TENDER AUTOMATION ENGINE — MAIN RUNNER
# Scrapes all sources, classifies, scores, persists to SQLite, creates folders
# ==========================================================

import json
import yaml
from datetime import datetime
import sys
import os
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

# Import utils
from scrapers import BaseScraper, get_active_scrapers
from utils.db_writer import DatabaseWriter
from utils.folder_tools import create_tender_folder
from utils.logging_tools import write_log, log_error, rotate_log_if_needed
from utils.pipeline_validation import validate_tender_batch
from utils.procurement_plan_linker import link_planned_opportunities
from utils.scraper_monitor import ScraperMonitor
from utils.config_validator import validate_env_on_startup

# Import the central classification engine
from classify_engine import classify_tender

# ----------------------------------------------------------
# LOAD CONFIG
# ----------------------------------------------------------
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
with open(config_path, "r") as f:
    CONFIG = yaml.safe_load(f)

# Paths
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DB_PATH", os.path.join(PROJECT_DIR, "data", "tenders.db"))


def _portable_runtime_path(env_name, configured_path, fallback_path):
    """Use configured local paths only when their platform root exists."""
    override = os.getenv(env_name)
    if override:
        return override
    configured = os.path.expanduser(str(configured_path or ""))
    if not configured:
        return fallback_path
    if not os.path.isabs(configured):
        return os.path.join(PROJECT_DIR, configured)
    # macOS paths from config.yaml must not be created on Linux/CI hosts.
    anchor = os.path.join(os.path.sep, *configured.split(os.path.sep)[1:2])
    return configured if os.path.exists(anchor) else fallback_path


ACTIVE_TENDERS_DIR = _portable_runtime_path(
    "ACTIVE_TENDERS_DIR",
    CONFIG["paths"]["active_tenders"],
    os.path.join(PROJECT_DIR, "data", "active_tenders"),
)
OUTPUT_DIR = _portable_runtime_path(
    "OUTPUT_DIR",
    CONFIG["paths"]["output_dir"],
    os.path.join(PROJECT_DIR, "output"),
)
LOG_FILE = _portable_runtime_path(
    "LOG_FILE",
    CONFIG["paths"]["log_file"],
    os.path.join(PROJECT_DIR, "logs", "scraper.log"),
)

# Selenium scraper toggle (set to True to enable)
ENABLE_SELENIUM = CONFIG.get("scrapers", {}).get("enable_selenium", True)

# Dashboard retains the last N tenders to avoid an empty UI when no new items are added
MAX_DASHBOARD_TENDERS = 200

# Deduplication Settings
DEDUPE_CONFIG = CONFIG.get(
    "deduplication",
    {
        "semantic_threshold": 0.75,
        "fuzzy_threshold": 85,
        "date_window_days": 7,
        "require_same_source": False,
        "limit_db_check": 200,
    },
)

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ACTIVE_TENDERS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# ----------------------------------------------------------
# PHASE 1: INTELLIGENCE ENHANCEMENTS (OPTIONAL)
# ----------------------------------------------------------
try:
    from utils.pdf_analyzer import add_pdf_analysis_to_tender

    PDF_ANALYZER_AVAILABLE = True
except ImportError:
    PDF_ANALYZER_AVAILABLE = False
    log_error(
        LOG_FILE,
        "PDF analyzer not available - install with: pip install pdfplumber pypdf",
    )

try:
    from utils.semantic_duplicate_detector import (
        build_semantic_index,
        filter_duplicates,
        find_semantic_duplicate,
    )

    SEMANTIC_DEDUP_AVAILABLE = True
except ImportError:
    SEMANTIC_DEDUP_AVAILABLE = False
    log_error(
        LOG_FILE,
        "Semantic deduplication not available - install with: pip install sentence-transformers torch scikit-learn",
    )

try:
    from utils.bid_tracker import (
        record_bid_outcome,
        get_win_rates,
        get_client_performance,
    )

    BID_TRACKER_AVAILABLE = True
except ImportError:
    BID_TRACKER_AVAILABLE = False
    log_error(LOG_FILE, "Bid tracker not available - install with: pip install")

try:
    from utils.multi_channel_alerts import send_slack_alert, send_sms_alert, smart_alert

    MULTI_CHANNEL_ALERTS_AVAILABLE = True
except ImportError:
    MULTI_CHANNEL_ALERTS_AVAILABLE = False
    log_error(
        LOG_FILE,
        "Multi-channel alerts not available - install with: pip install slack-sdk twilio",
    )

# ----------------------------------------------------------
# INITIALISE DATABASE WRITER
# ----------------------------------------------------------
db_writer = DatabaseWriter(DB_PATH, log_file_path=LOG_FILE)


# ----------------------------------------------------------
# RUN ALL SCRAPERS (PARALLEL)
# ----------------------------------------------------------
def run_all_scrapers(
    monitor: ScraperMonitor = None, max_workers: int = 5, timeout: int = 300
):
    """
    Run all scrapers in parallel using ThreadPoolExecutor.

    Args:
        monitor: ScraperMonitor instance for tracking scraper health
        max_workers: Maximum number of concurrent scrapers (default: 5)
        timeout: Global timeout in seconds for all scrapers (default: 300)

    Returns:
        List of all tenders found across all scrapers
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

    all_tenders = []
    failed_sources = []
    monitor = monitor or ScraperMonitor(output_dir=OUTPUT_DIR, db_path=DB_PATH)
    scraper_instances = get_active_scrapers(enable_selenium=ENABLE_SELENIUM)

    def run_scraper(scraper: BaseScraper):
        """Worker function to run a single scraper with monitoring."""
        from utils.scraper_monitor import CircuitOpenError

        try:
            with monitor.track(scraper.source_name) as run:
                write_log(LOG_FILE, f"=== Scraping {scraper.source_name} ===")
                tenders = scraper.run(raise_on_error=True)
                run.tenders_found = len(tenders)
            write_log(LOG_FILE, f"{scraper.source_name}: {len(tenders)} tenders found")
            return scraper.source_name, tenders, None
        except CircuitOpenError:
            msg = f"Skipping {scraper.source_name} (Circuit Open)"
            write_log(LOG_FILE, msg, "INFO")
            return scraper.source_name, [], msg
        except ImportError as e:
            error_msg = f"Import failed for {scraper.source_name}: {e}"
            log_error(LOG_FILE, error_msg)
            return scraper.source_name, [], error_msg
        except Exception as e:
            error_msg = f"{scraper.source_name} scraper failed: {e}"
            log_error(LOG_FILE, error_msg)
            return scraper.source_name, [], error_msg

    write_log(LOG_FILE, f"🚀 Starting parallel scraping with {max_workers} workers...")
    write_log(
        LOG_FILE,
        "Active scrapers: " + ", ".join(scraper.source_name for scraper in scraper_instances),
    )

    # Execute scrapers in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_scraper = {
            executor.submit(run_scraper, scraper): scraper.source_name
            for scraper in scraper_instances
        }

        try:
            # Collect results as they complete
            for future in as_completed(future_to_scraper, timeout=timeout):
                scraper_name = future_to_scraper[future]
                try:
                    name, tenders, error = future.result()
                    if error:
                        failed_sources.append(name)
                    else:
                        all_tenders.extend(tenders)
                except Exception as e:
                    log_error(
                        LOG_FILE, f"Unexpected error processing {scraper_name}: {e}"
                    )
                    failed_sources.append(scraper_name)
        except TimeoutError:
            write_log(
                LOG_FILE, f"⚠️  Global scraping timeout ({timeout}s) reached", "WARNING"
            )
            # Cancel remaining futures
            for future in future_to_scraper:
                future.cancel()

    if failed_sources:
        write_log(
            LOG_FILE,
            f"Failed sources this run: {', '.join(sorted(set(failed_sources)))}",
            "WARNING",
        )

    # NEW: Cross-Source Semantic Deduplication
    if SEMANTIC_DEDUP_AVAILABLE and all_tenders:
        dedupe_started = perf_counter()
        before_count = len(all_tenders)
        all_tenders, duplicate_info = filter_duplicates(
            all_tenders,
            semantic_threshold=DEDUPE_CONFIG["semantic_threshold"],
            fuzzy_threshold=DEDUPE_CONFIG["fuzzy_threshold"],
            date_window_days=DEDUPE_CONFIG["date_window_days"],
            require_same_source=DEDUPE_CONFIG["require_same_source"],
        )
        dedupe_duration = perf_counter() - dedupe_started
        removed_count = before_count - len(all_tenders)
        if removed_count > 0:
            write_log(
                LOG_FILE,
                f"✂️  Removed {removed_count} semantic duplicates across sources in {dedupe_duration:.2f}s",
            )
        else:
            write_log(
                LOG_FILE,
                f"Semantic cross-source dedup checked {before_count} tenders in {dedupe_duration:.2f}s",
            )

    write_log(
        LOG_FILE, f"✅ Parallel scraping complete. Total tenders: {len(all_tenders)}"
    )
    return all_tenders


# ----------------------------------------------------------
# PROCESS TENDERS WITH SCORING
# ----------------------------------------------------------
def process_tenders(tenders, *, return_stats=False):
    total_added = 0
    new_items = []
    excluded_count = 0

    # Fetch recent tenders from DB for semantic comparison (avoid re-adding)
    recent_db_tenders = db_writer.get_recent_tenders(
        limit=DEDUPE_CONFIG.get("limit_db_check", 200)
    )
    recent_refs = {
        str(tender.get("ref", "")).strip().upper()
        for tender in recent_db_tenders
        if tender.get("ref")
    }
    semantic_db_index = None
    if SEMANTIC_DEDUP_AVAILABLE and recent_db_tenders:
        semantic_index_started = perf_counter()
        semantic_db_index = build_semantic_index(recent_db_tenders)
        write_log(
            LOG_FILE,
            f"Prepared semantic dedup index for {len(recent_db_tenders)} recent DB tenders in {perf_counter() - semantic_index_started:.2f}s",
        )

    dedupe_started = perf_counter()
    exact_ref_refreshes = 0
    updated_count = 0
    unchanged_count = 0
    semantic_skips = 0

    for t in tenders:
        try:
            ref = str(t.get("ref", "NA")).strip().upper()
            title = t.get("title", "")
            description = t.get("description", title)
            classification = classify_tender(title, description)
            t["category"] = classification["category"]
            t["reason"] = classification["reason"]
            t["short_title"] = classification["short_title"]
            t["matched_keywords"] = classification.get("matched_keywords", [])

            # Classification is centralized here; excluded records must not be
            # deduplicated, scored, persisted, or emitted to dashboard outputs.
            if classification["category"] == "EXCLUDED":
                write_log(LOG_FILE, f"[SKIP] {ref}: {classification['reason']}")
                excluded_count += 1
                continue

            # Exact references are refreshed; semantic matching only guards new refs.
            exact_ref_exists = ref != "NA" and ref in recent_refs
            if exact_ref_exists:
                exact_ref_refreshes += 1

            # Semantic Duplicate Check against Database
            if (
                not exact_ref_exists
                and SEMANTIC_DEDUP_AVAILABLE
                and semantic_db_index is not None
            ):
                match = find_semantic_duplicate(
                    t,
                    existing_index=semantic_db_index,
                    semantic_threshold=DEDUPE_CONFIG["semantic_threshold"],
                    fuzzy_threshold=DEDUPE_CONFIG["fuzzy_threshold"],
                    date_window_days=DEDUPE_CONFIG["date_window_days"],
                    require_same_source=DEDUPE_CONFIG["require_same_source"],
                )
                if match and match.is_duplicate:
                    write_log(
                        LOG_FILE,
                        f"[SKIP] {ref}: Semantic duplicate of {match.existing_ref} ({match.reason})",
                    )
                    semantic_skips += 1
                    continue

            client = t.get("client", "")
            url = t.get("url", "")

            action, scores, classification = db_writer.upsert_tender_with_scoring(t)
            if action == "excluded":
                excluded_count += 1
                continue

            if action == "updated":
                updated_count += 1
                write_log(LOG_FILE, f"[UPDATE] {ref}: Refreshed changed tender fields")
            elif action == "unchanged":
                unchanged_count += 1

            if action == "inserted":
                total_added += 1
                t["category"] = classification["category"]
                t["reason"] = classification["reason"]
                t["short_title"] = classification["short_title"]
                t["matched_keywords"] = classification.get("matched_keywords", [])
                t["scores"] = scores
                new_items.append(t)

                # Phase 1: Enhanced PDF Analysis
                if PDF_ANALYZER_AVAILABLE and url and url.lower().endswith(".pdf"):
                    try:
                        t = add_pdf_analysis_to_tender(t)
                        # NEW: Save analysis to DB
                        if "pdf_analysis" in t:
                            # Re-map the flat fields back to the structure save_pdf_analysis expects
                            analysis_data = {
                                "page_count": t.get("pdf_analysis", {}).get(
                                    "page_count"
                                ),
                                "word_count": t.get("pdf_analysis", {}).get(
                                    "word_count"
                                ),
                                "requirements": t.get("pdf_requirements", []),
                                "deadlines": t.get("pdf_deadlines", []),
                                "values": t.get("pdf_values", []),
                                "contact": t.get("pdf_contact", {}),
                                "text": t.get(
                                    "pdf_text", ""
                                ),  # Assuming we might want to store more text later
                            }
                            db_writer.save_pdf_analysis(ref, analysis_data)

                        write_log(
                            LOG_FILE,
                            f"[PDF] Analyzed: {ref} - {len(t.get('pdf_requirements', []))} requirements found",
                        )
                    except Exception as e:
                        log_error(LOG_FILE, f"PDF analysis failed for {ref}: {e}")

                # Create tender folder
                folder_path = create_tender_folder(
                    base_dir=ACTIVE_TENDERS_DIR,
                    ref=ref,
                    client=client,
                    short_title=classification["short_title"],
                )

                write_log(
                    LOG_FILE,
                    f"[{scores['priority']}] Added: {t.get('title')} → {classification['category']} (Score: {scores['composite_score']})",
                )

        except Exception as e:
            log_error(LOG_FILE, f"Error processing tender: {e}")
            continue

    write_log(
        LOG_FILE,
        f"DB dedup/upsert checks completed in {perf_counter() - dedupe_started:.2f}s "
        f"(exact_ref_refreshes={exact_ref_refreshes}, updated={updated_count}, "
        f"unchanged={unchanged_count}, semantic_skips={semantic_skips}, candidates={len(tenders)})",
    )

    if excluded_count > 0:
        write_log(
            LOG_FILE,
            f"Excluded {excluded_count} out-of-scope tenders (construction, security, etc.)",
        )

    linkage_stats = {"linked": 0}
    if total_added or updated_count:
        try:
            linkage_stats = link_planned_opportunities(db_writer.db_path)
            if linkage_stats["linked"]:
                write_log(
                    LOG_FILE,
                    f"Linked {linkage_stats['linked']} procurement plan(s) to live tenders",
                )
        except Exception as exc:
            log_error(LOG_FILE, f"Procurement plan linkage failed: {exc}")

    stats = {
        "inserted": total_added,
        "updated": updated_count,
        "unchanged": unchanged_count,
        "semantic_skipped": semantic_skips,
        "excluded": excluded_count,
        "plan_linkage": linkage_stats,
    }
    if return_stats:
        return total_added, new_items, stats
    return total_added, new_items


# ----------------------------------------------------------
# DASHBOARD SNAPSHOT HELPERS
# ----------------------------------------------------------
def _load_existing_tenders(json_path):
    """Load previously saved tenders so that dashboard keeps historical data."""
    if os.path.exists(json_path):
        try:
            with open(json_path, "r") as jf:
                data = json.load(jf)
                if isinstance(data, dict) and "tenders" in data:
                    return data["tenders"]
                return data if isinstance(data, list) else []
        except Exception as exc:
            log_error(LOG_FILE, f"Failed to read existing tenders snapshot: {exc}")
    return []


def _tender_identity(tender):
    """Return a stable identifier for merging tender lists."""
    ref = (tender.get("ref") or "").strip().lower()
    if ref:
        return f"ref::{ref}"
    title = (tender.get("title") or "").strip().lower()
    if title:
        return f"title::{title}"
    source = (tender.get("source") or "unknown").lower()
    closing = (tender.get("closing_date") or "").lower()
    try:
        serialized = json.dumps(tender, sort_keys=True, default=str)
    except Exception:
        serialized = (
            f"{source}-{closing}-{tender.get('scores', {}).get('composite', 'na')}"
        )
    return f"fallback::{serialized}"


def _merge_tenders(new_items, existing_items, limit=MAX_DASHBOARD_TENDERS):
    """Merge tenders while keeping ordering (newest first) and removing duplicates."""
    merged = []
    seen = set()

    for tender in new_items + existing_items:
        identity = _tender_identity(tender)
        if identity in seen:
            continue
        merged.append(tender)
        seen.add(identity)
        if len(merged) >= limit:
            break

    return merged


# ----------------------------------------------------------
# SAVE OUTPUT REPORTS
# ----------------------------------------------------------
def save_outputs(new_items, *, validation_report_text=""):
    # Save JSON
    json_path = os.path.join(OUTPUT_DIR, "new_tenders.json")
    existing_items = _load_existing_tenders(json_path)

    if new_items:
        merged_items = _merge_tenders(new_items, existing_items)

        meta = {
            "last_sync": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "next_run": "Daily 08:00",
        }

        output_payload = {"meta": meta, "tenders": merged_items}

        with open(json_path, "w") as jf:
            json.dump(output_payload, jf, indent=4)

        write_log(
            LOG_FILE,
            f"Dashboard snapshot updated: {len(new_items)} new / {len(merged_items)} retained",
        )
    else:
        if existing_items:
            write_log(LOG_FILE, "No new tenders - keeping previous dashboard snapshot")
        else:
            with open(json_path, "w") as jf:
                json.dump([], jf, indent=4)
            write_log(
                LOG_FILE, "No new tenders and no history - snapshot initialised empty"
            )
        merged_items = existing_items

    # Save text summary
    summary_path = os.path.join(OUTPUT_DIR, "summary.txt")
    with open(summary_path, "w") as sf:
        sf.write(f"Tender Scan Summary\n")
        sf.write(f"===================\n")
        sf.write(f"Run date: {datetime.now()}\n")
        sf.write(f"New tenders added: {len(new_items)}\n")
        if not new_items and merged_items:
            sf.write(
                "No new tenders detected — dashboard is showing the previous snapshot.\n"
            )
        sf.write("\n")

        # Group by priority
        high_priority = [
            t for t in new_items if t.get("scores", {}).get("priority") == "HIGH"
        ]
        medium_priority = [
            t for t in new_items if t.get("scores", {}).get("priority") == "MEDIUM"
        ]
        low_priority = [
            t for t in new_items if t.get("scores", {}).get("priority") == "LOW"
        ]

        sf.write(f"\n🔥 HIGH PRIORITY ({len(high_priority)}):\n")
        sf.write("-" * 40 + "\n")
        for t in high_priority:
            comp = t.get("scores", {}).get("composite") or t.get("scores", {}).get(
                "composite_score", "na"
            )
            sf.write(f"  [{comp}] {t['ref']} | {t['title'][:50]}...\n")

        sf.write(f"\n✅ MEDIUM PRIORITY ({len(medium_priority)}):\n")
        sf.write("-" * 40 + "\n")
        for t in medium_priority:
            comp = t.get("scores", {}).get("composite") or t.get("scores", {}).get(
                "composite_score", "na"
            )
            sf.write(f"  [{comp}] {t['ref']} | {t['title'][:50]}...\n")

        sf.write(f"\n📝 LOW PRIORITY ({len(low_priority)}):\n")
        sf.write("-" * 40 + "\n")
        for t in low_priority:
            comp = t.get("scores", {}).get("composite") or t.get("scores", {}).get(
                "composite_score", "na"
            )
            sf.write(f"  [{comp}] {t['ref']} | {t['title'][:50]}...\n")

        # Group by source
        sf.write(f"\n\nBY SOURCE:\n")
        sf.write("=" * 40 + "\n")
        by_source = {}
        for t in new_items:
            src = t.get("source", "Unknown")
            if src not in by_source:
                by_source[src] = []
            by_source[src].append(t)

        for source, items in by_source.items():
            sf.write(f"\n{source} ({len(items)}):\n")
            for t in items:
                sf.write(f"  - {t['ref']} | {t['title'][:50]}... | {t['category']}\n")

        if validation_report_text:
            sf.write(validation_report_text)


# ----------------------------------------------------------
# MAIN ENTRY POINT
# ----------------------------------------------------------
if __name__ == "__main__":
    # Validate environment and configuration on startup
    try:
        validate_env_on_startup()
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)

    rotate_log_if_needed(LOG_FILE)

    write_log(LOG_FILE, "=" * 50)
    write_log(
        LOG_FILE, "TENDER ENGINE RUN STARTED (WITH SCORING & PHASE 1 INTELLIGENCE)"
    )
    write_log(LOG_FILE, "=" * 50)

    # Scrape all sources (with monitoring)
    monitor = ScraperMonitor(output_dir=OUTPUT_DIR, db_path=DB_PATH)
    all_tenders = run_all_scrapers(monitor)

    # Save scraper health report
    try:
        monitor.generate_report(
            output_path=os.path.join(OUTPUT_DIR, "scraper_health.json")
        )
    except Exception as exc:
        log_error(LOG_FILE, f"Failed to write scraper health report: {exc}")

    write_log(LOG_FILE, f"Total tenders scraped: {len(all_tenders)}")

    # Alert on repeated failures (3 consecutive failures) - Phase 1: Multi-channel alerts
    if MULTI_CHANNEL_ALERTS_AVAILABLE and CONFIG.get("alerts", {}).get(
        "scraper_failures", {}
    ).get("enabled", False):
        try:
            should_alert, failing = monitor.should_alert_on_failures(threshold=3)
            if should_alert:
                # Send via configured channels
                alert_config = CONFIG.get("alerts", {})
                sent_count = 0

                # Slack alerts for scraper failures
                if alert_config.get("slack", {}).get("enabled", False):
                    webhook_url = alert_config["slack"].get("webhook_url")
                    if webhook_url:
                        try:
                            send_slack_alert(
                                {
                                    "title": "Scraper Failure Alert",
                                    "priority": "HIGH",
                                    "description": f"Repeated failures detected: {', '.join(failing)}",
                                },
                                webhook_url,
                            )
                            sent_count += 1
                        except Exception as e:
                            log_error(
                                LOG_FILE, f"Slack scraper failure alert failed: {e}"
                            )

                # SMS alerts for scraper failures
                if alert_config.get("sms", {}).get("enabled", False):
                    from_number = alert_config["sms"].get("from_number")
                    recipients = (
                        alert_config["sms"].get("recipients", {}).get("urgent", [])
                    )
                    if from_number and recipients:
                        try:
                            send_sms_alert(
                                {
                                    "title": "Scraper Failure Alert",
                                    "priority": "HIGH",
                                    "description": f"Repeated failures detected: {', '.join(failing)}",
                                },
                                recipients,
                            )
                            sent_count += 1
                        except Exception as e:
                            log_error(
                                LOG_FILE, f"SMS scraper failure alert failed: {e}"
                            )

                if sent_count > 0:
                    write_log(
                        LOG_FILE,
                        f"📧 Scraper failure alert sent for {len(failing)} source(s)",
                    )
                    monitor.mark_alerted(failing, threshold=3)
        except Exception as exc:
            log_error(LOG_FILE, f"Failed to send scraper failure alert: {exc}")

    validation = validate_tender_batch(
        all_tenders,
        on_invalid=lambda message: log_error(LOG_FILE, message),
    )
    write_log(
        LOG_FILE,
        f"Validation complete: {validation.valid_count} valid / {validation.invalid_count} invalid",
    )

    # Process, classify & SCORE
    added_count, new_items, upsert_stats = process_tenders(
        validation.valid_tenders, return_stats=True
    )
    write_log(
        LOG_FILE,
        f"Persistence complete: {upsert_stats['inserted']} inserted / "
        f"{upsert_stats['updated']} updated / {upsert_stats['unchanged']} unchanged",
    )

    # Phase 1: Semantic Deduplication
    if SEMANTIC_DEDUP_AVAILABLE and new_items:
        try:
            original_count = len(new_items)
            new_items, duplicates = filter_duplicates(new_items)
            filtered_count = len(new_items)
            duplicates_found = original_count - filtered_count
            if duplicates_found > 0:
                write_log(
                    LOG_FILE,
                    f"[DEDUP] Removed {duplicates_found} semantic duplicate(s)",
                )
        except Exception as e:
            log_error(LOG_FILE, f"Semantic deduplication failed: {e}")

    # Save results
    save_outputs(new_items, validation_report_text=validation.report_text)

    # Phase 1: Multi-Channel Alerts for urgent tenders (if enabled)
    if MULTI_CHANNEL_ALERTS_AVAILABLE and new_items:
        try:
            # Calculate days until closing for each tender
            urgent_threshold = CONFIG.get("alerts", {}).get("urgent_threshold_days", 3)
            urgent_tenders = []

            for tender in new_items:
                # Check if HIGH priority
                priority = (
                    tender.get("scores", {}).get("priority")
                    or tender.get("priority")
                    or ""
                ).upper()
                if priority != "HIGH":
                    continue

                # Check closing date
                closing_date = tender.get("closing_date")
                if not closing_date:
                    continue

                try:
                    closing_dt = datetime.fromisoformat(
                        closing_date.replace("Z", "+00:00")
                    )
                    today = datetime.now(closing_dt.tzinfo).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    closing_day = closing_dt.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    days_until = int((closing_day - today).days)

                    if 0 <= days_until <= urgent_threshold:
                        urgent_tenders.append(tender)
                except (ValueError, AttributeError):
                    continue

            # Send multi-channel alerts if there are urgent tenders
            if urgent_tenders:
                alert_config = CONFIG.get("alerts", {})
                sent_count = 0

                # Slack alerts
                if alert_config.get("slack", {}).get("enabled", False):
                    webhook_url = alert_config["slack"].get("webhook_url")
                    if webhook_url:
                        for tender in urgent_tenders:
                            try:
                                send_slack_alert(tender, webhook_url)
                                sent_count += 1
                            except Exception as e:
                                log_error(
                                    LOG_FILE,
                                    f"Slack alert failed for {tender.get('ref')}: {e}",
                                )

                # SMS alerts
                if alert_config.get("sms", {}).get("enabled", False):
                    from_number = alert_config["sms"].get("from_number")
                    recipients = (
                        alert_config["sms"].get("recipients", {}).get("urgent", [])
                    )
                    if from_number and recipients:
                        for tender in urgent_tenders:
                            try:
                                send_sms_alert(tender, recipients)
                                sent_count += 1
                            except Exception as e:
                                log_error(
                                    LOG_FILE,
                                    f"SMS alert failed for {tender.get('ref')}: {e}",
                                )

                # Smart alerts (auto-select best channel)
                if alert_config.get("smart_alerts", {}).get("enabled", False):
                    for tender in urgent_tenders:
                        try:
                            smart_alert(tender, alert_config)
                            sent_count += 1
                        except Exception as e:
                            log_error(
                                LOG_FILE,
                                f"Smart alert failed for {tender.get('ref')}: {e}",
                            )

                if sent_count > 0:
                    write_log(
                        LOG_FILE,
                        f"📧 Multi-channel alert sent for {sent_count} urgent tender(s)",
                    )
                else:
                    write_log(
                        LOG_FILE,
                        "📧 No urgent tenders requiring alerts or alerts not configured",
                    )
            else:
                write_log(LOG_FILE, "📧 No urgent tenders requiring alerts")

        except Exception as e:
            write_log(LOG_FILE, f"⚠️ Multi-channel alert failed: {e}")
            print(f"⚠️ Multi-channel alert failed: {e}")

    write_log(LOG_FILE, "=" * 50)
    write_log(LOG_FILE, f"TENDER ENGINE COMPLETE - Added: {added_count}")
    write_log(LOG_FILE, "=" * 50)

    # Print summary by priority
    high = sum(1 for t in new_items if t.get("scores", {}).get("priority") == "HIGH")
    medium = sum(
        1 for t in new_items if t.get("scores", {}).get("priority") == "MEDIUM"
    )
    low = sum(1 for t in new_items if t.get("scores", {}).get("priority") == "LOW")

    print(f"\n🎉 Tender scan complete!")
    print(f"   Total scraped: {len(all_tenders)}")
    print(f"   New tenders added: {added_count}")
    print(f"\n📊 SCORING SUMMARY:")
    print(f"   🔥 HIGH Priority:   {high}")
    print(f"   ✅ MEDIUM Priority: {medium}")
    print(f"   📝 LOW Priority:    {low}")
    print(f"\nCheck output at: {OUTPUT_DIR}")
