# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

The Tender Intelligence System is an automated tender aggregation and prioritization platform for two South African companies (TES and Phakathi). It follows a pipeline architecture:

```
[Web Scrapers] → [Validation] → [Classification] → [Scoring Engine] → [Excel Logger] → [Dashboard] → [Alerts]
```

**Key Components:**
- **11 active scrapers** covering municipalities, SOEs, utilities, and mining companies
- **Rule-based classification engine** matching tenders to company capabilities
- **Multi-dimensional scoring engine** (fit, industry, risk, revenue, suitability)
- **Unified architecture** (Flask API backend + Vercel static PWA frontend)
- **File-based storage** using Excel as primary data store

## Development Commands

### Environment Setup

```bash
# Create and activate virtual environment (Python 3.11+)
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt

# Setup Chromedriver (REQUIRED for Selenium scrapers)
python tools/setup_chromedriver.py
```

### Running the System

```bash
# Run full tender scan (all scrapers + classification + scoring)
python tenderscan.py

# Run daily automation (includes log rotation, health monitoring, email alerts)
python daily_runner.py

# Generate weekly report (HTML dashboard with stats)
python weekly_report.py

# Sync dashboard to Vercel (generates HTML + pushes to GitHub)
python sync_to_vercel.py

# Run single scraper for testing
python -c "from scrapers.municipalities import scrape_ekurhuleni; print(scrape_ekurhuleni())"
```

### Dashboard Commands

**Unified Architecture**: Flask API (backend only) + Vercel PWA (frontend only)

```bash
# Run Flask API server - API endpoints only (http://localhost:5000)
python app.py

# Run Vercel dashboard locally - Static PWA (http://localhost:8000)
cd vercel-dashboard
python3 -m http.server 8000
# No npm dependencies required - pure static files
```

### Utility Commands

```bash
# Import CSV tenders to Excel
python import_csv.py path/to/tenders.csv

# Reclassify existing tenders (after keyword rule changes)
python reclassify_existing.py

# Test exclusion keywords
python test_exclusions.py

# Validate dashboard JSON schema
python tools/validate_dashboard_tenders_json.py

# Check Chromedriver version alignment
python tools/preflight_check.py

# Diagnose PWA installation issues
python tools/pwa_diagnostics.py
```

### Testing Individual Components

```bash
# Test scoring engine
python scoring_engine.py

# Test classification engine
python classify_engine.py

# Test keyword rules
python keyword_rules.py
```

## Architecture and Data Flow

### Pipeline Components

**1. Scraper Layer** (`scrapers/`)
- **Static HTML scrapers**: BeautifulSoup-based for most sources
  - `municipalities.py`: Ekurhuleni, Tshwane, Cape Town, eThekwini
  - `soes.py`: Rand Water, Eskom, Transnet, SANRAL
  - `umgeni_water.py`, `sanral.py`, `transnet.py`: Specialized scrapers
- **Selenium scrapers** (dynamic sites, can be disabled):
  - `national_treasury_selenium.py`: eTenders portal with search
  - `joburg_water_selenium.py`: Johannesburg Water tenders
  - `eskom_direct.py`: Eskom direct procurement portal
- **Base class pattern**: `BaseMunicipalityScraper` ensures consistency
- **Error handling**: Failed scrapers return empty arrays, don't crash pipeline

**2. Data Validation** (`utils/data_validator.py`)
- Required fields: `title`, `source`
- Optional fields with warnings: `ref`, `closing_date`, `client`
- Invalid tenders logged but don't block pipeline

**3. Classification Engine** (`classify_engine.py`)
- **Three keyword sets**:
  - `TES_KEYWORDS`: Water treatment, dosing, cooling towers, boiler treatment
  - `PHAKATHI_KEYWORDS`: Pumps, fabrication, bearings, switchgear, mechanical
  - `EXCLUDE_KEYWORDS`: Construction, security, maintenance (out of scope)
- **Override mechanism**: Strong signals bypass exclusions
- **BOTH category**: Tenders matching both companies
- **Short title generation**: For folder naming (30 chars max)

**4. Scoring Engine** (`scoring_engine.py`)
- **Five-dimensional composite score (1-10)**:
  - **Fit Score (30%)**: Capability alignment with company specialization
  - **Industry Score (20%)**: Client industry value (power=10, mining=9, municipal=7)
  - **Risk Score (15%)**: Entry barriers, deadlines, requirements
  - **Revenue Score (20%)**: Estimated contract value and duration
  - **Suitability Score (15%)**: TES vs Phakathi specific fit
- **Priority levels**: HIGH ≥7, MEDIUM ≥5, LOW <5
- **Actionable recommendations**: Next steps and win probability

**5. Excel Logger** (`utils/excel_writer.py`)
- Primary data store: `Tender_Dashboard_v2.xlsx`
- **Duplicate detection**: Fuzzy matching (85% similarity) + exact ref matching
- **Caching**: In-memory caches for refs and tender metadata (resets each run)
- **Color coding**: RED=HIGH, YELLOW=MEDIUM, GREEN=LOW priority

**6. Dashboard Generator** (`sync_to_vercel.py`)
- **Dual deployment**:
  - Embedded data in HTML (fast initial load)
  - Separate `tenders.json` (full dataset for filtering)
- **Git automation**: Commits + pushes to GitHub (triggers Vercel deploy)
- **PWA features**: Offline support via service worker

### Data Storage Structure

**File-Based Storage (no database)**:
```
MASTER/TENDERS/
├── 01_Tender_Log/
│   └── Tender_Dashboard_v2.xlsx     # Primary data store
├── 02_Active_Tenders/
│   └── REF-CLIENT-SHORT_TITLE/      # Folders per tender
└── 00_System/04_Automation/
    ├── output/
    │   ├── new_tenders.json         # Dashboard snapshot (200 tenders)
    │   ├── scraper_health.json      # Reliability metrics
    │   ├── scraper_metrics.json     # Detailed run history
    │   └── daily_email.html         # Email backup
    ├── logs/
    │   └── scraper.log              # Rotating log file
    └── reports/
        └── weekly_report_YYYYMMDD.html
```

**Vercel Dashboard** (`vercel-dashboard/`):
- `index.html`: Generated dashboard with embedded data
- `tenders.json`: Full tender dataset
- `service-worker.js`: PWA offline support
- `manifest.json`: PWA manifest

### Configuration Management

**Primary config**: `config.yaml`
- Absolute paths to data directories
- Scraper settings (timeout, user agent, URLs)
- Classification priorities (TES/Phakathi)
- Scoring weights and thresholds
- Email/SMTP configuration

**Environment variables** (for Flask deployment):
```bash
ENABLE_SELENIUM=false               # Toggle Selenium scrapers
OUTPUT_DIR=./output                 # JSON output location
TENDERSCAN_EMAIL_ENABLED=false      # Email alerts
PORT=5000                           # Flask server port
```

**Scraper-specific config**:
- National Treasury search terms in `config.yaml`
- Selenium can be disabled globally via `enable_selenium: false`

## Important Implementation Details

### Scraper Development Patterns

**Adding a new scraper**:
1. Create file in `scrapers/` directory
2. Implement function returning array of tender dicts:
   ```python
   def scrape_new_source():
       """Scraper for New Source"""
       tenders = []
       # Scraping logic here
       return tenders
   ```
3. Required fields: `title`, `source`, `url`
4. Optional fields: `ref`, `description`, `closing_date`, `client`, `published_date`
5. Add to `daily_runner.py` scraper list
6. Add to `SCRAPER_HEALTH` monitoring dict

**Error handling pattern**:
```python
try:
    # Scraping logic
    return tenders
except Exception as e:
    print(f"Error scraping source: {e}")
    return []  # Return empty array, don't crash
```

### Classification and Scoring

**Keyword rule modification** (`keyword_rules.py`):
- Three sets: `TES_KEYWORDS`, `PHAKATHI_KEYWORDS`, `EXCLUDE_KEYWORDS`
- Structure: `{"category": ["keyword1", "keyword2"], ...}`
- Case-insensitive matching on title + description
- After changing rules, run `reclassify_existing.py` to update Excel

**Scoring weight adjustment** (`config.yaml`):
```yaml
scoring:
  fit_weight: 0.30      # Capability match importance
  industry_weight: 0.25 # Client industry value
  risk_weight: 0.20     # Entry barrier assessment
  revenue_weight: 0.25  # Contract value potential
```

**Priority threshold tuning**:
```yaml
scoring:
  high_threshold: 7.0   # HIGH priority cutoff
  medium_threshold: 4.5 # MEDIUM priority cutoff
```

### Duplicate Detection Logic

**Two-stage detection** (`utils/excel_writer.py`):
1. **Exact ref match**: Check `_existing_refs_cache`
2. **Fuzzy title match**: 85% similarity threshold
   - Must be from same source (`require_same_source=True`)
   - Within 7-day window (configurable)
   - Uses `fuzzywuzzy` library with Levenshtein distance

**Cache behavior**:
- In-memory caches reset on each run
- Cache built from existing Excel data
- Not persisted between runs (ensures data integrity)

### Chromedriver Management

**Critical dependency**: Selenium scrapers require version-aligned Chromedriver

**Setup process**:
1. Auto-detects installed Chrome version
2. Downloads matching Chromedriver from Chrome for Testing
3. Installs to `tools/chromedriver/` (isolated, not system-wide)
4. Run `python tools/setup_chromedriver.py` after Chrome updates

**Common issues**:
- "Chromedriver version mismatch": Run setup script
- "Chromedriver not found": Check `tools/chromedriver/chromedriver` exists
- "Permission denied": Run `chmod +x tools/chromedriver/chromedriver`

### Dashboard Deployment Flow

**Local to Vercel sync** (`sync_to_vercel.py`):
1. Reads `output/new_tenders.json` (max 200 tenders)
2. Generates `index.html` with embedded data for fast load
3. Saves separate `tenders.json` for full dataset access
4. Copies files to `vercel-dashboard/`
5. Git commit + push to GitHub (auto-triggers Vercel deploy)
6. Vercel serves static files (~30 second deploy time)

**PWA installation**:
- Service worker caches assets for offline access
- Install prompt triggered on second visit (browser requirement)
- Manifest defines app name, icons, theme colors

## Testing and Validation

**No formal test suite exists**. Testing is manual and production-based:

**Manual testing utilities**:
- `test_exclusions.py`: Test exclusion keyword logic
- `reclassify_existing.py`: Batch reclassification for rule validation
- `tools/validate_dashboard_tenders_json.py`: JSON schema validation
- `tools/preflight_check.py`: Chromedriver version check

**Validation patterns in code**:
- Tender validator runs on all scraped data
- Count verification in sync script (scraped vs displayed)
- Scraper health monitoring (consecutive failure tracking)
- Detailed logging in `logs/scraper.log`

**When modifying code**:
1. Test individual scrapers first: `python scrapers/scraper_name.py`
2. Check validation: Look for "WARNING" or "ERROR" in output
3. Verify Excel output: Check `Tender_Dashboard_v2.xlsx` for new rows
4. Test classification: Run `test_exclusions.py` with sample data
5. Check dashboard: Run `sync_to_vercel.py` and inspect HTML

## Deployment

### Local Deployment (macOS)

**Scheduled automation** (launchd):
```bash
# Daily scan at 6 AM
cp com.tenderscan.daily.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.tenderscan.daily.plist

# Weekly report on Mondays at 8 AM
cp com.tenderscan.weekly.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.tenderscan.weekly.plist
```

### Vercel Deployment (Dashboard)

**Configuration**: `vercel.json`
- Rewrites route `/` to `index.html`
- Serves `tenders.json` at root level
- Static file deployment (no build step)
- PWA features: Offline support via service worker

**Deploy workflow**:
1. Run `python3 sync_to_vercel.py` to generate dashboard HTML
2. Script automatically commits and pushes to GitHub
3. Vercel auto-deploys (~30 seconds)
4. Dashboard live at your Vercel URL

**Manual deploy**: `vercel --prod` (from `vercel-dashboard/` directory)

### Flask API Deployment (Optional)

The Flask API (`app.py`) can be deployed separately for automation endpoints (`/api/run/*`, `/cron/*`, `/health`):

**Options**:
- Self-hosted VPS (DigitalOcean, AWS EC2, etc.)
- Any Python hosting platform
- Local machine (development only)

**Setup**:
```bash
# On your server
pip install -r requirements.txt
gunicorn app:app --bind 0.0.0.0:5000 --workers 2 --timeout 120
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete guide.

## Troubleshooting Common Issues

**Scraper failures**:
- Check `logs/scraper.log` for error details
- Verify URL hasn't changed (check `config.yaml`)
- Test scraper individually: `python -c "from scrapers.name import function; print(function())"`
- Disable problematic Selenium scrapers: `enable_selenium: false` in config

**Duplicate tenders appearing**:
- Check fuzzy match threshold (default 85%)
- Verify reference numbers are extracted correctly
- Review `_existing_refs_cache` logic in `excel_writer.py`

**Classification issues**:
- Review keyword rules in `keyword_rules.py`
- Test with `test_exclusions.py`
- Run `reclassify_existing.py` after keyword changes

**Dashboard not updating**:
- Check `output/new_tenders.json` exists and has data
- Verify `sync_to_vercel.py` completed successfully
- Check GitHub push succeeded (look for commit)
- Wait 30 seconds for Vercel to deploy

**Chromedriver errors**:
- Run `python tools/setup_chromedriver.py`
- Check Chrome version: `google-chrome --version` (or `Google Chrome.app` on macOS)
- Verify `tools/chromedriver/chromedriver` exists and is executable

**Excel file locked**:
- Close Excel/Numbers if file is open
- Check file permissions: `ls -l Tender_Dashboard_v2.xlsx`
- Verify path in `config.yaml` is correct

## Key Files Reference

**Core orchestration**:
- `tenderscan.py`: Main scraper orchestrator
- `daily_runner.py`: Daily automation with monitoring
- `weekly_report.py`: Weekly HTML report generator

**Classification and scoring**:
- `classify_engine.py`: Keyword-based classification
- `keyword_rules.py`: TES/Phakathi/Exclusion keywords
- `scoring_engine.py`: Five-dimensional scoring engine

**Data management**:
- `utils/excel_writer.py`: Excel read/write with duplicate detection
- `utils/data_validator.py`: Tender schema validation
- `sync_to_vercel.py`: Dashboard generation and Git sync

**Scrapers**:
- `scrapers/municipalities.py`: Ekurhuleni, Tshwane, Cape Town, eThekwini
- `scrapers/soes.py`: Rand Water, Eskom, Transnet
- `scrapers/national_treasury_selenium.py`: eTenders portal
- `scrapers/joburg_water_selenium.py`: Johannesburg Water
- `scrapers/eskom_direct.py`: Eskom procurement portal

**Dashboard**:
- `app.py`: Flask API server
- `vercel-dashboard/index.html`: Static PWA dashboard
- `vercel-dashboard/service-worker.js`: Offline support

**Configuration**:
- `config.yaml`: Primary configuration file
- `.env.example`: Environment variable template
- `requirements.txt`: Python dependencies
- `vercel-dashboard/package.json`: Node.js dependencies

---

# Enhanced Claude Code Development Rules

## 1. **Discovery & Planning Phase**
- **FIRST**: Read and understand the codebase structure
- **Map dependencies**: Identify all files/modules that relate to the task
- **Create detailed plan**: Write clear, atomic tasks with:
  - Risk level (low/medium/high) for each task
  - Files to be modified
  - Dependencies between tasks
- **Checkpoint**: Wait for approval before proceeding

## 2. **Task Breakdown Standards**
- Each task must be:
  - ✅ Completable in isolation
  - ✅ Testable independently
  - ✅ Reversible if needed
  - ✅ Clear success criteria

## 3. **Execution Principles**

### Simplicity First (CRITICAL)
- **Minimum viable change**: Touch the fewest lines possible
- **Single responsibility**: Each commit does ONE thing
- **Avoid refactoring**: Unless explicitly required
- **Prefer composition**: Add new code rather than modifying working code

### Communication Standards
- **After each task**: HIGH-LEVEL summary only (1-2 sentences)
- **Flag blockers immediately**: Explain why and ask for guidance
- **No code dumps**: Unless specifically requested

## 4. **Quality Standards**

### Zero Tolerance for Laziness
- **Root cause analysis**: Always find the underlying issue
- **No temporary fixes**: No "quick hacks" or "will fix later"
- **No commented-out code**: Either fix it or remove it
- **Complete error handling**: Every edge case handled
- **Production-ready code**: Not prototype-quality

### Testing Requirements
- **Verify after each change**: Test the specific change works
- **Regression check**: Ensure existing functionality still works
- **Document test steps**: Note how you verified each change

## 5. **Code Change Philosophy**

### Surgical Precision
- **Scope**: Only touch code directly related to the task
- **Side effects**: Avoid changing function signatures/interfaces
- **Backwards compatibility**: Maintain unless instructed otherwise
- **Imports**: Only add what's needed, remove unused imports

### Before Writing Code, Ask:
1. Is this the simplest possible solution?
2. Am I changing the minimum amount of code?
3. Could this break anything else?
4. Can I do this with NO changes to existing code?

## 6. **Error Handling Protocol**
When something doesn't work:
1. **Read error messages completely** - don't guess
2. **Trace the stack** - find exact failure point
3. **Understand the cause** - not just the symptom
4. **Fix properly** - address root cause
5. **Prevent recurrence** - add safeguards if needed

## 7. **Anti-Patterns to Avoid**
❌ Making multiple changes at once
❌ Refactoring while fixing bugs
❌ Adding features while fixing issues
❌ Changing code you don't understand
❌ Copying code without understanding it
❌ Leaving debug code in place
❌ "It works on my machine" mentality

## 8. **Pre-Commit Checklist**
Before marking any task complete:
- [ ] Code does exactly what task requires, nothing more
- [ ] No unrelated changes included
- [ ] Error handling is complete
- [ ] No temporary/debug code remains
- [ ] Tested in isolation
- [ ] Tested with existing features

## 9. **Communication Red Flags**
If you catch yourself saying:
- "This should work..." → TEST IT
- "Probably just..." → VERIFY IT
- "Quick fix..." → DO IT PROPERLY
- "I'll come back to..." → FIX IT NOW
- "Not sure why but..." → UNDERSTAND IT FIRST
