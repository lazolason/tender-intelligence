# Duplicate and Conflict Analysis Report

**Generated:** 2026-01-08  
**Workspace:** tender-intelligence  
**Analysis Scope:** Full workspace scan for duplicate files, code blocks, resources, and conflicts

---

## Executive Summary

This report documents a comprehensive analysis of the tender-intelligence workspace to identify duplicate files, code blocks, resources, and potential conflicts. The analysis revealed multiple categories of issues that require attention to improve code maintainability and reduce technical debt.

### Key Findings

- **Backup Files:** 4 backup files identified
- **Duplicate Functions:** 7 duplicate function definitions across multiple files
- **Version Control Issues:** Multiple versions of keyword rules files
- **Configuration Conflicts:** Duplicate email settings across configuration files
- **Code Overlap:** 2 duplicate utility functions in duplicate detection modules

---

## 1. Backup Files Analysis

### 1.1 Identified Backup Files

| File | Size | Status | Recommendation |
|------|------|--------|----------------|
| `email_alerts.py.backup` | ~17 KB | Duplicate of active file | Safe to remove after verification |
| `keyword_rules_old_backup.py.backup` | ~3 KB | Old version | Safe to remove |
| `keyword_rules_v2.py.backup` | ~3 KB | V2 backup | Safe to remove |
| `keyword_rules.py.backup` | ~3 KB | Backup of active file | Safe to remove after verification |

### 1.2 Backup File Details

#### `email_alerts.py.backup`
- **Location:** Root directory
- **Active Version:** `utils/email_alerts.py`
- **Content:** Identical to active version
- **Duplicate Functions:** 5 functions duplicated
- **Risk Level:** Low (backup can be safely removed)

#### Keyword Rules Backups
- **Files:** 
  - `keyword_rules_old_backup.py.backup`
  - `keyword_rules_v2.py.backup`
  - `keyword_rules.py.backup`
- **Active Version:** `keyword_rules.py`
- **Issue:** Multiple versions of the same file exist
- **Risk Level:** Low (backups can be safely removed)

---

## 2. Duplicate Functions Analysis

### 2.1 Critical Duplicates

#### 2.1.1 `_normalize_text()` Function
**Locations:**
- `utils/duplicate_detector.py:28`
- `utils/semantic_duplicate_detector.py:56`

**Function Signature:**
```python
def _normalize_text(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r'\s+', ' ', value)
    return value
```

**Impact:** Code duplication in duplicate detection utilities  
**Recommendation:** Consolidate into a shared utility module (e.g., `utils/text_utils.py`)

---

#### 2.1.2 `_parse_date()` Function
**Locations:**
- `utils/duplicate_detector.py:52`
- `utils/semantic_duplicate_detector.py:156`
- `utils/data_validator.py` (similar implementation)

**Function Signature:**
```python
def _parse_date(value: str) -> Optional[date]:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date_parser.parse(value).date()
    except:
        return None
```

**Impact:** Date parsing logic duplicated across 3 files  
**Recommendation:** Consolidate into shared utility module

---

#### 2.1.3 Email Alert Functions (5 duplicates)

**Locations:**
- `utils/email_alerts.py` (active)
- `email_alerts.py.backup` (backup)

**Duplicate Functions:**

1. **`load_tender_payload()`**
   - `utils/email_alerts.py:456`
   - `email_alerts.py.backup:32`
   - **Purpose:** Load canonical tenders payload for dashboard
   - **Lines:** ~25 lines each

2. **`get_days_until_closing()`**
   - `utils/email_alerts.py:482`
   - `email_alerts.py.backup:53`
   - **Purpose:** Calculate days until closing date
   - **Lines:** ~10 lines each

3. **`get_urgency_text()`**
   - `utils/email_alerts.py:494`
   - `email_alerts.py.backup:64`
   - **Purpose:** Get urgency label based on days
   - **Lines:** ~15 lines each

4. **`generate_email_html()`**
   - `utils/email_alerts.py:511`
   - `email_alerts.py.backup:80`
   - **Purpose:** Generate HTML email content
   - **Lines:** ~95 lines each

5. **`send_email()`**
   - `utils/email_alerts.py:609`
   - `email_alerts.py.backup:177`
   - **Purpose:** Send email via SMTP
   - **Lines:** ~28 lines each

6. **`send_daily_digest()`**
   - `utils/email_alerts.py:639`
   - `email_alerts.py.backup:206`
   - **Purpose:** Main function to send daily digest
   - **Lines:** ~100+ lines each

**Impact:** ~275 lines of duplicate code  
**Recommendation:** Remove backup file after verification

---

### 2.2 Additional Duplicates Found

#### 2.2.1 `_within_days()` Function
**Locations:**
- `utils/duplicate_detector.py:62`
- `utils/semantic_duplicate_detector.py:168`

**Function Signature:**
```python
def _within_days(a: Optional[date], b: Optional[date], *, days: int) -> bool:
    if a is None or b is None:
        return False
    delta = abs((a - b).days)
    return delta <= days
```

**Impact:** Date comparison logic duplicated  
**Recommendation:** Consolidate into shared utility module

---

#### 2.2.2 Scraper Function Names
**Duplicate Function Names Across Files:**

| Function Name | Locations | Status |
|---------------|-----------|--------|
| `scrape_eskom()` | `scrapers/eskom.py`, `scrapers/soes.py`, `scrapers/etenders_selenium.py` | Different implementations for different sources |
| `scrape_umgeni_water()` | `scrapers/umgeni_water.py`, `scrapers/soes.py`, `scrapers/etenders_selenium.py` | Different implementations for different sources |
| `scrape_sanral()` | `scrapers/sanral.py`, `scrapers/soes.py`, `scrapers/etenders_selenium.py` | Different implementations for different sources |
| `scrape_transnet()` | `scrapers/transnet.py`, `scrapers/soes.py`, `scrapers/etenders_selenium.py` | Different implementations for different sources |

**Impact:** Naming collision but acceptable (different sources)  
**Recommendation:** Consider renaming to indicate source (e.g., `scrape_eskom_direct()`, `scrape_eskom_etenders()`)

---

## 3. Version Control Issues

### 3.1 Keyword Rules Files

**Files Identified:**
- `keyword_rules.py` (active version)
- `keyword_rules.py.backup` (backup)
- `keyword_rules_old_backup.py.backup` (old version)
- `keyword_rules_v2.py.backup` (v2 backup)

**Issue:** Multiple versions of the same file exist in the workspace  
**Impact:** Confusion about which version is current  
**Recommendation:** Remove all backup files; rely on git for version control

---

### 3.2 Email Alerts File

**Files Identified:**
- `utils/email_alerts.py` (active version)
- `email_alerts.py.backup` (backup in root)

**Issue:** Backup file in root directory instead of backups folder  
**Impact:** Clutter in workspace root  
**Recommendation:** Remove backup file; rely on git for version control

---

## 4. Configuration Conflicts

### 4.1 Email Settings Duplication

**Locations:**
- `.env.example` (environment variable template)
- `config.yaml` (YAML configuration file)

**Duplicate Settings:**

| Setting | `.env.example` | `config.yaml` |
|---------|----------------|---------------|
| SMTP Server | `SMTP_SERVER` | `email.smtp_server` |
| SMTP Port | `SMTP_PORT` | `email.smtp_port` |
| SMTP User | `SMTP_USER` | `email.smtp_user` |
| SMTP Password | `SMTP_PASSWORD` | `email.smtp_password` |
| Email From | `EMAIL_FROM` | `email.from_address` |
| Email To | `EMAIL_TO` | `email.to_addresses` |

**Impact:** Configuration ambiguity  
**Recommendation:** Standardize on one configuration method (prefer `config.yaml` for structured config, `.env` for secrets)

---

## 5. Code Quality Issues

### 5.1 Syntax Verification Results

**Python Files Analyzed:** 274 import/class/function definitions found  
**Status:** All Python files have valid syntax  
**Issues Found:** None

**JavaScript Files Analyzed:** Multiple files in `vercel-dashboard/`  
**Status:** All JavaScript files have valid syntax  
**Issues Found:** None

---

### 5.2 Coding Standards Observations

**Positive Findings:**
- Consistent use of type hints in utility functions
- Proper docstrings for functions
- Clear separation of concerns (scrapers, utils, tools)
- Use of dataclasses for structured data

**Areas for Improvement:**
- Duplicate utility functions should be consolidated
- Inconsistent import ordering across files
- Some files have long functions that could be refactored

---

## 6. JavaScript Code Analysis

### 6.1 JavaScript Files Analyzed

| File | Lines | Purpose |
|------|-------|---------|
| `vercel-dashboard/script.js` | 3500+ | Main dashboard logic |
| `vercel-dashboard/js/notifications.js` | ~200 | Notification management |
| `vercel-dashboard/js/analytics.js` | ~300 | Tender analytics |
| `vercel-dashboard/js/advanced-filters.js` | ~400 | Advanced filtering |
| `vercel-dashboard/js/pwa-diagnostics.js` | ~150 | PWA diagnostics |

**Duplicate Code Found:** None significant  
**Status:** JavaScript code is well-organized with minimal duplication

---

## 7. Risk Assessment

### 7.1 Risk Matrix

| Issue | Severity | Impact | Likelihood | Risk Level |
|-------|----------|--------|------------|------------|
| Backup files in workspace | Low | Low | High | **Low** |
| Duplicate utility functions | Medium | Medium | High | **Medium** |
| Configuration conflicts | Medium | Medium | Medium | **Medium** |
| Scraper naming collisions | Low | Low | High | **Low** |
| Version control issues | Low | Low | High | **Low** |

---

## 8. Recommendations

### 8.1 Immediate Actions (High Priority)

1. **Remove Backup Files**
   - Delete `email_alerts.py.backup`
   - Delete `keyword_rules_old_backup.py.backup`
   - Delete `keyword_rules_v2.py.backup`
   - Delete `keyword_rules.py.backup`
   - **Estimated Impact:** Remove ~26 KB of redundant files

2. **Consolidate Utility Functions**
   - Create `utils/text_utils.py` module
   - Move `_normalize_text()` to shared module
   - Move `_parse_date()` to shared module
   - Move `_within_days()` to shared module
   - Update all imports to use shared module
   - **Estimated Impact:** Remove ~50 lines of duplicate code

---

### 8.2 Medium-Term Actions (Medium Priority)

3. **Standardize Configuration**
   - Use `config.yaml` for structured configuration
   - Use `.env` only for secrets and environment-specific values
   - Update documentation to reflect configuration approach
   - **Estimated Impact:** Reduce configuration ambiguity

4. **Rename Scraper Functions**
   - Add source prefixes to duplicate function names
   - Example: `scrape_eskom_direct()` vs `scrape_eskom_etenders()`
   - **Estimated Impact:** Improve code clarity

---

### 8.3 Long-Term Actions (Low Priority)

5. **Refactor Long Functions**
   - Break down `send_daily_digest()` into smaller functions
   - Refactor `generate_email_html()` for better maintainability
   - **Estimated Impact:** Improve code maintainability

6. **Standardize Import Ordering**
   - Apply consistent import ordering across all Python files
   - Use tools like `isort` for automatic import sorting
   - **Estimated Impact:** Improve code consistency

---

## 9. Proposed Cleanup Plan

### 9.1 Phase 1: Safe Removals (No Code Changes)

**Actions:**
1. Create backup directory: `backups/[timestamp]/`
2. Copy all files to be removed to backup directory
3. Remove backup files:
   - `email_alerts.py.backup`
   - `keyword_rules_old_backup.py.backup`
   - `keyword_rules_v2.py.backup`
   - `keyword_rules.py.backup`
4. Verify workspace still functions correctly

**Risk Level:** Low  
**Rollback:** Restore from backup directory if needed

---

### 9.2 Phase 2: Code Consolidation (Requires Testing)

**Actions:**
1. Create `utils/text_utils.py` module
2. Consolidate duplicate utility functions:
   - `_normalize_text()`
   - `_parse_date()`
   - `_within_days()`
3. Update imports in affected files:
   - `utils/duplicate_detector.py`
   - `utils/semantic_duplicate_detector.py`
   - `utils/data_validator.py`
4. Run tests to verify functionality
5. Run full tender scan to ensure no regressions

**Risk Level:** Medium  
**Rollback:** Revert changes using git if issues arise

---

### 9.3 Phase 3: Configuration Standardization

**Actions:**
1. Audit all configuration usage
2. Standardize on `config.yaml` for structured config
3. Move secrets to `.env` file
4. Update documentation
5. Test all configuration-dependent features

**Risk Level:** Medium  
**Rollback:** Revert configuration changes if issues arise

---

## 10. Testing Strategy

### 10.1 Pre-Cleanup Testing

**Tests to Run:**
1. Python syntax check: `python -m py_compile *.py`
2. Import test: Import all modules to verify no circular dependencies
3. Functionality test: Run daily tender scan
4. Email test: Send test email digest
5. Dashboard test: Verify dashboard loads correctly

---

### 10.2 Post-Cleanup Testing

**Tests to Run:**
1. Repeat all pre-cleanup tests
2. Duplicate detection test: Verify duplicate detection still works
3. Email alert test: Verify email alerts still function
4. Scraper test: Run all scrapers to ensure no regressions
5. Integration test: Run full daily workflow

---

## 11. Backup Strategy

### 11.1 Pre-Cleanup Backup

**Backup Location:** `backups/[timestamp]/`

**Files to Backup:**
- All backup files (before removal)
- All files to be modified (consolidation phase)
- Configuration files
- `requirements.txt`
- `config.yaml`

**Backup Verification:**
- Verify all files copied successfully
- Create checksum for each file
- Document backup contents

---

### 11.2 Rollback Plan

**If Issues Occur:**
1. Stop any running processes
2. Restore files from backup directory
3. Verify functionality restored
4. Document issue and root cause
5. Revise cleanup plan before retry

---

## 12. Summary Statistics

### 12.1 Duplicates Found

- **Backup Files:** 4 files
- **Duplicate Functions:** 7 function definitions
- **Duplicate Code Lines:** ~325 lines
- **Configuration Conflicts:** 6 settings duplicated
- **Naming Collisions:** 4 function names (acceptable)

### 12.2 Estimated Impact

**Files to Remove:** 4 backup files (~26 KB)  
**Code to Consolidate:** ~50 lines of duplicate utility functions  
**Configuration to Standardize:** 6 settings  

**Total Risk:** Low to Medium  
**Estimated Cleanup Time:** 2-4 hours (including testing)

---

## 13. Conclusion

The tender-intelligence workspace contains several duplicate files and code blocks that can be safely removed or consolidated to improve maintainability and reduce technical debt. The most critical issues are:

1. Backup files that should be removed
2. Duplicate utility functions that should be consolidated
3. Configuration settings that should be standardized

All identified issues are low to medium risk and can be addressed with proper testing and backup procedures. The proposed cleanup plan provides a phased approach to address these issues systematically while maintaining functionality.

---

## 14. Appendix

### 14.1 File Inventory

**Python Files:** 40+ files  
**JavaScript Files:** 5+ files  
**Configuration Files:** 3 files  
**Backup Files:** 4 files  
**Total Lines of Code:** ~15,000+ lines

### 14.2 Tools Used

- File system analysis
- Regex pattern matching
- Code comparison
- Syntax verification
- Manual code review

### 14.3 Next Steps

1. Review this report with stakeholders
2. Approve cleanup plan
3. Execute Phase 1 (safe removals)
4. Execute Phase 2 (code consolidation)
5. Execute Phase 3 (configuration standardization)
6. Document all changes
7. Update project documentation

---

**Report End**
