"""
Email Alerts Utility for Tender Intelligence
Sends urgent tender notifications via email
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import logging

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
        self.smtp_server = smtp_config.get('server', 'smtp.gmail.com')
        self.smtp_port = smtp_config.get('port', 587)
        self.sender_email = smtp_config['sender_email']
        self.sender_password = smtp_config['sender_password']
        self.recipients = smtp_config.get('recipients', [])
    
    def send_urgent_alert(self, urgent_tenders):
        """
        Send email for HIGH priority tenders closing soon
        
        Args:
            urgent_tenders: List of tender dictionaries with urgent status
        """
        if not urgent_tenders:
            logger.info("No urgent tenders to alert on")
            return
        
        if not self.recipients:
            logger.warning("No recipients configured for email alerts")
            return
        
        subject = f"🔴 URGENT: {len(urgent_tenders)} Tender{'' if len(urgent_tenders) == 1 else 's'} Closing Soon"
        
        html_body = self._generate_html_email(urgent_tenders)
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.sender_email
        msg['To'] = ', '.join(self.recipients)
        
        # Add plain text alternative
        plain_text = self._generate_plain_text(urgent_tenders)
        msg.attach(MIMEText(plain_text, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.recipients, msg.as_string())
            logger.info(f"✅ Email alert sent to {len(self.recipients)} recipient(s)")
        except Exception as e:
            logger.error(f"❌ Failed to send email alert: {e}")
            raise
    
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
            priority_color = {'HIGH': '#ff6b6b', 'MEDIUM': '#feca57', 'LOW': '#48dbfb'}
            scores = t.get('scores', {})
            priority = scores.get('priority', t.get('priority', 'UNKNOWN'))
            color = priority_color.get(priority, '#888')
            
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
                <td style="padding: 12px; font-weight: bold; color: {color};">
                    {priority}
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
                        View →
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
                                    Closing
                                </th>
                                <th style="
                                    padding: 12px;
                                    text-align: center;
                                    font-weight: 600;
                                    color: #666;
                                    font-size: 13px;
                                    border-bottom: 2px solid #e0e0e0;">
                                    Action
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
