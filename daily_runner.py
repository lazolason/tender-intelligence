#!/usr/bin/env python3
# ==========================================================
# DAILY TENDER RUNNER v2.0
# Runs daily scan, generates report, syncs local dashboard, sends alerts
# ==========================================================

import os
import sys
import json
import tempfile
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from utils.config_validator import validate_env_on_startup
from utils.pipeline_validation import validate_tender_batch
from utils.scraper_monitor import summarize_scraper_health_status
from utils.run_status import daily_run_outcome

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_DIR, ".env"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR") or os.path.join(PROJECT_DIR, "output")
DAILY_RUN_STATUS_PATH = os.path.join(OUTPUT_DIR, "last_daily_run.json")
DASHBOARD_URL = (os.getenv("DASHBOARD_URL") or "http://localhost:5001/").strip() or "http://localhost:5001/"


def persist_run_results(results, path: str | None = None):
    """Persist the latest daily runner result for health checks and debugging."""
    path = path or DAILY_RUN_STATUS_PATH
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete=False) as file_obj:
            temporary_path = file_obj.name
            json.dump(results, file_obj, indent=2)
            file_obj.flush()
            os.fsync(file_obj.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)
    return path


def run_daily():
    """Run complete daily tender workflow"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "scan": None,
        "procurement_plans": None,
        "sync": None,
        "email": None
    }
    
    print("=" * 60)
    print("🚀 DAILY TENDER SCAN STARTED")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Step 1: Run tender scan
    print("\n📡 Step 1: Running tender scan...")
    try:
        from tenderscan import run_all_scrapers, process_tenders, save_outputs
        from utils.logging_tools import write_log, rotate_log_if_needed
        
        LOG_FILE = os.environ.get("LOG_FILE") or os.path.join(PROJECT_DIR, "logs", "scraper.log")
        DB_PATH = os.getenv(
            "DB_PATH",
            os.path.join(PROJECT_DIR, "data", "tenders.db"),
        )
        rotate_log_if_needed(LOG_FILE)
        
        # Scrape all sources
        from utils.scraper_monitor import ScraperMonitor
        monitor = ScraperMonitor(
            output_dir=OUTPUT_DIR,
            db_path=DB_PATH,
        )
        
        all_tenders = run_all_scrapers(monitor=monitor)
        print(f"   Scraped: {len(all_tenders)} tenders")
        monitor.generate_report()
        scraper_summary = summarize_scraper_health_status(monitor.get_metrics(), problem_threshold=3)
        if "National Treasury" in scraper_summary["latest_failed_sources"]:
            raise RuntimeError("Primary eTenders feed failed; scan coverage is incomplete")
        
        # Check for scraper failures and send alerts
        has_critical_failures, failures = monitor.should_alert_on_failures(threshold=3)
        if has_critical_failures:
            print(f"   🚨 {len(failures)} critical scraper failures detected!")
            from utils.multi_channel_alerts import AlertConfig, send_scraper_health_alert
            # Try to load config for real alerts if available
            try:
                # This is a bit of a hack since DailyRunner doesn't have a full config object yet
                # but we can initialize a default AlertConfig and let it try to find env vars
                alert_config = AlertConfig(
                    slack_webhook=os.getenv("SLACK_WEBHOOK_URL"),
                    enabled_channels=['slack'] if os.getenv("SLACK_WEBHOOK_URL") else []
                )
                for source, metrics in failures.items():
                    if send_scraper_health_alert(alert_config, source, metrics):
                        print(f"      ✅ Alert sent for {source}")
                monitor.mark_alerted(failures, threshold=3)
            except Exception as alert_exc:
                print(f"      ⚠️ Failed to send health alerts: {alert_exc}")

        validation = validate_tender_batch(
            all_tenders,
            on_invalid=lambda message: write_log(LOG_FILE, message, "ERROR"),
        )
        print(
            f"   Validated: {validation.valid_count} valid / "
            f"{validation.invalid_count} invalid"
        )

        # Process and score only records accepted by the canonical validator
        added_count, new_items, upsert_stats = process_tenders(
            validation.valid_tenders, return_stats=True
        )
        print(
            f"   Persistence: {upsert_stats['inserted']} inserted / "
            f"{upsert_stats['updated']} updated / "
            f"{upsert_stats['unchanged']} unchanged"
        )

        # Save outputs with the same validation audit used by the CLI runner
        save_outputs(new_items, validation_report_text=validation.report_text)
        
        results["scan"] = {
            "status": "success",
            "total_scraped": len(all_tenders),
            "new_added": added_count,
            "persistence": upsert_stats,
            "validation": validation.metrics(),
            "critical_failures": len(failures) if has_critical_failures else 0,
            "failed_sources_count": len(scraper_summary["latest_failed_sources"]),
            "failed_sources": scraper_summary["latest_failed_sources"],
            "high_priority": sum(1 for t in new_items if t.get("scores", {}).get("priority") == "HIGH"),
            "medium_priority": sum(1 for t in new_items if t.get("scores", {}).get("priority") == "MEDIUM"),
            "low_priority": sum(1 for t in new_items if t.get("scores", {}).get("priority") == "LOW")
        }
        print(f"   ✅ Scan complete!")
        
    except Exception as e:
        results["scan"] = {"status": "error", "message": str(e)}
        print(f"   ❌ Scan failed: {e}")
    
    # Step 2: Refresh Treasury procurement plans
    print("\n🗓️ Step 2: Refreshing Treasury procurement plans...")
    try:
        from sync_procurement_plans import sync_procurement_plans

        plan_result = sync_procurement_plans()
        results["procurement_plans"] = plan_result
        print(f"   ✅ Planned opportunities refreshed: {plan_result['persisted']}")
    except Exception as e:
        results["procurement_plans"] = {"status": "error", "message": str(e)}
        print(f"   ⚠️ Procurement plan refresh failed: {e}")

    # Step 3: Sync local dashboard
    print("\n🔄 Step 3: Syncing local dashboard...")
    try:
        from sync_dashboard import sync
        sync_success = sync()
        results["sync"] = {"status": "success" if sync_success else "failed"}
        if sync_success:
            print(f"   ✅ Local dashboard updated!")
        else:
            print(f"   ⚠️ Local dashboard sync had issues")
    except Exception as e:
        results["sync"] = {"status": "error", "message": str(e)}
        print(f"   ⚠️ Local dashboard sync skipped: {e}")
    
    # Step 4: Send email alerts for HIGH priority tenders
    print("\n📧 Step 4: Sending email alerts...")
    try:
        from utils.email_alerts import send_daily_digest, config_status

        # Check whether the digest can actually be sent. The previous test
        # compared sender_email to a literal placeholder, so a config that was
        # empty in any other way reached SMTP and failed with a confusing error
        # instead of skipping cleanly.
        status = config_status()
        if not results.get("scan") or results["scan"].get("status") != "success":
            results["email"] = {"status": "skipped", "reason": "scan_failed"}
            print("   ⚠️ Scan failed - refusing to send a stale digest")
        elif not results.get("sync") or results["sync"].get("status") != "success":
            results["email"] = {"status": "skipped", "reason": "sync_failed"}
            print("   ⚠️ Dashboard sync failed - refusing to send a stale digest")
        elif not status.get("enabled", True):
            results["email"] = {"status": "disabled"}
            print("   Email digest disabled in config.yaml - skipping alerts")
        elif not status["configured"]:
            print("   ⚠️ Email not configured - skipping alerts")
            for missing in status["missing"]:
                print(f"      missing: {missing}")
            results["email"] = {"status": "not_configured", "missing": status["missing"]}
        else:
            delivery = send_daily_digest(return_status=True)
            results["email"] = delivery
            if delivery["status"] == "sent":
                print(f"   ✅ Email digest sent!")
            elif delivery["status"] == "no_alerts_needed":
                print(f"   ⚠️ No HIGH priority tenders to alert")
            else:
                print("   ⚠️ Email digest delivery failed")
    except Exception as e:
        results["email"] = {"status": "error", "message": str(e)}
        print(f"   ⚠️ Email alerts skipped: {e}")
    
    # Step 5: Database Backup
    print("\n💾 Step 5: Backing up database...")
    try:
        from utils.backup_database import backup_database
        if backup_database():
            results["backup"] = {"status": "success"}
            print(f"   ✅ Database backed up successfully!")
        else:
            results["backup"] = {"status": "failed"}
            print(f"   ⚠️ Database backup failed")
    except Exception as e:
        results["backup"] = {"status": "error", "message": str(e)}
        print(f"   ⚠️ Backup generation failed: {e}")
    
    # Final summary
    print("\n" + "=" * 60)
    print("🎉 DAILY TENDER SCAN COMPLETE")
    print("=" * 60)
    
    if results["scan"] and results["scan"].get("status") == "success":
        scan = results["scan"]
        print(f"""
📊 RESULTS:
   Total Scraped:   {scan['total_scraped']}
   New Added:       {scan['new_added']}
   
   🔥 HIGH Priority:   {scan['high_priority']}
   ✅ MEDIUM Priority: {scan['medium_priority']}
   📝 LOW Priority:    {scan['low_priority']}
   
   Dashboard: {'✅' if results.get('sync', {}).get('status') == 'success' else '⚠️'}
   Email:     {'✅' if results.get('email', {}).get('status') == 'sent' else '⚠️'}
   
   🌐 View Dashboard: {DASHBOARD_URL}
""")
    
    results["status"] = daily_run_outcome(results)
    try:
        persist_run_results(results)
    except Exception as e:
        results["status"] = "error"
        results["status_persistence"] = {"status": "error", "message": str(e)}
        print(f"   ⚠️ Failed to persist daily run status: {e}")
    return results

def generate_email_summary(results):
    """Generate HTML email summary"""
    scan = results.get("scan", {})
    
    if scan.get("status") != "success":
        return f"<p>Scan failed: {scan.get('message', 'Unknown error')}</p>"
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Daily Tender Report</title>
</head>
<body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h1 style="color: #667eea; margin: 0 0 10px 0;">🎯 Daily Tender Report</h1>
        <p style="color: #888; margin: 0 0 20px 0;">{datetime.now().strftime('%A, %d %B %Y at %H:%M')}</p>
        
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 25px; border-radius: 12px; margin: 20px 0; color: white;">
            <h2 style="margin: 0 0 15px 0; font-size: 18px;">📊 Scan Summary</h2>
            <div style="display: flex; justify-content: space-between;">
                <div>
                    <div style="font-size: 32px; font-weight: bold;">{scan['total_scraped']}</div>
                    <div style="opacity: 0.8;">Total Scraped</div>
                </div>
                <div>
                    <div style="font-size: 32px; font-weight: bold;">{scan['new_added']}</div>
                    <div style="opacity: 0.8;">New Added</div>
                </div>
            </div>
        </div>
        
        <h3 style="color: #333; margin: 25px 0 15px 0;">Priority Breakdown</h3>
        <div style="display: flex; gap: 10px; margin: 20px 0;">
            <div style="flex: 1; background: linear-gradient(135deg, #ff6b6b, #ee5a5a); padding: 20px; border-radius: 12px; text-align: center; color: white;">
                <div style="font-size: 2.5rem; font-weight: bold;">{scan['high_priority']}</div>
                <div style="font-weight: 600;">🔥 HIGH</div>
            </div>
            <div style="flex: 1; background: linear-gradient(135deg, #ffc107, #e0a800); padding: 20px; border-radius: 12px; text-align: center; color: white;">
                <div style="font-size: 2.5rem; font-weight: bold;">{scan['medium_priority']}</div>
                <div style="font-weight: 600;">⚡ MEDIUM</div>
            </div>
            <div style="flex: 1; background: linear-gradient(135deg, #17a2b8, #138496); padding: 20px; border-radius: 12px; text-align: center; color: white;">
                <div style="font-size: 2.5rem; font-weight: bold;">{scan['low_priority']}</div>
                <div style="font-weight: 600;">📝 LOW</div>
            </div>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 12px; margin: 25px 0; text-align: center;">
            <p style="margin: 0 0 15px 0; color: #666;">View all tenders on your dashboard:</p>
            <a href="{DASHBOARD_URL}"
               style="display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2); 
                      color: white; padding: 12px 30px; border-radius: 25px; text-decoration: none;
                      font-weight: 600;">
                🌐 Open Dashboard
            </a>
        </div>
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
        
        <p style="color: #888; font-size: 12px; margin: 0; text-align: center;">
            Tender Intelligence System v2.0 | Mexel Energy Sustain<br>
            Dashboard: {'✅ Updated' if results.get('sync', {}).get('status') == 'success' else '⚠️ Pending'} | 
            Email: {'✅ Sent' if results.get('email', {}).get('status') == 'sent' else '⚠️ Not sent'}
        </p>
    </div>
</body>
</html>
    """
    
    # Save email HTML
    email_path = os.path.join(OUTPUT_DIR, "daily_email.html")
    os.makedirs(os.path.dirname(email_path), exist_ok=True)
    with open(email_path, "w") as f:
        f.write(html)
    
    return html

if __name__ == "__main__":
    # Load environment variables and validate configuration
    load_dotenv()
    try:
        validate_env_on_startup()
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        sys.exit(1)
        
    results = run_daily()
    sys.exit({"success": 0, "partial": 2}.get(results["status"], 1))
