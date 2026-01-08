# Cleanup Plan: Duplicates and Conflicts

**Created:** 2026-01-08  
**Status:** Pending Approval  
**Workspace:** tender-intelligence

---

## Executive Summary

This cleanup plan addresses duplicate files, code blocks, resources, and conflicts identified in the comprehensive analysis. The plan is organized into three phases with clear rollback procedures for each phase.

### Key Metrics

- **Files to Remove:** 4 backup files (~26 KB)
- **Code to Consolidate:** ~50 lines of duplicate utility functions
- **Configuration to Standardize:** 6 settings
- **Total Risk Level:** Low to Medium
- **Estimated Time:** 2-4 hours (including testing)

---

## Phase 1: Safe Removals (No Code Changes)

### Overview

Remove backup files that are no longer needed. This phase has zero risk to functionality as these files are not referenced by any active code.

### Files to Remove

| File | Size | Status | Action |
|------|------|--------|--------|
| `email_alerts.py.backup` | ~17 KB | Duplicate of [`utils/email_alerts.py`](utils/email_alerts.py) | Delete |
| `keyword_rules_old_backup.py.backup` | ~3 KB | Old version | Delete |
| `keyword_rules_v2.py.backup` | ~3 KB | V2 backup | Delete |
| `keyword_rules.py.backup` | ~3 KB | Duplicate of [`keyword_rules.py`](keyword_rules.py) | Delete |

**Total:** 4 files, ~26 KB

### Pre-Removal Checklist

- [ ] Backup directory created: `backups/[timestamp]/`
- [ ] All 4 files copied to backup directory
- [ ] Manifest generated with file hashes
- [ ] Backup integrity verified
- [ ] No active code references these files (verified via grep)

### Removal Commands

```bash
# Set backup directory
BACKUP_DIR="backups/2026-01-08_17-21-00"

# Verify backup exists
if [ ! -d "$BACKUP_DIR" ]; then
  echo "ERROR: Backup directory not found: $BACKUP_DIR"
  exit 1
fi

# Remove backup files
rm email_alerts.py.backup
rm keyword_rules_old_backup.py.backup
rm keyword_rules_v2.py.backup
rm keyword_rules.py.backup

echo "✓ Backup files removed successfully"
```

### Verification Commands

```bash
# Verify files were removed
if [ ! -f "email_alerts.py.backup" ] && \
   [ ! -f "keyword_rules_old_backup.py.backup" ] && \
   [ ! -f "keyword_rules_v2.py.backup" ] && \
   [ ! -f "keyword_rules.py.backup" ]; then
  echo "✓ All backup files removed"
else
  echo "✗ Some files still exist"
fi

# Verify workspace still functions
python -c "import tenderscan; print('✓ Import successful')"
```

### Rollback Procedure

```bash
# Restore from backup
BACKUP_DIR="backups/2026-01-08_17-21-00"
cp "$BACKUP_DIR/email_alerts.py.backup" .
cp "$BACKUP_DIR/keyword_rules_old_backup.py.backup" .
cp "$BACKUP_DIR/keyword_rules_v2.py.backup" .
cp "$BACKUP_DIR/keyword_rules.py.backup" .
echo "✓ Backup files restored"
```

### Risk Assessment

- **Severity:** Low
- **Impact:** None (files not referenced by active code)
- **Likelihood:** 0% (no code dependencies)
- **Risk Level:** **Low**

---

## Phase 2: Code Consolidation (Requires Testing)

### Overview

Consolidate duplicate utility functions into a shared module to eliminate code duplication and improve maintainability.

### Duplicate Functions to Consolidate

| Function | Locations | Lines | Action |
|----------|-----------|-------|--------|
| `_normalize_text()` | [`utils/duplicate_detector.py:28`](utils/duplicate_detector.py:28), [`utils/semantic_duplicate_detector.py:56`](utils/semantic_duplicate_detector.py:56) | ~8 | Move to shared module |
| `_parse_date()` | [`utils/duplicate_detector.py:52`](utils/duplicate_detector.py:52), [`utils/semantic_duplicate_detector.py:156`](utils/semantic_duplicate_detector.py:156), [`utils/data_validator.py`](utils/data_validator.py) | ~12 | Move to shared module |
| `_within_days()` | [`utils/duplicate_detector.py:62`](utils/duplicate_detector.py:62), [`utils/semantic_duplicate_detector.py:168`](utils/semantic_duplicate_detector.py:168) | ~6 | Move to shared module |

**Total:** 3 functions, ~26 lines of duplicate code

### Step 2.1: Create Shared Utility Module

Create new file: [`utils/text_utils.py`](utils/text_utils.py)

```python
"""
Shared text and date utility functions.

This module consolidates common utility functions used across
duplicate detection, validation, and other modules.
"""

import re
from datetime import date
from typing import Optional
from dateutil import parser as date_parser


def normalize_text(value: str) -> str:
    """
    Normalize text for comparison.
    
    Args:
        value: Text to normalize
        
    Returns:
        Normalized text (lowercase, stripped, single spaces)
    """
    value = (value or "").strip().lower()
    value = re.sub(r'\s+', ' ', value)
    return value


def parse_date(value: str) -> Optional[date]:
    """
    Parse date string to date object.
    
    Args:
        value: Date string to parse
        
    Returns:
        Date object or None if parsing fails
    """
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date_parser.parse(value).date()
    except:
        return None


def within_days(a: Optional[date], b: Optional[date], *, days: int) -> bool:
    """
    Check if two dates are within specified days of each other.
    
    Args:
        a: First date
        b: Second date
        days: Maximum days difference
        
    Returns:
        True if dates are within specified days, False otherwise
    """
    if a is None or b is None:
        return False
    delta = abs((a - b).days)
    return delta <= days
```

### Step 2.2: Update Imports in Affected Files

#### File: [`utils/duplicate_detector.py`](utils/duplicate_detector.py)

**Changes:**
1. Remove `_normalize_text()` function (lines 28-34)
2. Remove `_parse_date()` function (lines 52-60)
3. Remove `_within_days()` function (lines 62-66)
4. Add import: `from utils.text_utils import normalize_text, parse_date, within_days`
5. Update function calls:
   - `_normalize_text()` → `normalize_text()`
   - `_parse_date()` → `parse_date()`
   - `_within_days()` → `within_days()`

#### File: [`utils/semantic_duplicate_detector.py`](utils/semantic_duplicate_detector.py)

**Changes:**
1. Remove `_normalize_text()` function (lines 56-62)
2. Remove `_parse_date()` function (lines 156-164)
3. Remove `_within_days()` function (lines 168-173)
4. Add import: `from utils.text_utils import normalize_text, parse_date, within_days`
5. Update function calls:
   - `_normalize_text()` → `normalize_text()`
   - `_parse_date()` → `parse_date()`
   - `_within_days()` → `within_days()`

#### File: [`utils/data_validator.py`](utils/data_validator.py)

**Changes:**
1. Add import: `from utils.text_utils import parse_date`
2. Update date parsing to use `parse_date()` instead of local implementation
3. Remove local `_parse_date()` function if it exists

### Step 2.3: Testing Commands

```bash
# Test imports
python -c "from utils.text_utils import normalize_text, parse_date, within_days; print('✓ Imports successful')"

# Test normalize_text
python -c "from utils.text_utils import normalize_text; assert normalize_text('  HELLO  WORLD  ') == 'hello world'; print('✓ normalize_text works')"

# Test parse_date
python -c "from utils.text_utils import parse_date; from datetime import date; assert parse_date('2024-01-01') == date(2024, 1, 1); print('✓ parse_date works')"

# Test within_days
python -c "from utils.text_utils import within_days; from datetime import date; assert within_days(date(2024, 1, 1), date(2024, 1, 3), days=3) == True; print('✓ within_days works')"

# Test duplicate_detector
python -c "from utils.duplicate_detector import find_duplicate; print('✓ duplicate_detector imports successfully')"

# Test semantic_duplicate_detector
python -c "from utils.semantic_duplicate_detector import find_semantic_duplicate; print('✓ semantic_duplicate_detector imports successfully')"

# Test data_validator
python -c "from utils.data_validator import TenderValidator; print('✓ data_validator imports successfully')"
```

### Step 2.4: Integration Testing

```bash
# Run full tender scan
python daily_runner.py

# Verify duplicate detection works
python -c "
from utils.duplicate_detector import find_duplicate
tender1 = {'ref': 'REF001', 'title': 'Test Tender', 'closing_date': '2024-01-01'}
tender2 = {'ref': 'REF002', 'title': 'Test Tender', 'closing_date': '2024-01-02'}
result = find_duplicate(tender1, [tender2])
print(f'Duplicate detection result: {result.is_duplicate}')
"

# Verify email alerts work
python -c "
from utils.email_alerts import send_daily_digest
print('✓ Email alerts module imports successfully')
"
```

### Rollback Procedure

```bash
# Restore from backup
BACKUP_DIR="backups/2026-01-08_17-21-00"

# Restore modified files
cp "$BACKUP_DIR/utils/duplicate_detector.py" utils/
cp "$BACKUP_DIR/utils/semantic_duplicate_detector.py" utils/
cp "$BACKUP_DIR/utils/data_validator.py" utils/

# Remove new shared module
rm utils/text_utils.py

echo "✓ Files restored to previous state"
```

### Risk Assessment

- **Severity:** Medium
- **Impact:** Medium (code changes affect multiple modules)
- **Likelihood:** 20% (potential import or function call issues)
- **Risk Level:** **Medium**

---

## Phase 3: Configuration Standardization

### Overview

Standardize configuration approach to eliminate ambiguity between `.env` and `config.yaml` files.

### Current State

| Setting | `.env.example` | `config.yaml` | Issue |
|---------|----------------|---------------|-------|
| SMTP Server | `SMTP_SERVER` | `email.smtp_server` | Duplicate |
| SMTP Port | `SMTP_PORT` | `email.smtp_port` | Duplicate |
| SMTP User | `SMTP_USER` | `email.smtp_user` | Duplicate |
| SMTP Password | `SMTP_PASSWORD` | `email.smtp_password` | Duplicate |
| Email From | `EMAIL_FROM` | `email.from_address` | Duplicate |
| Email To | `EMAIL_TO` | `email.to_addresses` | Duplicate |

### Proposed Standardization

**Approach:** Use `config.yaml` for structured configuration, `.env` only for secrets

#### File: [`config.yaml`](config.yaml)

```yaml
# Email Configuration
email:
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  smtp_use_tls: true
  from_address: "tenderscan@example.com"
  to_addresses:
    - "recipient1@example.com"
    - "recipient2@example.com"
  # Secrets loaded from environment variables
  smtp_user: ${SMTP_USER}
  smtp_password: ${SMTP_PASSWORD}
```

#### File: [`.env.example`](.env.example)

```bash
# Email Configuration Secrets
# SMTP credentials (required)
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Optional: Override config.yaml settings
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# EMAIL_FROM=tenderscan@example.com
# EMAIL_TO=recipient1@example.com,recipient2@example.com
```

### Step 3.1: Update Configuration Files

#### Changes to [`config.yaml`](config.yaml):

1. Keep all structured configuration in `config.yaml`
2. Replace hardcoded values with environment variable references for secrets
3. Add comments explaining which values come from `.env`

#### Changes to [`.env.example`](.env.example):

1. Remove duplicate settings that are in `config.yaml`
2. Keep only secrets and environment-specific values
3. Add comments explaining configuration hierarchy

### Step 3.2: Update Code to Load Configuration

#### File: [`utils/email_alerts.py`](utils/email_alerts.py)

**Changes:**
1. Update `EmailAlerter.__init__()` to load from `config.yaml`
2. Use environment variables for secrets
3. Remove hardcoded values

```python
import yaml
import os
from pathlib import Path

class EmailAlerter:
    def __init__(self, config_path="config.yaml"):
        # Load config from YAML
        config_file = Path(config_path)
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        email_config = config.get('email', {})
        
        # Load settings from config
        self.smtp_server = os.getenv('SMTP_SERVER', email_config.get('smtp_server'))
        self.smtp_port = int(os.getenv('SMTP_PORT', email_config.get('smtp_port', 587)))
        self.smtp_use_tls = email_config.get('smtp_use_tls', True)
        self.from_address = os.getenv('EMAIL_FROM', email_config.get('from_address'))
        
        # Load secrets from environment
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        
        # Load recipients
        to_env = os.getenv('EMAIL_TO')
        if to_env:
            self.to_addresses = [addr.strip() for addr in to_env.split(',')]
        else:
            self.to_addresses = email_config.get('to_addresses', [])
```

### Step 3.3: Testing Commands

```bash
# Test configuration loading
python -c "
import yaml
from pathlib import Path
config_file = Path('config.yaml')
with open(config_file, 'r') as f:
    config = yaml.safe_load(f)
print(f'✓ Config loaded: {config.get(\"email\", {}).get(\"smtp_server\")}')
"

# Test email alerter initialization
python -c "
from utils.email_alerts import EmailAlerter
alerter = EmailAlerter()
print(f'✓ EmailAlerter initialized: SMTP server={alerter.smtp_server}')
"

# Test email sending (with test credentials)
python -c "
from utils.email_alerts import EmailAlerter
alerter = EmailAlerter()
# alerter.send_test_email()  # Uncomment to test
print('✓ EmailAlerter ready to send emails')
"
```

### Rollback Procedure

```bash
# Restore from backup
BACKUP_DIR="backups/2026-01-08_17-21-00"

# Restore configuration files
cp "$BACKUP_DIR/config.yaml" .
cp "$BACKUP_DIR/.env.example" .

# Restore email alerts module
cp "$BACKUP_DIR/utils/email_alerts.py" utils/

echo "✓ Configuration files restored"
```

### Risk Assessment

- **Severity:** Medium
- **Impact:** Medium (affects email functionality)
- **Likelihood:** 15% (potential configuration loading issues)
- **Risk Level:** **Medium**

---

## Testing Strategy

### Pre-Cleanup Testing

Run these tests before any cleanup:

```bash
# 1. Python syntax check
python -m py_compile *.py scrapers/*.py utils/*.py tools/*.py

# 2. Import test
python -c "
import tenderscan
import daily_runner
from utils.email_alerts import EmailAlerter
from utils.duplicate_detector import find_duplicate
from utils.semantic_duplicate_detector import find_semantic_duplicate
print('✓ All imports successful')
"

# 3. Functionality test
python daily_runner.py

# 4. Email test
python -c "
from utils.email_alerts import send_daily_digest
print('✓ Email module ready')
"

# 5. Dashboard test
python app.py &
sleep 2
curl http://localhost:5000/health
pkill -f "python app.py"
```

### Post-Cleanup Testing

Run these tests after each phase:

#### After Phase 1:
```bash
# Verify files removed
ls *.backup 2>/dev/null || echo "✓ No backup files found"

# Verify imports still work
python -c "import tenderscan; print('✓ Imports work')"
```

#### After Phase 2:
```bash
# Test new shared module
python -c "
from utils.text_utils import normalize_text, parse_date, within_days
print('✓ Shared module works')
"

# Test updated modules
python -c "
from utils.duplicate_detector import find_duplicate
from utils.semantic_duplicate_detector import find_semantic_duplicate
from utils.data_validator import TenderValidator
print('✓ Updated modules work')
"

# Run full scan
python daily_runner.py
```

#### After Phase 3:
```bash
# Test configuration loading
python -c "
from utils.email_alerts import EmailAlerter
alerter = EmailAlerter()
print(f'✓ EmailAlerter: {alerter.smtp_server}')
"

# Test email sending
python -c "
from utils.email_alerts import send_daily_digest
print('✓ Email module works')
"

# Run full workflow
python daily_runner.py
```

---

## Execution Timeline

| Phase | Duration | Dependencies | Risk Level |
|-------|----------|--------------|------------|
| Phase 1: Safe Removals | 15 minutes | None | Low |
| Phase 2: Code Consolidation | 1-2 hours | Phase 1 complete | Medium |
| Phase 3: Configuration Standardization | 1 hour | Phase 2 complete | Medium |
| Testing & Verification | 1 hour | All phases complete | Low |

**Total Estimated Time:** 2-4 hours

---

## Rollback Strategy

### Rollback Triggers

Rollback should be triggered if:

1. Import errors occur after code changes
2. Tests fail after cleanup
3. Email functionality breaks
4. Duplicate detection stops working
5. Any unexpected behavior in daily workflow

### Rollback Priority

1. **Critical Rollback:** Phase 2 (Code Consolidation) - affects core functionality
2. **Medium Rollback:** Phase 3 (Configuration) - affects email functionality
3. **Low Rollback:** Phase 1 (Safe Removals) - minimal impact

### Rollback Procedure

```bash
# Stop all running processes
pkill -f "python.*tenderscan"
pkill -f "python.*daily_runner"
pkill -f "flask"

# Set backup directory
BACKUP_DIR="backups/2026-01-08_17-21-00"

# Restore all modified files
cp "$BACKUP_DIR/utils/email_alerts.py" utils/
cp "$BACKUP_DIR/utils/duplicate_detector.py" utils/
cp "$BACKUP_DIR/utils/semantic_duplicate_detector.py" utils/
cp "$BACKUP_DIR/utils/data_validator.py" utils/
cp "$BACKUP_DIR/config.yaml" .
cp "$BACKUP_DIR/.env.example" .

# Restore backup files if needed
cp "$BACKUP_DIR/email_alerts.py.backup" .
cp "$BACKUP_DIR/keyword_rules_old_backup.py.backup" .
cp "$BACKUP_DIR/keyword_rules_v2.py.backup" .
cp "$BACKUP_DIR/keyword_rules.py.backup" .

# Remove new files created during cleanup
rm utils/text_utils.py 2>/dev/null || true

echo "✓ Rollback complete"
```

---

## Success Criteria

Cleanup is considered successful when:

1. ✅ All backup files are removed
2. ✅ Duplicate utility functions consolidated into shared module
3. ✅ Configuration standardized between `.env` and `config.yaml`
4. ✅ All imports work without errors
5. ✅ All tests pass
6. ✅ Daily workflow runs successfully
7. ✅ Email alerts function correctly
8. ✅ Duplicate detection works as expected
9. ✅ No regressions in functionality
10. ✅ Code is more maintainable

---

## Documentation Updates

After successful cleanup, update:

1. **README.md** - Document new shared module
2. **config.yaml** - Add comments about configuration hierarchy
3. **.env.example** - Update with clear documentation
4. **utils/README.md** - Document text_utils.py module
5. **DEPLOYMENT.md** - Update configuration instructions

---

## Approval Required

Before executing this cleanup plan, approval is needed from:

- [ ] Project Lead
- [ ] Development Team
- [ ] Operations Team

**Approved By:** __________________________  
**Date:** __________________________  
**Signature:** __________________________

---

## Appendix

### A. File Changes Summary

| Phase | Files Modified | Files Created | Files Deleted |
|-------|----------------|---------------|---------------|
| Phase 1 | 0 | 0 | 4 |
| Phase 2 | 3 | 1 | 0 |
| Phase 3 | 2 | 0 | 0 |
| **Total** | **5** | **1** | **4** |

### B. Code Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Total Files | 40+ | 37+ | -4 |
| Lines of Code | ~15,000 | ~14,950 | -50 |
| Duplicate Functions | 7 | 0 | -7 |
| Configuration Files | 2 | 2 | 0 |

### C. Risk Matrix

| Phase | Severity | Impact | Likelihood | Risk Level |
|-------|----------|--------|------------|------------|
| Phase 1 | Low | Low | 0% | Low |
| Phase 2 | Medium | Medium | 20% | Medium |
| Phase 3 | Medium | Medium | 15% | Medium |

---

## Conclusion

This cleanup plan provides a systematic approach to removing duplicates and conflicts from the tender-intelligence workspace. The phased approach with clear rollback procedures ensures minimal risk while improving code maintainability and reducing technical debt.

**Recommendation:** Proceed with Phase 1 immediately (low risk), then evaluate Phase 2 and Phase 3 based on Phase 1 results and stakeholder feedback.

---

**Document End**
