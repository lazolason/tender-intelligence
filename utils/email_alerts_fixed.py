"""
Email Alerts Utility for Tender Intelligence
Sends urgent tender notifications via email
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import logging
import json
import os
from typing import Any, Dict, Iterable, List, Optional
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


def load_email_config():
    """
    Load email configuration from config.yaml and environment variables.
    
    Returns:
        Dictionary with email configuration
    """
    # Load config from YAML
    config_file = Path(__file__).parent.parent / "config.yaml"
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Could not load config.yaml: {e}")
        config = {}
    
    # Get email config section
    email_config = config.get('email', {})
    
    # Build configuration dict
    result = {
        "smtp_server": os.getenv('SMTP_SERVER', email_config.get('smtp_server', 'smtp.gmail.com')),
        "smtp_port": int(os.getenv('SMTP_PORT', str(email_config.get('smtp_port', 587))),
        "sender_email": os.getenv('SMTP_USER', os.getenv('EMAIL_FROM', email_config.get('from_address', ''))),
        "sender_password": os.getenv('SMTP_PASSWORD', ''),
        "recipient_emails": [],
    }
    
    # Parse recipients from env var if provided
    email_to = os.getenv('EMAIL_TO', '')
    if email_to:
        result["recipient_emails"] = [addr.strip() for addr in email_to.split(',')]
    elif email_config.get('to_addresses'):
        result["recipient_emails"] = email_config['to_addresses']
    
    return result


# Load configuration on module import
EMAIL_CONFIG = load_email_config()


class EmailAlerter:
    """Handles email alerts for urgent tenders"""
    
    def __init__(self, smtp_config=None):
        """
        Initialize email alerter with SMTP configuration
        
        Args:
            smtp_config: Optional dictionary (uses EMAIL_CONFIG if not provided)
        """
        # Use provided config or load from config.yaml + env vars
        smtp_config = smtp_config or EMAIL_CONFIG
        
        self.smtp_server = smtp_config.get("smtp_server", "smtp.gmail.com")
        self.smtp_port = smtp_config.get("smtp_port", 587)
        self.sender_email = smtp_config.get("sender_email", "")
        self.sender_password = smtp_config.get("sender_password", "")
        self.recipients = smtp_config.get("recipient_emails", []) or []
    
    def send_urgent_alert(self, urgent_tenders):
        """
        Send email for HIGH priority tenders closing soon
        
        Args:
            urgent_tenders: List of tender dictionaries with urgent status
        """
        tenders = list(urgent_tenders or [])
        if not tenders:
            logger.info("No urgent tenders to alert on.")
            return False
        
        # Requirements: filter for HIGH priority tenders
        high_priority = []
        for tender in tenders:
            scores = (tender or {}).get("scores", {}) or {}
            priority = (scores.get("priority") or (tender or {}).get("priority") or "").upper()
            if priority == "HIGH":
                high_priority.append(tender)
        
        if not high_priority:
            logger.info("No HIGH priority urgent tenders to alert on.")
            return False
        
        if not self.recipients:
            logger.warning("No recipients configured for email alerts")
            return False
        
        if not self.sender_email or not self.sender_password:
            logger.warning("Email alerts enabled, but sender credentials are missing.")
            return False
        
        subject = f"🔴 URGENT: {len(high_priority)} Tender{'' if len(high_priority) == 1 else 's'} Closing Soon"
        
        html_body = self._generate_html_email(high_priority)
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.sender_email
        msg['To'] = ', '.join(self.recipients)
        
        # Add plain text alternative
        plain_text = self._generate_plain_text(high_priority)
        msg.attach(MIMEText(plain_text, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.recipients, msg.as_string())
            logger.info(f"✅ Email alert sent to {len(self.recipients)} recipient(s)")
            return True
        except Exception as e:
            # Requirements: handle errors gracefully
            logger.error(f"❌ Failed to send email alert: {e}")
            return False
    
    def send_scraper_failure_alert(self, failing_sources: Dict[str, Dict[str, Any]]):
        """
        Send email alert when scrapers fail repeatedly (e.g., 3 times in a row).

        Args:
            failing_sources: mapping of source -> metrics dict (from ScraperMonitor)
        """
        failing_sources = failing_sources or {}
        if not failing_sources:
            return False
        
        if not self.recipients:
            logger.warning("No recipients configured for scraper failure alerts")
            return False
        
        if not self.sender_email or not self.sender_password:
            logger.warning("Scraper failure alerts enabled, but sender credentials are missing.")
            return False
        
        sources = list(failing_sources.keys())
        subject = f"⚠️ Scraper Alert: {len(sources)} Source{'' if len(sources) == 1 else 's'} Failing Repeatedly"
        
        plain_lines = ["SCRAPER FAILURE ALERT", "=" * 50, ""]
        plain_lines.append("The following sources have failed 3 times in a row:")
        plain_lines.append("")
        for src in sources:
            m = failing_sources.get(src, {}) or {}
            plain_lines.append(f"- {src}: consecutive_failures={m.get('consecutive_failures')} success_rate={m.get('success_rate')}")
            if m.get("error_message"):
                plain_lines.append(f"  Last error: {m.get('error_message')}")
        plain_lines.append("")
        plain_lines.append("Recommendation: consider disabling or investigating these scrapers.")
        plain_text = "\n".join(plain_lines)
        
        html_rows = ""
        for src in sources:
            m = failing_sources.get(src, {}) or {}
            cf = m.get("consecutive_failures", 0)
            sr = m.get("success_rate", 0.0)
            last_run = m.get("last_run", "-")
            err = (m.get("error_message") or "-")
            html_rows += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 12px; font-weight: 600;">{src}</td>
                <td style="padding: 12px;">{last_run}</td>
                <td style="padding: 12px; text-align:center;"><strong>{cf}</strong></td>
                <td style="padding: 12px; text-align:center;">{float(sr):.0%}</td>
                <td style="padding: 12px; color:#444;">{err}</td>
            </tr>
            """
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; padding: 20px; background: #f5f5f5; margin: 0;">
            <div style="max-width: 900px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 26px 20px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 22px; font-weight: 700;">🩺 Scraper Failure Alert</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0;">Sources failing 3 times in a row</p>
                </div>
                <div style="padding: 18px 18px 8px 18px;">
                    <p style="margin: 0 0 12px 0; color: #333;">
                        Recommendation: consider disabling or investigating these scrapers.
                    </p>
                    <table style="border-collapse: collapse; width: 100%; margin: 12px 0;">
                        <tr>
                            <th style="background: #667eea; color: #fff; padding: 10px; text-align:left;">Source</th>
                            <th style="background: #667eea; color: #fff; padding: 10px; text-align:left;">Last Run</th>
                            <th style="background: #667eea; color: #fff; padding: 10px; text-align:center;">Consecutive Failures</th>
                            <th style="background: #667eea; color: #fff; padding: 10px; text-align:center;">Success Rate</th>
                            <th style="background: #667eea; color: #fff; padding: 10px; text-align:left;">Last Error</th>
                        </tr>
                        {html_rows}
                    </table>
                </div>
                <div style="padding: 14px 18px; background: #fafafa; border-top: 1px solid #eee; color: #666; font-size: 12px;">
                    Generated by TenderScan | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = ", ".join(self.recipients)
        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.recipients, msg.as_string())
            logger.info(f"✅ Scraper failure alert sent to {len(self.recipients)} recipient(s)")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send scraper failure alert: {e}")
            return False
    
    def _generate_plain_text(self, tenders):
        """Generate plain text email body"""
        lines = ["URGENT TENDER ALERT", "=" * 50, ""]
        lines.append(f"The following {len(tenders)} tender(s) require immediate attention:")
        lines.append("")
        
        for t in tenders:
            priority = t.get('scores', {}).get('priority', t.get('priority', 'UNKNOWN'))
            ref = t.get('ref', 'N/A')
            title = t.get('title', 'Unknown')[:80]
            closing = t.get('closing_date', 'TBC')
            url = t.get('url', '#')
            
            lines.append(f"Priority: {priority}")
            lines.append(f"Ref: {ref}")
            lines.append(f"Title: {title}")
            lines.append(f"Closing: {closing}")
            lines.append(f"Link: {url}")
            lines.append("-" * 50)
        
        lines.append("")
        lines.append("View full dashboard: https://tender-intelligence-dashboard.vercel.app")
        return "\n".join(lines)
    
    def _generate_html_email(self, tenders):
        """Generate HTML email body"""
        rows = ""
        for t in tenders:
            # Priority badges (requirements)
            priority_color = {"HIGH": "#ff6b6b", "MEDIUM": "#feca57", "LOW": "#48dbfb"}
            scores = t.get('scores', {})
            priority = (scores.get("priority") or t.get("priority") or "UNKNOWN").upper()
            color = priority_color.get(priority, "#888")
            badge_text_color = "#ffffff" if priority == "HIGH" else "#0a0a0a"
            
            ref = t.get('ref', 'N/A')
            title = t.get('title', 'Unknown')
            # Truncate long titles
            if len(title) > 80:
                title = title[:80] + '...'
            
            closing = t.get('closing_date', 'TBC')
            if closing and closing != 'TBC':
                try:
                    # Format date nicely
                    dt = datetime.fromisoformat(closing.replace('Z', '+00:00'))
                    closing = dt.strftime('%d %b %Y')
                except:
                    pass
            
            url = t.get('url', '#')
            
            rows += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 12px;">
                    <span style="
                        display: inline-block;
                        padding: 4px 10px;
                        border-radius: 999px;
                        background: {color};
                        color: {badge_text_color};
                        font-weight: 700;
                        font-size: 12px;
                        letter-spacing: 0.5px;">
                        {priority}
                    </span>
                </td>
                <td style="padding: 12px; font-family: monospace; color: #666;">
                    {ref}
                </td>
                <td style="padding: 12px; color: #333;">
                    {title}
                </td>
                <td style="padding: 12px; color: #666;">
                    {closing}
                </td>
                <td style="padding: 12px; text-align: center;">
                    <a href="{url}" style="
                        display: inline-block;
                        padding: 6px 12px;
                        background: #667eea;
                        color: white;
                        text-decoration: none;
                        border-radius: 6px;
                        font-size: 0.9rem;">
                        Open ↗
                    </a>
                </td>
            </tr>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            padding: 20px;
            background: #f5f5f5;
            margin: 0;">
            <div style="
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                overflow: hidden;">
        
                <!-- Header -->
                <div style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 30px 20px;
                    text-align: center;">
                    <h1 style="
                        color: white;
                        margin: 0;
                        font-size: 24px;
                        font-weight: 600;">
                        🎯 Urgent Tender Alert
                    </h1>
                    <p style="
                        color: rgba(255,255,255,0.9);
                        margin: 10px 0 0 0;
                        font-size: 14px;">
                        The following tenders require immediate attention
                    </p>
                </div>
        
                <!-- Content -->
                <div style="padding: 30px 20px;">
                    <p style="
                        color: #333;
                        margin: 0 0 20px 0;
                        font-size: 15px;">
                        <strong>{len(tenders)}</strong> urgent tender{'' if len(tenders) == 1 else 's'}
                        {'is' if len(tenders) == 1 else 'are'} closing soon and require immediate review:
                    </p>
        
                    <!-- Tenders Table -->
                    <table style="
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                        border: 1px solid #e0e0e0;
                        border-radius: 8px;
                        overflow: hidden;">
                        <thead>
                            <tr style="background: #f8f9fa;">
                                <th style="
                                    padding: 12px;
                                    text-align: left;
                                    font-weight: 600;
                                    color: #666;
                                    font-size: 13px;
                                    border-bottom: 2px solid #e0e0e0;">
                                    Priority
                                </th>
                                <th style="
                                    padding: 12px;
                                    text-align: left;
                                    font-weight: 600;
                                    color: #666;
                                    font-size: 13px;
                                    border-bottom: 2px solid #e0e0e0;">
                                    Ref
                                </th>
                                <th style="
                                    padding: 12px;
                                    text-align: left;
                                    font-weight: 600;
                                    color: #666;
                                    font-size: 13px;
                                    border-bottom: 2px solid #e0e0e0;">
                                    Title
                                </th>
                                <th style="
                                    padding: 12px;
                                    text-align: left;
                                    font-weight: 600;
                                    color: #666;
                                    font-size: 13px;
                                    border-bottom: 2px solid #e0e0e0;">
                                    Closing Date
                                </th>
                                <th style="
                                    padding: 12px;
                                    text-align: center;
                                    font-weight: 600;
                                    color: #666;
                                    font-size: 13px;
                                    border-bottom: 2px solid #e0e0e0;">
                                    Link
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows}
                        </tbody>
                    </table>
                </div>
        
                <!-- Footer -->
                <div style="
                    padding: 20px;
                    background: #f8f9fa;
                    border-top: 1px solid #e0e0e0;
                    text-align: center;">
                    <p style="
                        margin: 0 0 10px 0;
                        color: #666;
                        font-size: 14px;">
                        View full dashboard for more details:
                    </p>
                    <a href="https://tender-intelligence-dashboard.vercel.app" style="
                        display: inline-block;
                        padding: 10px 24px;
                        background: #667eea;
                        color: white;
                        text-decoration: none;
                        border-radius: 8px;
                        font-weight: 600;
                        font-size: 14px;">
                        Open Dashboard →
                    </a>
                    <p style="
                        margin: 20px 0 0 0;
                        color: #999;
                        font-size: 12px;">
                        This is an automated alert from Tender Intelligence System
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def send_email(subject, html_content):
        """Send email via SMTP"""
        if not EMAIL_CONFIG["sender_email"] or not EMAIL_CONFIG["recipient_emails"]:
            logger.warning("⚠️ Email not configured. Update EMAIL_CONFIG in utils/email_alerts.py")
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
            
            logger.info("✅ Email sent successfully!")
            return True
        except Exception as e:
            logger.error(f"❌ Email failed: {e}")
            return False


def load_tender_payload():
    """Load canonical tenders payload used by the deployed dashboard."""
    automation_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dashboard_tenders_json = os.path.join(automation_dir, "vercel-dashboard", "tenders.json")
    legacy_tenders_json = os.path.join(automation_dir, "output", "new_tenders.json")
    
    for path in (dashboard_tenders_json, legacy_tenders_json):
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            continue
    
    if isinstance(payload, list):
        return {"tenders": payload, "meta": {}, "source_path": path}
    if isinstance(payload, dict):
        tenders = payload.get("tenders") or payload.get("data") or []
        meta = payload.get("meta") or {}
        if isinstance(tenders, list) and isinstance(meta, dict):
            return {"tenders": tenders, "meta": meta, "source_path": path}
    
    return {"tenders": [], "meta": {}, "source_path": None}


def get_days_until_closing(closing_date):
    """Calculate days until closing"""
    if not closing_date:
        return None
    try:
        close = datetime.strptime(closing_date, "%Y-%m-%d")
        delta = (close - datetime.now()).days
        return delta
    except (ValueError, TypeError):
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


def generate_email_html(tenders, meta=None):
    """Generate HTML email content"""
    meta = meta or {}
    build_id = meta.get("build_id") or meta.get("last_sync") or datetime.now().strftime("%Y-%m-%d %H:%M")
    
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
            <p style="color: #888; font-size: 11px; margin-top: 0;">Build stamp: <strong>{build_id}</strong></p>
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
                <p>View full dashboard: <a href="https://tender-intelligence-dashboard.vercel.app/">https://tender-intelligence-dashboard.vercel.app/</a></p>
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
        logger.warning("⚠️ Email not configured. Update EMAIL_CONFIG in utils/email_alerts.py")
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
        
        logger.info("✅ Email sent successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Email failed: {e}")
        return False


def send_daily_digest():
    """Main function to send daily digest"""
    logger.info("📧 Preparing daily tender digest...")
    
    payload = load_tender_payload()
    tenders = payload.get("tenders") or []
    meta = payload.get("meta") or {}
    high_count = sum(1 for t in tenders if t.get("scores", {}).get("priority") == "HIGH")
    
    if high_count == 0:
        logger.info("   No high priority tenders - skipping email")
        return False
    
    stamp = meta.get("build_id") or meta.get("last_sync") or datetime.now().strftime("%Y-%m-%d")
    subject = f"🎯 {high_count} High Priority Tender{'s' if high_count != 1 else ''} - {stamp}"
    html = generate_email_html(tenders, meta=meta)
    
    return send_email(subject, html)
