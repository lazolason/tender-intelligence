#!/usr/bin/env python3
# ==========================================================
# DAILY TENDER RUNNER v2.0
# Runs daily scan, generates report, syncs to Vercel, sends alerts
# ==========================================================

import os
import sys
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_daily():
    """Run complete daily tender workflow"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "scan": None,
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
        
        LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "scraper.log")
        rotate_log_if_needed(LOG_FILE)
        
        # Scrape all sources
        all_tenders = run_all_scrapers()
        print(f"   Scraped: {len(all_tenders)} tenders")
        
        # Process and score
        added_count, new_items = process_tenders(all_tenders)
        print(f"   New tenders added: {added_count}")
        
        # Save outputs
        save_outputs(new_items)
        
        results["scan"] = {
            "status": "success",
            "total_scraped": len(all_tenders),
            "new_added": added_count,
            "high_priority": sum(1 for t in new_items if t.get("scores", {}).get("priority") == "HIGH"),
            "medium_priority": sum(1 for t in new_items if t.get("scores", {}).get("priority") == "MEDIUM"),
            "low_priority": sum(1 for t in new_items if t.get("scores", {}).get("priority") == "LOW")
        }
        print(f"   ✅ Scan complete!")
        
    except Exception as e:
        results["scan"] = {"status": "error", "message": str(e)}
        print(f"   ❌ Scan failed: {e}")
    
    # Step 2: Sync to Vercel
    print("\n🔄 Step 2: Syncing to Vercel...")
    try:
        from sync_to_vercel import sync
        sync_success = sync()
        results["sync"] = {"status": "success" if sync_success else "failed"}
        if sync_success:
            print(f"   ✅ Vercel dashboard updated!")
        else:
            print(f"   ⚠️ Vercel sync had issues")
    except Exception as e:
        results["sync"] = {"status": "error", "message": str(e)}
        print(f"   ⚠️ Vercel sync skipped: {e}")
    
    # Step 3: Send email alerts for HIGH priority tenders
    print("\n📧 Step 3: Sending email alerts...")
    try:
        from utils.email_alerts import send_daily_digest, EMAIL_CONFIG

        # Check if email is configured
        if EMAIL_CONFIG["sender_email"] == "your-email@gmail.com":
            print("   ⚠️ Email not configured - skipping alerts")
            print("   💡 Edit utils/email_alerts.py to enable email alerts")
            results["email"] = {"status": "not_configured"}
        else:
            success = send_daily_digest()
            if success:
                print(f"   ✅ Email digest sent!")
                results["email"] = {"status": "sent"}
            else:
                print(f"   ⚠️ No HIGH priority tenders to alert")
                results["email"] = {"status": "no_alerts_needed"}
    except Exception as e:
        results["email"] = {"status": "error", "message": str(e)}
        print(f"   ⚠️ Email alerts skipped: {e}")
    
    # Step 4: Generate email summary (HTML backup)
    print("\n📄 Step 4: Generating HTML summary...")
    try:
        summary = generate_email_summary(results)
        print(f"   ✅ Summary saved to output/daily_email.html")
    except Exception as e:
        print(f"   ⚠️ Summary generation failed: {e}")
    
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
   
   🌐 View Dashboard: https://tender-intelligence-dashboard.vercel.app/
""")
    
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
            <a href="https://tender-intelligence-dashboard.vercel.app/" 
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
    email_path = os.path.join(os.path.dirname(__file__), "output", "daily_email.html")
    os.makedirs(os.path.dirname(email_path), exist_ok=True)
    with open(email_path, "w") as f:
        f.write(html)
    
    return html

if __name__ == "__main__":
    run_daily()
