#!/usr/bin/env python3
# ==========================================================
# EMAIL ALERTS FOR HIGH PRIORITY TENDERS
# Sends daily digest via email
# ==========================================================

import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Configuration - UPDATE THESE
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "",  # Your Gmail address
    "sender_password": "",  # App password (not regular password)
    "recipient_emails": []  # List of emails to receive alerts
}

AUTOMATION_DIR = os.path.dirname(os.path.abspath(__file__))
TENDERS_JSON = os.path.join(AUTOMATION_DIR, "output", "new_tenders.json")

def load_tenders():
    if os.path.exists(TENDERS_JSON):
        with open(TENDERS_JSON, "r") as f:
            return json.load(f)
    return []

def get_days_until_closing(closing_date):
    """Calculate days until closing"""
    if not closing_date:
        return None
    try:
        close = datetime.strptime(closing_date, "%Y-%m-%d")
        delta = (close - datetime.now()).days
        return delta
    except:
        return None

def get_urgency_text(days):
    """Get urgency label"""
    if days is None:
        return "📅 Date TBC"
    if days < 0:
        return "❌ CLOSED"
    if days == 0:
        return "🔴 CLOSES TODAY!"
    if days == 1:
        return "🔴 CLOSES TOMORROW!"
    if days <= 3:
        return f"🟠 {days} DAYS LEFT"
    if days <= 7:
        return f"🟡 {days} days left"
    return f"🟢 {days} days left"

def generate_email_html(tenders):
    """Generate HTML email content"""
    high_priority = [t for t in tenders if t.get("scores", {}).get("priority") == "HIGH"]
    medium_priority = [t for t in tenders if t.get("scores", {}).get("priority") == "MEDIUM"]
    
    # Sort by closing date
    for lst in [high_priority, medium_priority]:
        lst.sort(key=lambda x: x.get("closing_date", "9999-99-99"))
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 20px; }}
            h1 {{ color: #667eea; }}
            .tender {{ border-left: 4px solid #667eea; padding: 15px; margin: 15px 0; background: #f9f9f9; border-radius: 5px; }}
            .tender.high {{ border-left-color: #ff6b6b; }}
            .tender.medium {{ border-left-color: #feca57; }}
            .ref {{ font-weight: bold; color: #667eea; }}
            .title {{ color: #333; margin: 5px 0; }}
            .meta {{ color: #888; font-size: 12px; }}
            .urgency {{ display: inline-block; padding: 3px 10px; border-radius: 15px; font-size: 11px; font-weight: bold; }}
            .urgency.red {{ background: #ffe0e0; color: #ff6b6b; }}
            .urgency.orange {{ background: #fff3e0; color: #ff9800; }}
            .urgency.yellow {{ background: #fff9e6; color: #f9a825; }}
            .urgency.green {{ background: #e8f5e9; color: #4caf50; }}
            .company {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-left: 10px; }}
            .company.tes {{ background: #e3f2fd; color: #2196f3; }}
            .company.phakathi {{ background: #fff3e0; color: #ff9800; }}
            .footer {{ text-align: center; color: #888; font-size: 11px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Tender Intelligence Daily Digest</h1>
            <p style="color: #888;">{datetime.now().strftime("%A, %d %B %Y")}</p>
    """
    
    if high_priority:
        html += f"<h2 style='color: #ff6b6b;'>🔥 High Priority ({len(high_priority)})</h2>"
        for t in high_priority:
            days = get_days_until_closing(t.get("closing_date"))
            urgency = get_urgency_text(days)
            urgency_class = "red" if days is not None and days <= 3 else "orange" if days is not None and days <= 7 else "green"
            
            scores = t.get("scores", {})
            company = "TES" if scores.get("tes", 0) > scores.get("phakathi", 0) else "Phakathi" if scores.get("phakathi", 0) > scores.get("tes", 0) else "Both"
            company_class = "tes" if company == "TES" else "phakathi"
            
            html += f"""
            <div class="tender high">
                <span class="ref">{t.get('ref', 'N/A')}</span>
                <span class="company {company_class}">{company}</span>
                <span class="urgency {urgency_class}">{urgency}</span>
                <div class="title">{t.get('title', 'Unknown')[:100]}</div>
                <div class="meta">📍 {t.get('client', 'Unknown')} | 📁 {t.get('category', 'Unknown')} | Score: {scores.get('composite', 0)}</div>
            </div>
            """
    
    if medium_priority:
        html += f"<h2 style='color: #feca57;'>✅ Medium Priority ({len(medium_priority)})</h2>"
        for t in medium_priority[:5]:  # Limit to 5
            days = get_days_until_closing(t.get("closing_date"))
            urgency = get_urgency_text(days)
            
            scores = t.get("scores", {})
            company = "TES" if scores.get("tes", 0) > scores.get("phakathi", 0) else "Phakathi" if scores.get("phakathi", 0) > scores.get("tes", 0) else "Both"
            
            html += f"""
            <div class="tender medium">
                <span class="ref">{t.get('ref', 'N/A')}</span>
                <span class="company">{company}</span>
                <div class="title">{t.get('title', 'Unknown')[:80]}</div>
                <div class="meta">📍 {t.get('client', 'Unknown')} | {urgency}</div>
            </div>
            """
    
    if not high_priority and not medium_priority:
        html += "<p style='text-align: center; color: #888; padding: 40px;'>No high or medium priority tenders today. 📭</p>"
    
    html += f"""
            <div class="footer">
                <p>View full dashboard: <a href="https://vercel-dashboard-roan.vercel.app">vercel-dashboard-roan.vercel.app</a></p>
                <p>Tender Intelligence System | TES & Phakathi</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def send_email(subject, html_content):
    """Send email via SMTP"""
    if not EMAIL_CONFIG["sender_email"] or not EMAIL_CONFIG["recipient_emails"]:
        print("⚠️  Email not configured. Update EMAIL_CONFIG in email_alerts.py")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_CONFIG["sender_email"]
        msg["To"] = ", ".join(EMAIL_CONFIG["recipient_emails"])
        
        msg.attach(MIMEText(html_content, "html"))
        
        with smtplib.SMTP(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["sender_password"])
            server.sendmail(
                EMAIL_CONFIG["sender_email"],
                EMAIL_CONFIG["recipient_emails"],
                msg.as_string()
            )
        
        print("✅ Email sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False

def send_daily_digest():
    """Main function to send daily digest"""
    print("📧 Preparing daily tender digest...")
    
    tenders = load_tenders()
    high_count = sum(1 for t in tenders if t.get("scores", {}).get("priority") == "HIGH")
    
    if high_count == 0:
        print("   No high priority tenders - skipping email")
        return
    
    subject = f"🎯 {high_count} High Priority Tender{'s' if high_count != 1 else ''} - {datetime.now().strftime('%d %b')}"
    html = generate_email_html(tenders)
    
    send_email(subject, html)

if __name__ == "__main__":
    send_daily_digest()
