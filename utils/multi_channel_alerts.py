# ==========================================================
# MULTI-CHANNEL ALERTS - Slack, SMS, Push Notifications
# ==========================================================

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ==========================================================
# CONFIGURATION
# ==========================================================

class AlertConfig:
    """Configuration for multi-channel alerts"""
    
    def __init__(self, slack_webhook: Optional[str] = None,
                 slack_channels: Dict[str, str] = None,
                 twilio_account_sid: Optional[str] = None,
                 twilio_auth_token: Optional[str] = None,
                 twilio_from_number: Optional[str] = None,
                 sms_recipients: List[str] = None,
                 push_tokens: List[str] = None,
                 enabled_channels: List[str] = None):
        self.slack_webhook = slack_webhook
        self.slack_channels = slack_channels or {
            'high_priority': '#tenders-high',
            'medium_priority': '#tenders-medium',
            'all': '#tenders'
        }
        self.twilio_account_sid = twilio_account_sid
        self.twilio_auth_token = twilio_auth_token
        self.twilio_from_number = twilio_from_number
        self.sms_recipients = sms_recipients or []
        self.push_tokens = push_tokens or []
        self.enabled_channels = enabled_channels or ['email']
    
    def is_enabled(self, channel: str) -> bool:
        """Check if a channel is enabled"""
        return channel in self.enabled_channels
    
    def should_send_slack(self, priority: str) -> bool:
        """Determine if Slack alert should be sent"""
        if priority == 'HIGH':
            return self.is_enabled('slack') and 'high_priority' in self.slack_channels
        elif priority == 'MEDIUM':
            return self.is_enabled('slack') and 'medium_priority' in self.slack_channels
        return False
    
    def should_send_sms(self, priority: str, urgent_only: bool = False) -> bool:
        """Determine if SMS alert should be sent"""
        if not self.is_enabled('sms'):
            return False
        
        # SMS for urgent tenders only
        if urgent_only and priority != 'HIGH':
            return False
        
        # Check if recipient is configured
        if not self.sms_recipients:
            return False
        
        return True
    
    def get_slack_channel(self, priority: str) -> str:
        """Get appropriate Slack channel for priority"""
        if priority == 'HIGH' and 'high_priority' in self.slack_channels:
            return self.slack_channels['high_priority']
        elif priority == 'MEDIUM' and 'medium_priority' in self.slack_channels:
            return self.slack_channels['medium_priority']
        else:
            return self.slack_channels.get('all', '#tenders')


# ==========================================================
# SLACK ALERTS
# ==========================================================

def send_slack_alert(config: AlertConfig, tender: Dict, priority: str, 
                     message: str, emoji: str = "🎯") -> bool:
    """
    Send alert to Slack
    
    Args:
        config: Alert configuration
        tender: Tender dictionary
        priority: Priority level (HIGH, MEDIUM, LOW)
        message: Alert message
        emoji: Emoji to use in alert
        
    Returns:
        True if successful, False otherwise
    """
    if not config.should_send_slack(priority):
        logger.debug(f"Slack disabled for {priority} priority")
        return False
    
    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
        
        client = WebClient(token=config.slack_webhook)
        
        # Build message
        title = tender.get('title', 'Unknown Tender')
        ref = tender.get('ref', 'N/A')
        source = tender.get('source', 'Unknown')
        category = tender.get('category', 'Unknown')
        score = tender.get('scores', {}).get('composite_score', 0)
        priority_color = {
            'HIGH': '#ff6b6b',
            'MEDIUM': '#feca57',
            'LOW': '#48dbfb'
        }.get(priority, '#48dbfb')
        
        slack_message = {
            'text': f"{emoji} *{priority}* Priority Tender\n\n"
                      f"*Title:* {title}\n\n"
                      f"*Reference:* {ref}\n\n"
                      f"*Source:* {source}\n\n"
                      f"*Category:* {category}\n\n"
                      f"*Score:* {score}/10\n\n"
                      f"*Closing Date:* {tender.get('closing_date', 'N/A')}",
            'attachments': [
                {
                    'color': priority_color[priority],
                    'title': f"{emoji} {priority} Priority - {ref}",
                    'text': f"{title}\n"
                             f"Score: {score}/10 | {tender.get('scores', {}).get('priority', 'LOW')}\n"
                             f"Category: {category} | Source: {source}",
                    'footer': f"Closing: {tender.get('closing_date', 'N/A')}",
                    'actions': [
                        {
                            'type': 'button',
                            'text': 'View Details',
                            'url': tender.get('url', '#'),
                            'style': 'primary'
                        }
                    ]
                }
            ],
            'channel': config.get_slack_channel(priority)
        }
        
        # Send message
        response = client.chat_postMessage(**slack_message)
        
        if response['ok']:
            logger.info(f"Slack alert sent: {ref} ({priority}) to {config.slack_channels.get(config.get_slack_channel(priority), 'default')}")
            return True
        else:
            logger.error(f"Slack alert failed: {response['error']}")
            return False
    
    except ImportError:
        logger.warning("slack-sdk not installed, skipping Slack alerts")
        return False
    except SlackApiError as e:
        logger.error(f"Slack API error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending Slack alert: {e}")
        return False


# ==========================================================
# SMS ALERTS
# ==========================================================

def send_sms_alert(config: AlertConfig, tender: Dict, priority: str,
                   message: str = "Urgent tender") -> bool:
    """
    Send SMS alert using Twilio
    
    Args:
        config: Alert configuration
        tender: Tender dictionary
        priority: Priority level
        message: Custom message (default: "Urgent tender")
        
    Returns:
        True if successful, False otherwise
    """
    if not config.should_send_sms(priority, urgent_only=True):
        logger.debug(f"SMS disabled or not urgent for {priority} priority")
        return False
    
    try:
        from twilio.rest import Client
        from twilio.base.exceptions import TwilioRestException
        
        client = Client(
            account_sid=config.twilio_account_sid,
            auth_token=config.twilio_auth_token
        )
        
        # Build message
        title = tender.get('title', 'Unknown Tender')
        ref = tender.get('ref', 'N/A')
        closing_date = tender.get('closing_date', 'N/A')
        days_left = _calculate_days_left(closing_date)
        
        urgency_text = "URGENT - " if priority == 'HIGH' else "IMPORTANT"
        
        sms_message = f"""
🎯 {urgency_text} TENDER ALERT 🎯

Ref: {ref}
Title: {title}

Priority: {priority}
Closing: {closing_date}

{days_left} days remaining

View details in your dashboard.
"""
        
        # Send to all recipients
        success_count = 0
        for phone_number in config.sms_recipients:
            try:
                message = client.messages.create(
                    body=sms_message,
                    from_=config.twilio_from_number,
                    to=phone_number
                )
                logger.info(f"SMS sent to {phone_number}: {ref}")
                success_count += 1
            except TwilioRestException as e:
                logger.error(f"SMS failed for {phone_number}: {e}")
        
        if success_count > 0:
            logger.info(f"SMS alert sent: {ref} to {success_count} recipients")
            return True
        else:
            logger.warning("No SMS alerts sent (all failed or no recipients)")
            return False
    
    except ImportError:
        logger.warning("twilio not installed, skipping SMS alerts")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending SMS alert: {e}")
        return False


def _calculate_days_left(closing_date: str) -> str:
    """
    Calculate days remaining until closing date
    
    Args:
        closing_date: Date string (YYYY-MM-DD)
        
    Returns:
        Formatted days remaining string
    """
    if not closing_date or closing_date == 'N/A':
        return 'N/A'
    
    try:
        from datetime import datetime
        closing = datetime.strptime(closing_date, '%Y-%m-%d')
        today = datetime.now()
        today = today.replace(hour=0, minute=0, second=0, microsecond=0)
        
        delta = closing - today
        days_left = delta.days
        
        if days_left <= 0:
            return f"CLOSED ({abs(days_left)} days ago)"
        elif days_left == 1:
            return "TOMORROW"
        elif days_left <= 3:
            return f"{days_left} days"
        elif days_left <= 7:
            return f"{days_left} days"
        else:
            return f"{days_left} days"
    except:
        return 'N/A'


# ==========================================================
# PUSH NOTIFICATIONS (Optional)
# ==========================================================

def send_push_notification(config: AlertConfig, tender: Dict, priority: str,
                          message: str = "New tender available") -> bool:
    """
    Send push notification (placeholder for future Firebase/OneSignal integration)
    
    Args:
        config: Alert configuration
        tender: Tender dictionary
        priority: Priority level
        message: Custom message (default: "New tender available")
        
    Returns:
        True if successful, False otherwise
    """
    if not config.push_tokens:
        logger.debug("Push notifications not configured")
        return False
    
    # Placeholder for future implementation
    logger.info(f"Push notification for {tender.get('ref', 'N/A')}: Not yet implemented")
    return False


# ==========================================================
# SMART ALERTING
# ==========================================================

def smart_alert(config: AlertConfig, tender: Dict) -> Dict[str, bool]:
    """
    Determine which alert channels to use and send alerts
    
    Args:
        config: Alert configuration
        tender: Tender dictionary
        
    Returns:
        Dictionary mapping channel names to success status
    """
    priority = tender.get('scores', {}).get('priority', 'LOW')
    results = {}
    
    # Slack for HIGH and MEDIUM priority
    if config.should_send_slack(priority):
        slack_sent = send_slack_alert(config, tender, priority)
        results['slack'] = slack_sent
    
    # SMS for HIGH priority only
    if config.should_send_sms(priority, urgent_only=True):
        sms_sent = send_sms_alert(config, tender, priority)
        results['sms'] = sms_sent
    
    # Push notifications (optional)
    if config.is_enabled('push'):
        push_sent = send_push_notification(config, tender, priority)
        results['push'] = push_sent
    
    # Email is always enabled
    results['email'] = True  # Email handled by existing system
    
    return results


# ==========================================================
# BATCH ALERTING
# ==========================================================

def send_batch_alerts(config: AlertConfig, tenders: List[Dict]) -> Dict[str, Dict]:
    """
    Send alerts for multiple tenders
    
    Args:
        config: Alert configuration
        tenders: List of tender dictionaries
        
    Returns:
        Dictionary mapping tender refs to alert results
    """
    results = {}
    
    for tender in tenders:
        ref = tender.get('ref', 'Unknown')
        results[ref] = smart_alert(config, tender)
    
    # Summary
    slack_count = sum(1 for v in results.values() if v.get('slack', False))
    sms_count = sum(1 for v in results.values() if v.get('sms', False))
    push_count = sum(1 for v in results.values() if v.get('push', False))
    
    logger.info(f"Batch alerts complete: {len(tenders)} tenders, "
                f"{slack_count} Slack, {sms_count} SMS, {push_count} Push")
    
    return results


# ==========================================================
# STANDALONE TEST
# ==========================================================
if __name__ == "__main__":
    # Test with sample tender
    test_tender = {
        "ref": "NT-001",
        "title": "Supply of water treatment chemicals",
        "description": "Supply and delivery of cooling water treatment chemicals",
        "source": "National Treasury",
        "closing_date": "2025-01-15",
        "category": "TES",
        "scores": {
            "priority": "HIGH",
            "composite_score": 8.5
        }
    }
    
    print("=" * 60)
    print("MULTI-CHANNEL ALERTS TEST")
    print("=" * 60)
    
    # Test with default config (no credentials)
    config = AlertConfig()
    
    # Test Slack alert
    print("\n--- Testing Slack Alert ---")
    slack_result = send_slack_alert(config, test_tender, "HIGH", "🔥")
    print(f"Slack: {slack_result}")
    
    # Test SMS alert
    print("\n--- Testing SMS Alert ---")
    sms_result = send_sms_alert(config, test_tender, "HIGH", "Urgent tender")
    print(f"SMS: {sms_result}")
    
    # Test smart alert
    print("\n--- Testing Smart Alert ---")
    smart_results = smart_alert(config, test_tender)
    print(f"Smart results: {smart_results}")
    
    # Test batch alerts
    print("\n--- Testing Batch Alerts ---")
    batch_results = send_batch_alerts(config, [test_tender])
    print(f"Batch results: {batch_results}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("\nNote: To enable Slack/SMS alerts, add credentials to config.yaml:")
    print("  alerts:")
    print("    slack:")
    print("      webhook: 'https://hooks.slack.com/services/YOUR_WEBHOOK'")
    print("      channels:")
    print("        high_priority: '#tenders-high'")
    print("        medium_priority: '#tenders-medium'")
    print("    sms:")
    print("      account_sid: 'YOUR_TWILIO_ACCOUNT_SID'")
    print("      auth_token: 'YOUR_TWILIO_AUTH_TOKEN'")
    print("      from_number: 'YOUR_TWILIO_NUMBER'")
    print("      recipients:")
    print("        - '+27XXXXXXXXXXX'")
    print("        - '+27XXXXXXXXXXX'")
