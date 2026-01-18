# Utils Module Documentation

This directory contains utility modules for the Tender Intelligence System.

## Table of Contents

- [text_utils.py](#text_utilspy) - Shared text processing utilities
- [duplicate_detector.py](#duplicate_detectorpy) - Fuzzy duplicate detection
- [semantic_duplicate_detector.py](#semantic_duplicate_detectorpy) - ML-based semantic duplicate detection
- [data_validator.py](#data_validatorpy) - Tender data validation
- [excel_writer.py](#excel_writerpy) - Excel file operations
- [email_alerts.py](#email_alertspy) - Email alert functionality
- [config_validator.py](#config_validatorpy) - Configuration validation
- [logging_tools.py](#logging_toolspy) - Logging utilities
- [retry_tools.py](#retry_toolspy) - Retry logic with exponential backoff
- [text_cleaner.py](#text_cleanerpy) - Text cleaning utilities
- [pdf_tools.py](#pdf_toolspy) - PDF analysis tools
- [folder_tools.py](#folder_toolspy) - Folder creation utilities
- [scraper_monitor.py](#scraper_monitorpy) - Scraper health monitoring
- [bid_tracker.py](#bid_trackerpy) - Bid outcome tracking
- [multi_channel_alerts.py](#multi_channel_alertspy) - Multi-channel alert system (Slack, SMS, Push)

---

## text_utils.py

Shared text processing utilities used across the codebase.

### Functions

#### `normalize_text(value: str) -> str`
Normalizes text for comparison by:
- Converting to lowercase
- Removing extra whitespace
- Replacing multiple spaces with single space

**Parameters:**
- `value`: Input text string (can be None)

**Returns:**
- Normalized text string (empty string if input is None or empty)

**Example:**
```python
from utils.text_utils import normalize_text

normalize_text("  HELLO  WORLD  ")  # Returns: "hello world"
```

---

#### `parse_date(value: str) -> Optional[date]`
Parses date strings into Python date objects using python-dateutil.

**Parameters:**
- `value`: Date string in various formats

**Returns:**
- `datetime.date` object if parsing succeeds
- `None` if parsing fails or input is empty

**Supported Formats:**
- ISO format: `2025-01-15`
- Slash format: `2025/01/15`
- Month names: `15 January 2025`, `15 Jan 2025`
- With time: `2025-01-15T10:30:00`

**Example:**
```python
from utils.text_utils import parse_date

parse_date("2025-01-15")  # Returns: date(2025, 1, 15)
parse_date("15 January 2025")  # Returns: date(2025, 1, 15)
parse_date("TBC")  # Returns: None
```

---

#### `within_days(a: Optional[date], b: Optional[date], *, days: int) -> bool`
Checks if two dates are within a specified number of days of each other.

**Parameters:**
- `a`: First date (can be None)
- `b`: Second date (can be None)
- `days`: Maximum number of days between dates

**Returns:**
- `True` if dates are within `days` of each other
- `False` if either date is None or difference exceeds `days`

**Example:**
```python
from utils.text_utils import within_days

within_days(date(2025, 1, 15), date(2025, 1, 18), days=5)  # Returns: True
within_days(date(2025, 1, 15), date(2025, 1, 22), days=5)  # Returns: False
```

---

## duplicate_detector.py

Fuzzy duplicate detection using string similarity.

### Functions

#### `find_duplicate(new_tender, existing_tenders, *, threshold, date_window_days, require_same_source) -> Optional[DuplicateMatch]`
Finds duplicate tenders using fuzzy string matching.

**Parameters:**
- `new_tender`: New tender dictionary to check
- `existing_tenders`: Iterable of existing tender dictionaries
- `threshold`: Fuzzy match threshold (0-100, default: 85)
- `date_window_days`: Days to consider for date matching (default: 7)
- `require_same_source`: Whether to require same source (default: True)

**Returns:**
- `DuplicateMatch` object if duplicate found, `None` otherwise

**Example:**
```python
from utils.duplicate_detector import find_duplicate

match = find_duplicate(
    new_tender={"ref": "NT-001", "title": "Supply of pumps"},
    existing_tenders=[{"ref": "NT-001", "title": "Supply of pumps"}],
    threshold=85
)
# Returns: DuplicateMatch with is_duplicate=True, similarity=100
```

---

#### `find_best_title_match(new_tender, existing_tenders) -> Optional[Tuple[int, Dict]]`
Finds the best matching title from existing tenders.

**Parameters:**
- `new_tender`: New tender dictionary
- `existing_tenders`: Iterable of existing tender dictionaries

**Returns:**
- Tuple of (similarity_score, best_matching_tender) or `None`

---

## semantic_duplicate_detector.py

ML-based semantic duplicate detection using sentence embeddings.

### Functions

#### `find_semantic_duplicate(new_tender, existing_tenders, *, semantic_threshold, fuzzy_threshold, date_window_days, require_same_source) -> Optional[SemanticDuplicateMatch]`
Finds duplicate tenders using semantic similarity with fallback to fuzzy matching.

**Parameters:**
- `new_tender`: New tender dictionary
- `existing_tenders`: Iterable of existing tender dictionaries
- `semantic_threshold`: Cosine similarity threshold (0.0-1.0, default: 0.90)
- `fuzzy_threshold`: Fuzzy match threshold (0-100, default: 85)
- `date_window_days`: Days to consider for date matching (default: 7)
- `require_same_source`: Whether to require same source (default: True)

**Returns:**
- `SemanticDuplicateMatch` object if duplicate found, `None` otherwise

**Example:**
```python
from utils.semantic_duplicate_detector import find_semantic_duplicate

match = find_semantic_duplicate(
    new_tender={"ref": "NT-001", "title": "Supply of water treatment chemicals"},
    existing_tenders=[{"ref": "NT-002", "title": "Provision of water treatment chemicals"}],
    semantic_threshold=0.90
)
# Returns: SemanticDuplicateMatch with is_duplicate=True, similarity=0.95, match_type="semantic"
```

---

#### `filter_duplicates(tenders, *, semantic_threshold, fuzzy_threshold, date_window_days, require_same_source, keep_first) -> Tuple[List[Dict], List[SemanticDuplicateMatch]]`
Filters out duplicate tenders from a list.

**Parameters:**
- `tenders`: List of tender dictionaries
- `semantic_threshold`: Cosine similarity threshold (default: 0.90)
- `fuzzy_threshold`: Fuzzy match threshold (default: 85)
- `date_window_days`: Days to consider for date matching (default: 7)
- `require_same_source`: Whether to require same source (default: True)
- `keep_first`: If True, keep first occurrence; if False, find all duplicate pairs

**Returns:**
- Tuple of (filtered_tenders, duplicate_matches)

---

## data_validator.py

Validates tender data structure and required fields.

### Functions

#### `TenderValidator.validate_with_warnings(tender) -> ValidationResult`
Validates a tender dictionary and returns detailed validation results.

**Parameters:**
- `tender`: Tender dictionary to validate

**Returns:**
- `ValidationResult` object with:
  - `valid`: Boolean indicating if tender is valid
  - `errors`: List of validation errors
  - `warnings`: List of validation warnings

**Example:**
```python
from utils.data_validator import TenderValidator

validator = TenderValidator()
result = validator.validate_with_warnings({"ref": "NT-001", "title": "Supply of pumps"})
# Returns: ValidationResult with valid=True, errors=[], warnings=[]
```

---

## excel_writer.py

Writes tender data to Excel spreadsheets with scoring and formatting.

### Class: `ExcelWriter`

Manages Excel workbook operations including:
- Loading existing workbooks or creating new ones
- Writing tender data with duplicate detection
- Applying scoring and formatting
- Maintaining caches for performance

### Methods

#### `__init__(file_path, sheet_name, *, log_file_path, fuzzy_duplicate_threshold, fuzzy_date_window_days)`
Initialize Excel writer.

**Parameters:**
- `file_path`: Path to Excel file
- `sheet_name`: Name of worksheet (default: "Tender_Log")
- `log_file_path`: Optional path to log file
- `fuzzy_duplicate_threshold`: Fuzzy match threshold (default: 85)
- `fuzzy_date_window_days`: Date window for duplicates (default: 7)

#### `write_tender(tender_name, client, tender_type, industry, fit_score, stage, closing_date, status, next_action, notes, reference_number, *, composite_score, priority, risk_level, revenue_potential, tes_fit) -> bool`
Write a single tender to Excel.

**Parameters:**
- `tender_name`: Full tender name (e.g., "NT-001 - Supply of Pumps")
- `client`: Client organization name
- `tender_type`: Tender category/classification
- `industry`: Industry type with source
- `fit_score`: TES fit score (0-10)
- `stage`: Tender stage (e.g., "New", "In Progress")
- `closing_date`: Tender closing date string
- `status`: Current status (e.g., "Open", "Closed")
- `next_action`: Recommended next action
- `notes`: Additional notes
- `reference_number`: Tender reference number
- `composite_score`: Overall composite score (0-10)
- `priority`: Priority level (HIGH, MEDIUM, LOW)
- `risk_level`: Risk assessment (Low, Medium, High)
- `revenue_potential`: Revenue potential (Low, Medium, High)
- `tes_fit`: TES suitability score (0-10)

**Returns:**
- `True` if tender was added, `False` if duplicate

#### `get_stats() -> Dict[str, Any]`
Get tender statistics from Excel sheet.

**Returns:**
- Dictionary with:
  - `total`: Total number of tenders
  - `by_type`: Count by tender type
  - `by_priority`: Count by priority level
  - `by_status`: Count by status

**Example:**
```python
from utils.excel_writer import ExcelWriter

writer = ExcelWriter("/path/to/tender_log.xlsx")
stats = writer.get_stats()
# Returns: {"total": 100, "by_type": {"MEXEL": 50}, "by_priority": {"HIGH": 20, "MEDIUM": 50, "LOW": 30}}
```

---

## email_alerts.py

Email alert functionality for urgent tender notifications.

### Class: `EmailAlerter`

Handles email alerts for urgent tenders.

### Methods

#### `__init__(smtp_config=None)`
Initialize email alerter with SMTP configuration.

**Parameters:**
- `smtp_config`: Optional dictionary with SMTP settings (uses EMAIL_CONFIG if not provided)

**Configuration Dictionary:**
- `smtp_server`: SMTP server address (e.g., "smtp.gmail.com")
- `smtp_port`: SMTP port (e.g., 587)
- `sender_email`: Sender email address
- `sender_password`: Sender email password (app-specific password for Gmail)
- `recipient_emails`: List of recipient email addresses

#### `send_urgent_alert(urgent_tenders) -> bool`
Send email for HIGH priority tenders closing soon.

**Parameters:**
- `urgent_tenders`: List of tender dictionaries

**Returns:**
- `True` if email sent successfully, `False` otherwise

#### `send_scraper_failure_alert(failing_sources: Dict[str, Dict[str, Any]]) -> bool`
Send email alert when scrapers fail repeatedly (3 times in a row).

**Parameters:**
- `failing_sources`: Mapping of source name to metrics dict

**Returns:**
- `True` if email sent successfully, `False` otherwise

---

## config_validator.py

Configuration validation utilities for config.yaml.

### Functions

#### `validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]`
Validate configuration structure and required fields.

**Parameters:**
- `config`: Configuration dictionary from config.yaml

**Returns:**
- Tuple of (is_valid, list_of_errors)

**Validation Checks:**
- Required top-level sections: `paths`, `scrapers`, `classification`, `scoring`, `excel`
- Required paths: `tender_log_excel`, `active_tenders`, `output_dir`, `log_file`
- Scrapers settings: `enable_selenium`, `timeout`
- Scoring weights and thresholds
- Email settings: `smtp_server`, `smtp_port`, `from_address`, `to_addresses`
- Alerts configuration: `slack`, `sms`, `smart_alerts`, `scraper_failures`

**Example:**
```python
from utils.config_validator import validate_config

import yaml

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

is_valid, errors = validate_config(config)
if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

#### `load_and_validate_config(config_path: str = None) -> Dict[str, Any]`
Load and validate configuration from file.

**Parameters:**
- `config_path`: Path to config.yaml (defaults to ./config.yaml)

**Returns:**
- Validated configuration dictionary

**Raises:**
- `ConfigValidationError`: If configuration is invalid
- `FileNotFoundError`: If config file doesn't exist
- `yaml.YAMLError`: If YAML parsing fails

#### `validate_environment_variables() -> Tuple[bool, List[str]]`
Validate required environment variables are set.

**Returns:**
- Tuple of (all_present, list_of_missing_vars)

**Checked Variables:**
- Email: `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`, `EMAIL_TO`
- Slack: `SLACK_WEBHOOK_URL` (optional)
- SMS: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` (optional)

#### `get_config_summary(config: Dict[str, Any]) -> str`
Generate a human-readable summary of configuration.

**Returns:**
- Formatted summary string with all configuration sections

---

## Usage Examples

### Text Normalization
```python
from utils.text_utils import normalize_text, parse_date, within_days

# Normalize text for comparison
title = normalize_text("  SUPPLY OF PUMPS  ")
# Returns: "supply of pumps"

# Parse dates
closing = parse_date("2025-01-15")
# Returns: date(2025, 1, 15)

# Check date proximity
is_close = within_days(date(2025, 1, 15), date(2025, 1, 18), days=5)
# Returns: True
```

### Duplicate Detection
```python
from utils.duplicate_detector import find_duplicate
from utils.semantic_duplicate_detector import find_semantic_duplicate, filter_duplicates

# Fuzzy duplicate detection
match = find_duplicate(new_tender, existing_tenders, threshold=85)
if match.is_duplicate:
    print(f"Duplicate found: {match.reason} ({match.similarity}%)")

# Semantic duplicate detection
semantic_match = find_semantic_duplicate(new_tender, existing_tenders, semantic_threshold=0.90)
if semantic_match.is_duplicate:
    print(f"Semantic duplicate: {semantic_match.reason}")

# Filter duplicates from list
filtered, duplicates = filter_duplicates(tenders_list, semantic_threshold=0.90, fuzzy_threshold=85)
print(f"Filtered to {len(filtered)} tenders from {len(tenders_list)}")
```

### Excel Writing
```python
from utils.excel_writer import ExcelWriter

# Create Excel writer
writer = ExcelWriter(
    file_path="/path/to/tender_log.xlsx",
    sheet_name="Tender_Log",
    log_file_path="/path/to/scraper.log",
    fuzzy_duplicate_threshold=85,
    fuzzy_date_window_days=7
)

# Write tender with scoring
was_added = writer.write_tender(
    tender_name="NT-001 - Supply of Water Treatment Chemicals",
    client="Eskom",
    tender_type="MEXEL",
    industry="Power Generation",
    fit_score=8,
    stage="New",
    closing_date="2025-01-15",
    status="Open",
    next_action="Prepare Bid",
    notes="Test tender",
    reference_number="NT-001",
    composite_score=8.5,
    priority="HIGH",
    risk_level="Low",
    revenue_potential="High",
    tes_fit=9
)

if was_added:
    print("Tender added successfully")
else:
    print("Tender is a duplicate")

# Get statistics
stats = writer.get_stats()
print(f"Total tenders: {stats['total']}")
print(f"By priority: {stats['by_priority']}")
```

### Email Alerts
```python
from utils.email_alerts import EmailAlerter

# Initialize with default config
alerter = EmailAlerter()

# Or with custom config
custom_config = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your-email@gmail.com",
    "sender_password": "your-app-password",
    "recipient_emails": ["team@example.com"]
}
alerter = EmailAlerter(smtp_config=custom_config)

# Send urgent alert
urgent_tenders = [
    {
        "ref": "NT-001",
        "title": "Urgent Supply Contract",
        "closing_date": "2025-01-15",
        "scores": {"priority": "HIGH"}
    }
]
alerter.send_urgent_alert(urgent_tenders)
```

### Configuration Validation
```python
from utils.config_validator import load_and_validate_config, validate_environment_variables

# Load and validate config
config = load_and_validate_config()
print("Configuration loaded successfully")

# Validate environment variables
env_valid, missing = validate_environment_variables()
if not env_valid:
    print(f"Missing environment variables: {', '.join(missing)}")
else:
    print("All required environment variables are set")

# Get config summary
summary = get_config_summary(config)
print(summary)
```

## Testing

Run tests with pytest:

```bash
# Run all tests
pytest tests/test_text_utils.py -v

# Run specific test file
pytest tests/test_text_utils.py::TestNormalizeText -v

# Run with coverage
pytest tests/ --cov=utils --cov-report=html
```

## Best Practices

1. **Always use shared utilities** from `text_utils.py` instead of duplicating code
2. **Validate configuration** before using it with `load_and_validate_config()`
3. **Handle errors gracefully** - don't let exceptions crash the application
4. **Log important events** using the logging utilities
5. **Use type hints** for better IDE support and error detection
6. **Write comprehensive docstrings** following the format shown above
7. **Run linter** before committing: `pylint utils/*.py`

## Dependencies

All utils modules have minimal external dependencies:
- `python-dateutil` - Date parsing (required)
- `PyYAML` - Configuration file parsing (required)
- `openpyxl` - Excel file operations (required)
- `fuzzywuzzy` - Fuzzy string matching (optional, falls back to difflib)

Additional dependencies for specific modules:
- `sentence-transformers`, `torch`, `scikit-learn`, `numpy` - For semantic duplicate detection
- `slack-sdk`, `twilio` - For multi-channel alerts

## Notes

- All modules follow consistent error handling patterns
- Logging is done through the `logging_tools.py` module
- Retry logic with exponential backoff is available in `retry_tools.py`
- Configuration is centralized in `config.yaml` with validation in `config_validator.py`
- Type hints are added to all public functions for better IDE support
