"""
Email Alerts Utility for Tender Intelligence
Sends urgent tender notifications via email
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import logging
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


class EmailAlerter:
    """Handles email alerts for urgent tenders"""
    
    def __init__(self, smtp_config):
        """
        Initialize email alerter with SMTP configuration
        
        Args:
            smtp_config: Dictionary with keys:
                - server: SMTP server address
                - port: SMTP port (usually 587)
                - sender_email: Email address to send from
                - sender_password: App-specific password
                - recipients: List of recipient email addresses
        """
        smtp_config = smtp_config or {}
        self.smtp_server = smtp_config.get("server", "smtp.gmail.com")
        self.smtp_port = smtp_config.get("port", 587)
        self.sender_email = smtp_config.get("sender_email", "")
        self.sender_password = smtp_config.get("sender_password", "")
        self.recipients = smtp_config.get("recipients", []) or []
    
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
                        Recommendation: consider disabling or investigating the scrapers below.
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
                        View the full dashboard for more details:
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
