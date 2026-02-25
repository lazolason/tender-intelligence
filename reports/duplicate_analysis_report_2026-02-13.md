# Duplicate and Conflict Analysis Report - February 2026

**Generated:** 2026-02-13  
**Workspace:** tender-intelligence  
**Analysis Scope:** Full workspace scan for duplicate files, code blocks, resources, and conflicts

---

## Executive Summary

This report provides an updated analysis of the tender-intelligence workspace, building upon the January 2026 analysis. Several issues from the previous report have been resolved, but new duplicates and conflicts have been identified.

### Key Findings Summary

| Category | Status | Count |
|----------|--------|-------|
| Previously Identified Backup Files | ✅ Resolved | 4 files removed |
| Code Consolidation (Phase 2) | ✅ Completed | `utils/text_utils.py` created |
| Duplicate JSON Data Files | ⚠️ New Issue | 5 files |
| JavaScript Class Duplicates | ⚠️ New Issue | 2 files |
| Scraper Naming Collisions | ⚠️ Ongoing | 4 functions |
| Test File Versioning Issues | ⚠️ New Issue | 6 files |
| Excel Backup Files | ⚠️ New Issue | 1 file |

---

## 1. Previously Resolved Issues

### 1.1 Backup Files Removed
The following backup files from the January 2026 report have been successfully removed:
- ~~`email_alerts.py.backup`~~ - Removed
- ~~`keyword_rules_old_backup.py.backup`~~ - Removed
- ~~`keyword_rules_v2.py.backup`~~ - Removed
- ~~`keyword_rules.py.backup`~~ - Removed

### 1.2 Code Consolidation Completed
The shared utility module [`utils/text_utils.py`](utils/text_utils.py) has been created and is now imported by:
- [`utils/duplicate_detector.py:5`](utils/duplicate_detector.py:5)
- [`utils/semantic_duplicate_detector.py:11`](utils/semantic_duplicate_detector.py:11)

Tests for the new module exist at [`tests/test_text_utils.py`](tests/test_text_utils.py).

---

## 2. New Duplicate Files Identified

### 2.1 Duplicate JSON Data Files

**Issue:** Three identical JSON files with the same content exist in the dashboard public directory.

| File | Size | Content Hash | Status |
|------|------|--------------|--------|
| [`dashboard/public/tenders-latest.json`](dashboard/public/tenders-latest.json) | 2,138 chars | Identical | Keep (primary) |
| [`dashboard/public/build/tenders.json`](dashboard/public/build/tenders.json) | 2,138 chars | Identical | Duplicate |
| [`dashboard/public/tenders-2026-01-22.json`](dashboard/public/tenders-2026-01-22.json) | 2,138 chars | Identical | Date-stamped backup |

**Recommendation:** 
- Keep `tenders-latest.json` as the primary data source
- Keep `build/tenders.json` if required for deployment/build process
- Remove `tenders-2026-01-22.json` (date-stamped backup - use git for version history)

### 2.2 Duplicate Summary JSON Files

**Issue:** Two identical summary files exist.

| File | Size | Content Hash | Status |
|------|------|--------------|--------|
| [`dashboard/public/summary.json`](dashboard/public/summary.json) | 1,123 chars | Identical | Keep (primary) |
| [`dashboard/public/build/summary.json`](dashboard/public/build/summary.json) | 1,123 chars | Identical | Keep if needed for build |

**Recommendation:** Keep both if `build/` directory is used for deployment; otherwise consolidate.

---

## 3. JavaScript Code Duplicates

### 3.1 TenderAnalytics Class Duplication

**Issue:** The `TenderAnalytics` class is defined in two locations with different implementations.

#### Location 1: [`dashboard/js/analytics.js`](dashboard/js/analytics.js)
- **Type:** Standalone class, exported to `window.TenderAnalytics`
- **Lines:** 248 lines
- **Usage:** Legacy inline script loading

```javascript
// dashboard/js/analytics.js:247-248
// Export for use in main script
window.TenderAnalytics = TenderAnalytics;
```

#### Location 2: [`dashboard/js/modules/analytics.js`](dashboard/js/modules/analytics.js)
- **Type:** ES6 module export
- **Lines:** ~400+ lines (larger implementation)
- **Usage:** Modern modular architecture

```javascript
// dashboard/js/modules/analytics.js:11
export class TenderAnalytics {
```

**Key Differences:**
| Feature | `js/analytics.js` | `js/modules/analytics.js` |
|---------|-------------------|---------------------------|
| Export Type | `window.TenderAnalytics` | ES6 `export class` |
| Dependencies | None | Imports from `config.js`, `helpers.js` |
| ISO Week Calculation | `getWeekNumber()` | Static `getISOWeek()` |
| Dependencies | Self-contained | Module imports |

**Recommendation:**
1. Determine which version is actively used in [`dashboard/index.html`](dashboard/index.html)
2. If modular version is used, remove `js/analytics.js`
3. If inline version is used, document why modular version exists

---

## 4. Scraper Naming Collisions

### 4.1 Functions with Same Names Across Files

**Issue:** Multiple scraper functions have identical names but different implementations.

| Function Name | File 1 | File 2 | Status |
|---------------|--------|--------|--------|
| `scrape_transnet()` | [`scrapers/transnet.py:21`](scrapers/transnet.py:21) | [`scrapers/soes.py:280`](scrapers/soes.py:280) | Different implementations |
| `scrape_eskom()` | [`scrapers/eskom.py:28`](scrapers/eskom.py:28) | [`scrapers/soes.py:343`](scrapers/soes.py:343) | Different implementations |
| `scrape_joburg_water_selenium()` | [`scrapers/joburg_water_selenium.py:19`](scrapers/joburg_water_selenium.py:19) | [`scrapers/soes.py:28`](scrapers/soes.py:28) | Fallback stub in soes.py |

**Analysis:**
- `scrapers/soes.py` appears to aggregate multiple SOE scrapers
- Individual scraper files (`transnet.py`, `eskom.py`) have specialized implementations
- The naming collision is intentional but could cause confusion

**Recommendation:**
1. Add source prefixes to function names for clarity:
   - `scrape_transnet()` → `scrape_transnet_direct()` in `transnet.py`
   - `scrape_eskom()` → `scrape_eskom_etenders()` in `eskom.py`
2. Or document in docstrings which file should be used as primary source

---

## 5. Test File Versioning Issues

### 5.1 Multiple Test Versions in Execution Directory

**Issue:** The [`dashboard/execution/`](dashboard/execution/) directory contains multiple versions of test files.

| File Pattern | Files | Purpose |
|--------------|-------|---------|
| `test_excel_sync*.py` | 4 files | Excel synchronization tests |
| `live_audit*.py` | 2 files | Live audit scripts |

**Files Identified:**
```
dashboard/execution/
├── test_excel_sync.py      # Original
├── test_excel_sync_v2.py   # Version 2
├── test_excel_sync_v3.py   # Version 3
├── test_excel_sync_v4.py   # Version 4 (latest?)
├── live_audit.py           # Original
└── live_audit_v2.py        # Version 2
```

**Recommendation:**
1. Identify the current/active version of each test
2. Archive or remove obsolete versions
3. Use git for version control instead of file naming

---

## 6. Excel Backup Files

### 6.1 Tender Dashboard Backup

**Issue:** An Excel backup file exists in the Tender Log directory.

| File | Size | Status |
|------|------|--------|
| [`01_Tender_Log/Tender_Dashboard_v2.xlsx`](01_Tender_Log/Tender_Dashboard_v2.xlsx) | 8,428 chars | Active file |
| [`01_Tender_Log/Tender_Dashboard_v2_backup_20260124_194121.xlsx`](01_Tender_Log/Tender_Dashboard_v2_backup_20260124_194121.xlsx) | 8,428 chars | Backup |

**Recommendation:** 
- Move backup files to a dedicated `backups/` directory
- Or rely on git/time-machine for backups
- Document backup retention policy

---

## 7. Configuration Status

### 7.1 Configuration Hierarchy

The configuration has been properly standardized since the January 2026 report:

| File | Purpose | Status |
|------|---------|--------|
| [`config.yaml`](config.yaml) | Main configuration | ✅ Properly structured |
| [`.env.example`](.env.example) | Environment secrets template | ✅ Documented hierarchy |

**Configuration is now properly separated:**
- `config.yaml` contains structured settings
- `.env` contains secrets (SMTP credentials, API keys)
- `.env.example` documents the expected environment variables

---

## 8. Risk Assessment

### 8.1 Risk Matrix

| Issue | Severity | Impact | Likelihood | Risk Level |
|-------|----------|--------|------------|------------|
| Duplicate JSON files | Low | Low | High | **Low** |
| JavaScript class duplicates | Medium | Medium | Medium | **Medium** |
| Scraper naming collisions | Low | Low | High | **Low** |
| Test file versioning | Low | Low | Medium | **Low** |
| Excel backup files | Low | Low | Low | **Low** |

---

## 9. Proposed Cleanup Actions

### Phase 1: Safe Removals (No Code Changes)

| Action | Files Affected | Risk |
|--------|----------------|------|
| Remove date-stamped JSON backup | `dashboard/public/tenders-2026-01-22.json` | Low |
| Archive old test versions | `dashboard/execution/test_excel_sync.py`, `test_excel_sync_v2.py`, `test_excel_sync_v3.py` | Low |
| Archive old audit versions | `dashboard/execution/live_audit.py` | Low |
| Move Excel backup | `01_Tender_Log/Tender_Dashboard_v2_backup_20260124_194121.xlsx` | Low |

### Phase 2: Code Analysis Required

| Action | Files Affected | Risk |
|--------|----------------|------|
| Determine active TenderAnalytics version | `dashboard/js/analytics.js`, `dashboard/js/modules/analytics.js` | Medium |
| Consolidate or document scraper functions | `scrapers/*.py` | Medium |

---

## 10. Backup Strategy

### Pre-Cleanup Backup

**Backup Location:** `backups/2026-02-13_[timestamp]/`

**Files to Backup:**
1. All files marked for removal
2. All files marked for archival
3. Configuration files
4. Test files

**Backup Verification:**
- Generate checksums for all files
- Create manifest with file details
- Verify backup integrity

---

## 11. Testing Strategy

### Pre-Cleanup Tests

```bash
# Python syntax check
python -m py_compile *.py scrapers/*.py utils/*.py tools/*.py

# Import tests
python -c "import tenderscan; from utils.text_utils import normalize_text; print('OK')"

# Run existing tests
python -m pytest tests/ -v
```

### Post-Cleanup Tests

```bash
# Verify dashboard loads
python app.py &
curl http://localhost:5000/health

# Verify scrapers work
python -c "from scrapers.soes import scrape_all_soes; print('OK')"
```

---

## 12. Summary Statistics

### Current State

| Metric | Count |
|--------|-------|
| Duplicate JSON files | 5 |
| Duplicate JavaScript classes | 2 |
| Scraper naming collisions | 4 |
| Test file versions | 6 |
| Excel backup files | 1 |

### Estimated Impact

- **Files to Remove:** 4-6 files
- **Files to Archive:** 4-5 files
- **Code to Analyze:** 2 JavaScript files
- **Total Risk:** Low to Medium

---

## 13. Conclusion

The tender-intelligence workspace has improved since the January 2026 analysis. The Phase 2 code consolidation has been completed successfully with the creation of `utils/text_utils.py`. However, new duplicates have emerged:

1. **JSON data files** - Multiple identical copies exist, likely from different build/deploy processes
2. **JavaScript modules** - Two versions of TenderAnalytics exist for different loading patterns
3. **Test file versions** - Multiple versions of test files suggest iterative development without cleanup
4. **Scraper naming** - Intentional naming collisions could cause confusion

All identified issues are low to medium risk and can be addressed systematically with proper backup procedures.

---

## 14. Next Steps

1. **User Approval:** Review this report and approve proposed cleanup actions
2. **Create Backup:** Backup all affected files before any changes
3. **Execute Phase 1:** Remove/archive safe files
4. **Analyze Phase 2:** Determine active code versions
5. **Run Tests:** Verify functionality after changes
6. **Document Changes:** Update documentation to reflect cleanup

---

*Report generated by workspace analysis on 2026-02-13*
