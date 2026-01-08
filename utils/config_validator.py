"""
Configuration validation utilities
Validates config.yaml structure and values
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate configuration structure and required fields
    
    Args:
        config: Configuration dictionary from config.yaml
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required top-level sections
    required_sections = ['paths', 'scrapers', 'classification', 'scoring', 'excel']
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")
    
    # Validate paths section
    if 'paths' in config:
        paths = config['paths']
        required_paths = ['tender_log_excel', 'active_tenders', 'output_dir', 'log_file']
        for path_key in required_paths:
            if path_key not in paths:
                errors.append(f"Missing required path: paths.{path_key}")
            elif not paths[path_key]:
                errors.append(f"Empty path value: paths.{path_key}")
    
    # Validate scrapers section
    if 'scrapers' in config:
        scrapers = config['scrapers']
        if 'enable_selenium' not in scrapers:
            errors.append("Missing scrapers.enable_selenium setting")
        if 'timeout' not in scrapers:
            errors.append("Missing scrapers.timeout setting")
        elif not isinstance(scrapers.get('timeout'), int) or scrapers.get('timeout') <= 0:
            errors.append("scrapers.timeout must be a positive integer")
    
    # Validate scoring section
    if 'scoring' in config:
        scoring = config['scoring']
        required_weights = ['fit_weight', 'industry_weight', 'risk_weight', 'revenue_weight']
        for weight in required_weights:
            if weight not in scoring:
                errors.append(f"Missing scoring weight: scoring.{weight}")
            elif not isinstance(scoring.get(weight), (int, float)):
                errors.append(f"scoring.{weight} must be a number")
            elif not 0 <= scoring.get(weight, 0) <= 1:
                errors.append(f"scoring.{weight} must be between 0 and 1")
        
        # Check threshold values
        if 'high_threshold' in scoring:
            if not isinstance(scoring['high_threshold'], (int, float)):
                errors.append("scoring.high_threshold must be a number")
        if 'medium_threshold' in scoring:
            if not isinstance(scoring['medium_threshold'], (int, float)):
                errors.append("scoring.medium_threshold must be a number")
    
    # Validate email section
    if 'email' in config:
        email = config['email']
        if 'smtp_server' not in email:
            errors.append("Missing email.smtp_server setting")
        if 'smtp_port' not in email:
            errors.append("Missing email.smtp_port setting")
        elif not isinstance(email.get('smtp_port'), int):
            errors.append("email.smtp_port must be an integer")
    
    # Validate alerts section
    if 'alerts' in config:
        alerts = config['alerts']
        required_alert_types = ['slack', 'sms', 'smart_alerts', 'scraper_failures']
        for alert_type in required_alert_types:
            if alert_type not in alerts:
                errors.append(f"Missing alerts.{alert_type} setting")
            elif 'enabled' not in alerts[alert_type]:
                errors.append(f"Missing alerts.{alert_type}.enabled setting")
    
    return len(errors) == 0, errors


def load_and_validate_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load and validate configuration from file
    
    Args:
        config_path: Path to config.yaml (defaults to ./config.yaml)
        
    Returns:
        Validated configuration dictionary
        
    Raises:
        ConfigValidationError: If configuration is invalid
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml')
    
    # Check file exists
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    # Load YAML
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Failed to parse YAML: {e}")
    
    # Validate structure
    is_valid, errors = validate_config(config)
    
    if not is_valid:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
        raise ConfigValidationError(error_msg)
    
    logger.info(f"Configuration loaded and validated successfully: {config_path}")
    return config


def validate_environment_variables() -> Tuple[bool, List[str]]:
    """
    Validate required environment variables are set
    
    Returns:
        Tuple of (all_present, list_of_missing_vars)
    """
    missing = []
    
    # Check email-related environment variables if email is enabled
    try:
        config = load_and_validate_config()
        
        if config.get('email', {}).get('enabled', False):
            email_vars = ['SMTP_USER', 'SMTP_PASSWORD']
            for var in email_vars:
                if not os.getenv(var):
                    missing.append(var)
        
        if config.get('email_alerts', {}).get('enabled', False):
            email_alert_vars = ['SMTP_USER', 'SMTP_PASSWORD']
            for var in email_alert_vars:
                if not os.getenv(var):
                    missing.append(var)
        
        # Check optional alert environment variables
        if config.get('alerts', {}).get('slack', {}).get('enabled', False):
            if not os.getenv('SLACK_WEBHOOK_URL'):
                missing.append('SLACK_WEBHOOK_URL (optional)')
        
        if config.get('alerts', {}).get('sms', {}).get('enabled', False):
            sms_vars = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM_NUMBER']
            for var in sms_vars:
                if not os.getenv(var):
                    missing.append(f"{var} (optional)")
    
    except (FileNotFoundError, ConfigValidationError):
        # Can't validate env vars without config
        return False, []
    
    return len(missing) == 0, missing


def get_config_summary(config: Dict[str, Any]) -> str:
    """
    Generate a human-readable summary of configuration
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Formatted summary string
    """
    summary_lines = ["Configuration Summary:", "=" * 50]
    
    # Paths
    if 'paths' in config:
        summary_lines.append("\nPaths:")
        for key, value in config['paths'].items():
            summary_lines.append(f"  {key}: {value}")
    
    # Scrapers
    if 'scrapers' in config:
        summary_lines.append("\nScrapers:")
        summary_lines.append(f"  Selenium enabled: {config['scrapers'].get('enable_selenium', False)}")
        summary_lines.append(f"  Timeout: {config['scrapers'].get('timeout', 15)}s")
    
    # Scoring
    if 'scoring' in config:
        summary_lines.append("\nScoring:")
        summary_lines.append(f"  High threshold: {config['scoring'].get('high_threshold', 7.0)}")
        summary_lines.append(f"  Medium threshold: {config['scoring'].get('medium_threshold', 4.5)}")
    
    # Email
    if 'email' in config:
        summary_lines.append("\nEmail:")
        summary_lines.append(f"  Enabled: {config['email'].get('enabled', False)}")
        summary_lines.append(f"  SMTP Server: {config['email'].get('smtp_server', 'N/A')}")
    
    # Alerts
    if 'alerts' in config:
        summary_lines.append("\nAlerts:")
        alerts = config['alerts']
        summary_lines.append(f"  Slack: {alerts.get('slack', {}).get('enabled', False)}")
        summary_lines.append(f"  SMS: {alerts.get('sms', {}).get('enabled', False)}")
        summary_lines.append(f"  Smart Alerts: {alerts.get('smart_alerts', {}).get('enabled', False)}")
    
    return "\n".join(summary_lines)


# Standalone test
if __name__ == "__main__":
    try:
        config = load_and_validate_config()
        print(get_config_summary(config))
        
        # Validate environment variables
        env_valid, missing = validate_environment_variables()
        if env_valid:
            print("\n✅ All required environment variables are set")
        elif missing:
            print(f"\n⚠️  Missing environment variables: {', '.join(missing)}")
    
    except FileNotFoundError as e:
        print(f"❌ {e}")
    except ConfigValidationError as e:
        print(f"❌ {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
