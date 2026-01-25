# ==========================================================
# TENDER AUTOMATION ENGINE — MAIN RUNNER
# Scrapes all sources, classifies, SCORES, logs to Excel, creates folders
# ==========================================================

import json
import yaml
from datetime import datetime
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Import scrapers
from scrapers.municipalities import scrape_all_municipalities
from scrapers.soes import scrape_all_soes
# NOTE: Umgeni, Eskom, SANRAL, Transnet scrapers disabled - etenders.gov.za API returns 405
# from scrapers.eskom import scrape_eskom
# from scrapers.sanral import scrape_sanral
# from scrapers.transnet import scrape_transnet
# from scrapers.sadc import scrape_all_sadc
from scrapers.water_boards import scrape_all_water_boards

# Import utils
from utils.db_writer import DatabaseWriter
from utils.folder_tools import create_tender_folder
from utils.logging_tools import write_log, log_error, rotate_log_if_needed
from utils.data_validator import TenderValidator, format_validation_report
from utils.scraper_monitor import ScraperMonitor
from utils.config_validator import validate_env_on_startup

# Import scoring engine
from scoring_engine import score_tender

# ----------------------------------------------------------
# LOAD CONFIG
# ----------------------------------------------------------
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
with open(config_path, "r") as f:
    CONFIG = yaml.safe_load(f)

# Paths
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tenders.db"))
ACTIVE_TENDERS_DIR = CONFIG["paths"]["active_tenders"]
OUTPUT_DIR = CONFIG["paths"]["output_dir"]
LOG_FILE = CONFIG["paths"]["log_file"]
SHEET_NAME = CONFIG["excel"]["tender_log_sheet"]

# Selenium scraper toggle (set to True to enable)
ENABLE_SELENIUM = CONFIG.get("scrapers", {}).get("enable_selenium", True)

# Dashboard retains the last N tenders to avoid an empty UI when no new items are added
MAX_DASHBOARD_TENDERS = 200

# Deduplication Settings
DEDUPE_CONFIG = CONFIG.get("deduplication", {
    "semantic_threshold": 0.75,
    "fuzzy_threshold": 85,
    "date_window_days": 7,
    "require_same_source": False,
    "limit_db_check": 200
})

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
    log_error(LOG_FILE, "PDF analyzer not available - install with: pip install pdfplumber PyPDF2")

try:
    from utils.semantic_duplicate_detector import filter_duplicates, find_semantic_duplicate
    SEMANTIC_DEDUP_AVAILABLE = True
except ImportError:
    SEMANTIC_DEDUP_AVAILABLE = False
    log_error(LOG_FILE, "Semantic deduplication not available - install with: pip install sentence-transformers torch scikit-learn")

try:
    from utils.bid_tracker import record_bid_outcome, get_win_rates, get_client_performance
    BID_TRACKER_AVAILABLE = True
except ImportError:
    BID_TRACKER_AVAILABLE = False
    log_error(LOG_FILE, "Bid tracker not available - install with: pip install")

try:
    from utils.multi_channel_alerts import send_slack_alert, send_sms_alert, smart_alert
    MULTI_CHANNEL_ALERTS_AVAILABLE = True
except ImportError:
    MULTI_CHANNEL_ALERTS_AVAILABLE = False
    log_error(LOG_FILE, "Multi-channel alerts not available - install with: pip install slack-sdk twilio")

# ----------------------------------------------------------
# INITIALISE DATABASE WRITER
# ----------------------------------------------------------
db_writer = DatabaseWriter(DB_PATH, log_file_path=LOG_FILE)

# ----------------------------------------------------------
# RUN ALL SCRAPERS (PARALLEL)
# ----------------------------------------------------------
def run_all_scrapers(monitor: ScraperMonitor = None, max_workers: int = 5, timeout: int = 300):
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
    monitor = monitor or ScraperMonitor(output_dir=OUTPUT_DIR)
    
    # Define scraper tasks as (name, function) tuples
    scraper_tasks = [
        ("Municipalities", lambda: scrape_all_municipalities()),
        ("SOEs", lambda: scrape_all_soes()),
        ("Water Boards", lambda: scrape_all_water_boards()),
    ]
    
    # Add Selenium-based scrapers if enabled
    if ENABLE_SELENIUM:
        scraper_tasks.extend([
            ("National Treasury", lambda: __import__('scrapers.national_treasury_selenium', fromlist=['scrape_national_treasury']).scrape_national_treasury()),
            ("Johannesburg Water", lambda: __import__('scrapers.joburg_water_selenium', fromlist=['scrape_joburg_water_selenium']).scrape_joburg_water_selenium()),
            ("Eskom Tender Bulletin", lambda: __import__('scrapers.eskom_direct', fromlist=['scrape_eskom_tenders']).scrape_eskom_tenders()),
        ])
    
    def run_scraper(name: str, scraper_func):
        """Worker function to run a single scraper with monitoring."""
        from utils.scraper_monitor import CircuitOpenError
        try:
            with monitor.track(name) as run:
                write_log(LOG_FILE, f"=== Scraping {name} ===")
                tenders = scraper_func()
                run.tenders_found = len(tenders)
            write_log(LOG_FILE, f"{name}: {len(tenders)} tenders found")
            return name, tenders, None
        except CircuitOpenError:
            msg = f"Skipping {name} (Circuit Open)"
            write_log(LOG_FILE, msg, "INFO")
            return name, [], msg
        except ImportError as e:
            error_msg = f"Import failed for {name}: {e}"
            log_error(LOG_FILE, error_msg)
            return name, [], error_msg
        except Exception as e:
            error_msg = f"{name} scraper failed: {e}"
            log_error(LOG_FILE, error_msg)
            return name, [], error_msg
    
    write_log(LOG_FILE, f"🚀 Starting parallel scraping with {max_workers} workers...")
    
    # Execute scrapers in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_scraper = {
            executor.submit(run_scraper, name, func): name 
            for name, func in scraper_tasks
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
                    log_error(LOG_FILE, f"Unexpected error processing {scraper_name}: {e}")
                    failed_sources.append(scraper_name)
        except TimeoutError:
            write_log(LOG_FILE, f"⚠️  Global scraping timeout ({timeout}s) reached", "WARNING")
            # Cancel remaining futures
            for future in future_to_scraper:
                future.cancel()
    
    if failed_sources:
        write_log(LOG_FILE, f"Failed sources this run: {', '.join(sorted(set(failed_sources)))}", "WARNING")
    
    # NEW: Cross-Source Semantic Deduplication
    if SEMANTIC_DEDUP_AVAILABLE and all_tenders:
        before_count = len(all_tenders)
        all_tenders, duplicate_info = filter_duplicates(
            all_tenders,
            semantic_threshold=DEDUPE_CONFIG["semantic_threshold"],
            fuzzy_threshold=DEDUPE_CONFIG["fuzzy_threshold"],
            date_window_days=DEDUPE_CONFIG["date_window_days"],
            require_same_source=DEDUPE_CONFIG["require_same_source"]
        )
        if len(all_tenders) < before_count:
            write_log(LOG_FILE, f"✂️  Removed {before_count - len(all_tenders)} semantic duplicates across sources")
    
    write_log(LOG_FILE, f"✅ Parallel scraping complete. Total tenders: {len(all_tenders)}")
    return all_tenders

# ----------------------------------------------------------
# PROCESS TENDERS WITH SCORING
# ----------------------------------------------------------
def process_tenders(tenders):
    total_added = 0
    new_items = []
    excluded_count = 0
    
    # Fetch recent tenders from DB for semantic comparison (avoid re-adding)
    recent_db_tenders = db_writer.get_recent_tenders(limit=DEDUPE_CONFIG.get("limit_db_check", 200))
    
    for t in tenders:
        try:
            ref = str(t.get("ref", "NA")).strip().upper()
            title = t.get("title", "")
            
            # 1. Exact Ref Check (DB Writer handles this, but we log it here)
            if ref != "NA" and ref in [str(rt.get("ref")).upper() for rt in recent_db_tenders]:
                write_log(LOG_FILE, f"[SKIP] {ref}: Already in database (exact ref)")
                continue

            # 2. Semantic Duplicate Check against Database
            if SEMANTIC_DEDUP_AVAILABLE:
                match = find_semantic_duplicate(
                    t,
                    recent_db_tenders,
                    semantic_threshold=DEDUPE_CONFIG["semantic_threshold"],
                    fuzzy_threshold=DEDUPE_CONFIG["fuzzy_threshold"],
                    date_window_days=DEDUPE_CONFIG["date_window_days"],
                    require_same_source=DEDUPE_CONFIG["require_same_source"]
                )
                if match and match.is_duplicate:
                    write_log(LOG_FILE, f"[SKIP] {ref}: Semantic duplicate of {match.existing_ref} ({match.reason})")
                    continue

            description = t.get("description", title)
            description = t.get("description", title)
            client = t.get("client", "")
            category = t.get("category", "Unknown")
            closing_date = t.get("closing_date", "")
            short_title = t.get("short_title", "Tender")
            reason = t.get("reason", "")
            source = t.get("source", "")
            url = t.get("url", "")
            
            # SKIP EXCLUDED TENDERS (construction, security, etc.)
            if category == "EXCLUDED":
                write_log(LOG_FILE, f"[SKIP] {ref}: {reason}")
                excluded_count += 1
                continue
            
            tender_name = f"{ref} - {title}" if ref and ref != "NA" else title
            
            was_added, scores, classification = db_writer.add_tender_with_scoring(t)
            t["matched_keywords"] = classification.get("matched_keywords", [])
            
            if was_added:
                total_added += 1
                t["scores"] = scores
                new_items.append(t)
                
                # Phase 1: Enhanced PDF Analysis
                if PDF_ANALYZER_AVAILABLE and url and url.lower().endswith('.pdf'):
                    try:
                        t = add_pdf_analysis_to_tender(t)
                        # NEW: Save analysis to DB
                        if "pdf_analysis" in t:
                            # Re-map the flat fields back to the structure save_pdf_analysis expects
                            analysis_data = {
                                "page_count": t.get("pdf_analysis", {}).get("page_count"),
                                "word_count": t.get("pdf_analysis", {}).get("word_count"),
                                "requirements": t.get("pdf_requirements", []),
                                "deadlines": t.get("pdf_deadlines", []),
                                "values": t.get("pdf_values", []),
                                "contact": t.get("pdf_contact", {}),
                                "text": t.get("pdf_text", "") # Assuming we might want to store more text later
                            }
                            db_writer.save_pdf_analysis(ref, analysis_data)
                        
                        write_log(LOG_FILE, f"[PDF] Analyzed: {ref} - {len(t.get('pdf_requirements', []))} requirements found")
                    except Exception as e:
                        log_error(LOG_FILE, f"PDF analysis failed for {ref}: {e}")
    
                # Create tender folder
                folder_path = create_tender_folder(
                    base_dir=ACTIVE_TENDERS_DIR,
                    ref=ref,
                    client=client,
                    short_title=classification["short_title"]
                )

                write_log(LOG_FILE, f"[{scores['priority']}] Added: {t.get('title')} → {classification['category']} (Score: {scores['composite_score']})")
    
        except Exception as e:
            log_error(LOG_FILE, f"Error processing tender: {e}")
            continue

    if excluded_count > 0:
        write_log(LOG_FILE, f"Excluded {excluded_count} out-of-scope tenders (construction, security, etc.)")
    
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
        serialized = f"{source}-{closing}-{tender.get('scores', {}).get('composite', 'na')}"
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
def save_outputs(new_items):
    # Save JSON
    json_path = os.path.join(OUTPUT_DIR, "new_tenders.json")
    existing_items = _load_existing_tenders(json_path)

    if new_items:
        merged_items = _merge_tenders(new_items, existing_items)
        
        meta = {
            "last_sync": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "next_run": "Daily 08:00"
        }

        output_payload = {
            "meta": meta,
            "tenders": merged_items
        }

        with open(json_path, "w") as jf:
            json.dump(output_payload, jf, indent=4)
            
        write_log(
            LOG_FILE,
            f"Dashboard snapshot updated: {len(new_items)} new / {len(merged_items)} retained"
        )
    else:
        if existing_items:
            write_log(LOG_FILE, "No new tenders - keeping previous dashboard snapshot")
        else:
            with open(json_path, "w") as jf:
                json.dump([], jf, indent=4)
            write_log(LOG_FILE, "No new tenders and no history - snapshot initialised empty")
        merged_items = existing_items
    
    # Save text summary
    summary_path = os.path.join(OUTPUT_DIR, "summary.txt")
    with open(summary_path, "w") as sf:
        sf.write(f"Tender Scan Summary\n")
        sf.write(f"===================\n")
        sf.write(f"Run date: {datetime.now()}\n")
        sf.write(f"New tenders added: {len(new_items)}\n")
        if not new_items and merged_items:
            sf.write("No new tenders detected — dashboard is showing the previous snapshot.\n")
        sf.write("\n")
        
        # Group by priority
        high_priority = [t for t in new_items if t.get("scores", {}).get("priority") == "HIGH"]
        medium_priority = [t for t in new_items if t.get("scores", {}).get("priority") == "MEDIUM"]
        low_priority = [t for t in new_items if t.get("scores", {}).get("priority") == "LOW"]
        
        sf.write(f"\n🔥 HIGH PRIORITY ({len(high_priority)}):\n")
        sf.write("-" * 40 + "\n")
        for t in high_priority:
            comp = t.get("scores", {}).get("composite") or t.get("scores", {}).get("composite_score", "na")
            sf.write(f"  [{comp}] {t['ref']} | {t['title'][:50]}...\n")
        
        sf.write(f"\n✅ MEDIUM PRIORITY ({len(medium_priority)}):\n")
        sf.write("-" * 40 + "\n")
        for t in medium_priority:
            comp = t.get("scores", {}).get("composite") or t.get("scores", {}).get("composite_score", "na")
            sf.write(f"  [{comp}] {t['ref']} | {t['title'][:50]}...\n")
        
        sf.write(f"\n📝 LOW PRIORITY ({len(low_priority)}):\n")
        sf.write("-" * 40 + "\n")
        for t in low_priority:
            comp = t.get("scores", {}).get("composite") or t.get("scores", {}).get("composite_score", "na")
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

        # Validation report (if available)
        if isinstance(globals().get("VALIDATION_REPORT_TEXT"), str) and globals().get("VALIDATION_REPORT_TEXT"):
            sf.write(globals().get("VALIDATION_REPORT_TEXT"))

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
    write_log(LOG_FILE, "TENDER ENGINE RUN STARTED (WITH SCORING & PHASE 1 INTELLIGENCE)")
    write_log(LOG_FILE, "=" * 50)
    
    # Scrape all sources (with monitoring)
    monitor = ScraperMonitor(output_dir=OUTPUT_DIR)
    all_tenders = run_all_scrapers(monitor)

    # Save scraper health report
    try:
        monitor.generate_report(output_path=os.path.join(OUTPUT_DIR, "scraper_health.json"))
    except Exception as exc:
        log_error(LOG_FILE, f"Failed to write scraper health report: {exc}")
    
    write_log(LOG_FILE, f"Total tenders scraped: {len(all_tenders)}")

    # Alert on repeated failures (3 consecutive failures) - Phase 1: Multi-channel alerts
    if MULTI_CHANNEL_ALERTS_AVAILABLE and CONFIG.get("alerts", {}).get("scraper_failures", {}).get("enabled", False):
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
                            send_slack_alert({"title": "Scraper Failure Alert", "priority": "HIGH", "description": f"Repeated failures detected: {', '.join(failing)}"}, webhook_url)
                            sent_count += 1
                        except Exception as e:
                            log_error(LOG_FILE, f"Slack scraper failure alert failed: {e}")
                
                # SMS alerts for scraper failures
                if alert_config.get("sms", {}).get("enabled", False):
                    from_number = alert_config["sms"].get("from_number")
                    recipients = alert_config["sms"].get("recipients", {}).get("urgent", [])
                    if from_number and recipients:
                        try:
                            send_sms_alert({"title": "Scraper Failure Alert", "priority": "HIGH", "description": f"Repeated failures detected: {', '.join(failing)}"}, recipients)
                            sent_count += 1
                        except Exception as e:
                            log_error(LOG_FILE, f"SMS scraper failure alert failed: {e}")
                
                if sent_count > 0:
                    write_log(LOG_FILE, f"📧 Scraper failure alert sent for {len(failing)} source(s)")
                    monitor.mark_alerted(failing, threshold=3)
        except Exception as exc:
            log_error(LOG_FILE, f"Failed to send scraper failure alert: {exc}")
    
    # Validate scraped tenders before scoring/processing
    validator = TenderValidator()
    valid_tenders = []
    invalid_count = 0
    valid_count = 0
    error_counts = {}
    warning_counts = {}
    invalid_examples = []

    for tender in all_tenders:
        result = validator.validate_with_warnings(tender)
        if result.valid:
            valid_tenders.append(tender)
            valid_count += 1
        else:
            invalid_count += 1
            ref = tender.get("ref") or "NA"
            log_error(LOG_FILE, f"Invalid tender {ref}: {result.errors}")
            for msg in result.errors:
                error_counts[msg] = error_counts.get(msg, 0) + 1
            if len(invalid_examples) < 20:
                invalid_examples.append(f"{ref} ({tender.get('source','Unknown')}): {', '.join(result.errors)}")

        for msg in result.warnings:
            warning_counts[msg] = warning_counts.get(msg, 0) + 1

    VALIDATION_REPORT_TEXT = format_validation_report(
        total=len(all_tenders),
        valid_count=valid_count,
        invalid_count=invalid_count,
        error_counts=error_counts,
        warning_counts=warning_counts,
        invalid_examples=invalid_examples,
    )

    write_log(LOG_FILE, f"Validation complete: {valid_count} valid / {invalid_count} invalid")

    # Process, classify & SCORE
    added_count, new_items = process_tenders(valid_tenders)

    # Phase 1: Semantic Deduplication
    if SEMANTIC_DEDUP_AVAILABLE and new_items:
        try:
            original_count = len(new_items)
            new_items, duplicates = filter_duplicates(new_items)
            filtered_count = len(new_items)
            duplicates_found = original_count - filtered_count
            if duplicates_found > 0:
                write_log(LOG_FILE, f"[DEDUP] Removed {duplicates_found} semantic duplicate(s)")
        except Exception as e:
            log_error(LOG_FILE, f"Semantic deduplication failed: {e}")

    # Save results
    save_outputs(new_items)

    # Phase 1: Multi-Channel Alerts for urgent tenders (if enabled)
    if MULTI_CHANNEL_ALERTS_AVAILABLE and new_items:
        try:
            # Calculate days until closing for each tender
            urgent_threshold = CONFIG.get("alerts", {}).get("urgent_threshold_days", 3)
            urgent_tenders = []

            for tender in new_items:
                # Check if HIGH priority
                priority = (tender.get("scores", {}).get("priority") or tender.get("priority") or "").upper()
                if priority != "HIGH":
                    continue

                # Check closing date
                closing_date = tender.get("closing_date")
                if not closing_date:
                    continue

                try:
                    closing_dt = datetime.fromisoformat(closing_date.replace("Z", "+00:00"))
                    today = datetime.now(closing_dt.tzinfo).replace(hour=0, minute=0, second=0, microsecond=0)
                    closing_day = closing_dt.replace(hour=0, minute=0, second=0, microsecond=0)
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
                                log_error(LOG_FILE, f"Slack alert failed for {tender.get('ref')}: {e}")

                # SMS alerts
                if alert_config.get("sms", {}).get("enabled", False):
                    from_number = alert_config["sms"].get("from_number")
                    recipients = alert_config["sms"].get("recipients", {}).get("urgent", [])
                    if from_number and recipients:
                        for tender in urgent_tenders:
                            try:
                                send_sms_alert(tender, recipients)
                                sent_count += 1
                            except Exception as e:
                                log_error(LOG_FILE, f"SMS alert failed for {tender.get('ref')}: {e}")

                # Smart alerts (auto-select best channel)
                if alert_config.get("smart_alerts", {}).get("enabled", False):
                    for tender in urgent_tenders:
                        try:
                            smart_alert(tender, alert_config)
                            sent_count += 1
                        except Exception as e:
                            log_error(LOG_FILE, f"Smart alert failed for {tender.get('ref')}: {e}")

                if sent_count > 0:
                    write_log(LOG_FILE, f"📧 Multi-channel alert sent for {sent_count} urgent tender(s)")
                else:
                    write_log(LOG_FILE, "📧 No urgent tenders requiring alerts or alerts not configured")
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
    medium = sum(1 for t in new_items if t.get("scores", {}).get("priority") == "MEDIUM")
    low = sum(1 for t in new_items if t.get("scores", {}).get("priority") == "LOW")

    print(f"\n🎉 Tender scan complete!")
    print(f"   Total scraped: {len(all_tenders)}")
    print(f"   New tenders added: {added_count}")
    print(f"\n📊 SCORING SUMMARY:")
    print(f"   🔥 HIGH Priority:   {high}")
    print(f"   ✅ MEDIUM Priority: {medium}")
    print(f"   📝 LOW Priority:    {low}")
    print(f"\nCheck output at: {OUTPUT_DIR}")
