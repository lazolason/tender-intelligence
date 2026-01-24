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

# Import scoring engine
from scoring_engine import score_tender

# ----------------------------------------------------------
# LOAD CONFIG
# ----------------------------------------------------------
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
with open(config_path, "r") as f:
    CONFIG = yaml.safe_load(f)

# Paths
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tenders.db")
ACTIVE_TENDERS_DIR = CONFIG["paths"]["active_tenders"]
OUTPUT_DIR = CONFIG["paths"]["output_dir"]
LOG_FILE = CONFIG["paths"]["log_file"]
SHEET_NAME = CONFIG["excel"]["tender_log_sheet"]

# Selenium scraper toggle (set to True to enable)
ENABLE_SELENIUM = CONFIG.get("scrapers", {}).get("enable_selenium", True)

# Dashboard retains the last N tenders to avoid an empty UI when no new items are added
MAX_DASHBOARD_TENDERS = 200

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
    from utils.semantic_duplicate_detector import filter_duplicates
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
# RUN ALL SCRAPERS
# ----------------------------------------------------------
def run_all_scrapers(monitor: ScraperMonitor = None):
    all_tenders = []
    failed_sources = []
    monitor = monitor or ScraperMonitor(output_dir=OUTPUT_DIR)
    
    # Municipalities
    write_log(LOG_FILE, "=== Scraping Municipalities ===")
    try:
        with monitor.track("Municipalities") as run:
            muni_tenders = scrape_all_municipalities()
            run.tenders_found = len(muni_tenders)
        all_tenders.extend(muni_tenders)
        write_log(LOG_FILE, f"Municipalities: {len(muni_tenders)} tenders found")
    except Exception as e:
        log_error(LOG_FILE, f"Municipality scraper failed: {e}")
        failed_sources.append("Municipalities")
    
    # SOEs
    write_log(LOG_FILE, "=== Scraping SOEs ===")
    try:
        with monitor.track("SOEs") as run:
            soe_tenders = scrape_all_soes()
            run.tenders_found = len(soe_tenders)
        all_tenders.extend(soe_tenders)
        write_log(LOG_FILE, f"SOEs: {len(soe_tenders)} tenders found")
    except Exception as e:
        log_error(LOG_FILE, f"SOE scraper failed: {e}")
        failed_sources.append("SOEs")
    
    # National Treasury (Selenium) - Optional
    if ENABLE_SELENIUM:
        write_log(LOG_FILE, "=== Scraping National Treasury (Selenium) ===")
        try:
            with monitor.track("National Treasury") as run:
                from scrapers.national_treasury_selenium import scrape_national_treasury
                nt_tenders = scrape_national_treasury()
                run.tenders_found = len(nt_tenders)
            all_tenders.extend(nt_tenders)
            write_log(LOG_FILE, f"National Treasury: {len(nt_tenders)} tenders found")
        except ImportError:
            log_error(LOG_FILE, "Selenium not available - skipping National Treasury")
            failed_sources.append("National Treasury (Selenium import)")
        except Exception as e:
            log_error(LOG_FILE, f"National Treasury scraper failed: {e}")
            failed_sources.append("National Treasury")
    
    # Johannesburg Water (Selenium) - Optional
    if ENABLE_SELENIUM:
        write_log(LOG_FILE, "=== Scraping Johannesburg Water (Selenium) ===")
        try:
            with monitor.track("Johannesburg Water") as run:
                from scrapers.joburg_water_selenium import scrape_joburg_water_selenium
                jw_tenders = scrape_joburg_water_selenium()
                run.tenders_found = len(jw_tenders)
            all_tenders.extend(jw_tenders)
            write_log(LOG_FILE, f"Johannesburg Water: {len(jw_tenders)} tenders found")
        except Exception as e:
            log_error(LOG_FILE, f"Johannesburg Water scraper failed: {e}")
            failed_sources.append("Johannesburg Water")
    
    # NOTE: Disabled non-functional scrapers (405 errors on etenders.gov.za API)
    # TODO: Research correct etenders.gov.za API endpoints for:
    # - Eskom
    # - SANRAL
    # - Transnet
    
    # Eskom (Direct Tender Bulletin)
    if ENABLE_SELENIUM:
        write_log(LOG_FILE, "=== Scraping Eskom Tender Bulletin ===")
        try:
            with monitor.track("Eskom Tender Bulletin") as run:
                from scrapers.eskom_direct import scrape_eskom_tenders
                eskom_tenders = scrape_eskom_tenders()
                run.tenders_found = len(eskom_tenders)
            all_tenders.extend(eskom_tenders)
            write_log(LOG_FILE, f"Eskom: {len(eskom_tenders)} tenders found")
        except Exception as e:
            log_error(LOG_FILE, f"Eskom tender bulletin scraper failed: {e}")
            failed_sources.append("Eskom Tender Bulletin")

    # Water Boards (Umgeni, Magalies, Lepelle)
    write_log(LOG_FILE, "=== Scraping Water Boards ===")
    try:
        with monitor.track("Water Boards") as run:
            wb_tenders = scrape_all_water_boards()
            run.tenders_found = len(wb_tenders)
        all_tenders.extend(wb_tenders)
        write_log(LOG_FILE, f"Water Boards: {len(wb_tenders)} tenders found")
    except Exception as e:
        log_error(LOG_FILE, f"Water Board scraper failed: {e}")
        failed_sources.append("Water Boards")

    # SADC Region (Botswana, Namibia)
    # write_log(LOG_FILE, "=== Scraping SADC Region ===")
    # try:
    #     with monitor.track("SADC Region") as run:
    #         sadc_tenders = scrape_all_sadc()
    #         run.tenders_found = len(sadc_tenders)
    #     all_tenders.extend(sadc_tenders)
    #     write_log(LOG_FILE, f"SADC Region: {len(sadc_tenders)} tenders found")
    # except Exception as e:
    #     log_error(LOG_FILE, f"SADC Region scraper failed: {e}")
    #     failed_sources.append("SADC Region")
    
    if failed_sources:
        write_log(LOG_FILE, f"Failed sources this run: {', '.join(sorted(set(failed_sources)))}", "WARNING")

    return all_tenders

# ----------------------------------------------------------
# PROCESS TENDERS WITH SCORING
# ----------------------------------------------------------
def process_tenders(tenders):
    total_added = 0
    new_items = []
    excluded_count = 0
    
    for t in tenders:
        try:
            ref = t.get("ref", "NA")
            title = t.get("title", "")
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
                        write_log(LOG_FILE, f"[PDF] Analyzed: {ref} - {len(t.get('pdf_analysis', {}).get('requirements', []))} requirements found")
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
