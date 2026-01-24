# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Tender Intelligence System** - Automated tender scraping, classification, and scoring engine for Mexel Energy Sustain. Scrapes 11+ South African government and SOE sources, scores opportunities using a composite scoring engine, and displays results on a local-only PWA dashboard.

## Architecture

### Three-Component System

1. **Scraping & Processing Pipeline** (Python)
   - [tenderscan.py](tenderscan.py) - Main automation engine that orchestrates all scrapers, validates data, classifies tenders, scores them, logs to Excel, and generates output files
   - [scrapers/](scrapers/) - Individual scraper modules for each data source (municipalities, SOEs, National Treasury, Eskom, etc.)
   - [utils/](utils/) - Shared utilities (Excel writer, validators, duplicate detection, PDF analysis, alerts)
- [scoring_engine.py](scoring_engine.py) - Composite scoring algorithm (fit, industry, Mexel suitability)
   - [keyword_rules.py](keyword_rules.py) - Classification rules defining what qualifies as Mexel vs EXCLUDED

2. **Dashboard Sync** (Python → Static PWA)
   - [sync_dashboard.py](sync_dashboard.py) - Generates static HTML dashboard from scraped data for local use
   - [dashboard/](dashboard/) - Static PWA with offline support, virtual scrolling, filters, calendar view

3. **Flask API** (Optional, for automation triggers)
   - [app.py](app.py) - Minimal Flask API with `/api/run/*` and `/cron/*` endpoints
   - Used for remote triggering of scans (not required for local operation)

### Data Flow

```
Scrapers → tenderscan.py → Validation → Classification → Scoring → Excel Log
                                                                    ↓
                                                              output/new_tenders.json
                                                                    ↓
                                                            sync_dashboard.py
                                                                    ↓
                                                          dashboard/index.html
                                                                    ↓
                                                            Local static server
```

### Key Design Decisions

- **Scoring vs Classification**: Classification ([keyword_rules.py](keyword_rules.py)) determines Mexel/EXCLUDED using keyword matching. Scoring ([scoring_engine.py](scoring_engine.py)) evaluates priority (HIGH/MEDIUM/LOW) using composite metrics (fit, industry).
- **Suitability**: Each tender gets a `mexel_suitability` score (Mexel product fit). The dashboard treats all classified tenders as Mexel.
- **Dashboard Persistence**: [sync_dashboard.py](sync_dashboard.py) merges new tenders with existing ones (up to 200 max) to prevent empty UI when no new tenders are found.
- **Selenium Toggle**: Controlled by `config.yaml` → `scrapers.enable_selenium`. Some scrapers (National Treasury, Joburg Water, Eskom Direct) require Selenium. Disabled in production to avoid Chrome dependencies.

## Common Development Commands

### Setup
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the System

```bash
# Run full tender scan (scrapes all sources, scores, logs to Excel)
python tenderscan.py

# Sync results to local dashboard (generates HTML + tenders.json)
python sync_dashboard.py

# Run weekly report generation
python weekly_report.py

# Start Flask API (optional, for remote triggers)
python app.py
# or with Gunicorn:
gunicorn app:app --bind 0.0.0.0:5000 --workers 2 --timeout 120
```

### Testing Components

```bash
# Test individual scrapers
python -c "from scrapers.municipalities import scrape_all_municipalities; print(len(scrape_all_municipalities()))"
python -c "from scrapers.soes import scrape_all_soes; print(len(scrape_all_soes()))"

# Test scoring engine
python -c "from scoring_engine import score_tender; print(score_tender({'title': 'Water treatment RO system', 'description': 'Reverse osmosis for power station', 'client': 'Eskom'}))"

# Validate dashboard data
python tools/validate_dashboard_tenders_json.py

# Build dashboard snapshot locally
python tools/build_dashboard_snapshot.py

# Test dashboard locally (serves on http://localhost:8000)
cd dashboard && python3 -m http.server 8000
```

### Configuration

Primary configuration file: [config.yaml](config.yaml)

**Critical Paths** (absolute paths on macOS - adjust for your system):
- `paths.tender_log_excel` - Master Excel log where ALL tenders are recorded
- `paths.active_tenders` - Folder creation root (tender folders: `{ref} - {client} - {short_title}`)
- `paths.output_dir` - JSON outputs (`new_tenders.json`, `summary.txt`, `scraper_health.json`)
- `paths.log_file` - Scraper execution logs

**Scraper Settings**:
- `scrapers.enable_selenium` - Toggle Selenium-based scrapers (National Treasury, Joburg Water)
- `scrapers.search_terms` - National Treasury search queries

**Scoring Thresholds**:
- `scoring.high_threshold: 7.0` - Composite score ≥ 7.0 → HIGH priority
- `scoring.medium_threshold: 4.5` - Composite score ≥ 4.5 → MEDIUM priority

## Code Organization

### Scrapers ([scrapers/](scrapers/))

Each scraper module follows this pattern:
- Returns list of tender dictionaries with standardized fields: `ref`, `title`, `description`, `client`, `source`, `url`, `closing_date`
- **Must NOT** perform classification or scoring (tenderscan.py handles this centrally)
- Should use `utils.retry_tools` for HTTP requests with backoff
- Log errors using `utils.logging_tools.log_error()`

**Active Scrapers**:
- [municipalities.py](scrapers/municipalities.py) - Cape Town
- [soes.py](scrapers/soes.py) - Rand Water, Johannesburg Water, Transnet, Eskom, Anglo American, Harmony Gold, Seriti
- [national_treasury_selenium.py](scrapers/national_treasury_selenium.py) - eTenders portal (Selenium-based)
- [joburg_water_selenium.py](scrapers/joburg_water_selenium.py) - Johannesburg Water (Selenium-based)
- [eskom_direct.py](scrapers/eskom_direct.py) - Eskom tender bulletin (Selenium-based)

**Disabled Scrapers** (etenders.gov.za API returns 405 errors):
- [eskom.py](scrapers/eskom.py), [sanral.py](scrapers/sanral.py), [transnet.py](scrapers/transnet.py)

### Utils ([utils/](utils/))

- [excel_writer.py](utils/excel_writer.py) - Handles Excel logging with duplicate detection, scoring integration, and auto-column sizing
- [data_validator.py](utils/data_validator.py) - Validates tender schema (required fields, date formats, ref patterns)
- [duplicate_detector.py](utils/duplicate_detector.py) - Fuzzy string matching for duplicate detection (Levenshtein distance)
- [semantic_duplicate_detector.py](utils/semantic_duplicate_detector.py) - ML-based semantic deduplication using sentence transformers
- [pdf_analyzer.py](utils/pdf_analyzer.py) - Extracts requirements, deadlines, and metadata from PDF tender documents
- [bid_tracker.py](utils/bid_tracker.py) - Records bid outcomes and calculates win rates
- [multi_channel_alerts.py](utils/multi_channel_alerts.py) - Slack/SMS alerts for urgent tenders
- [scraper_monitor.py](utils/scraper_monitor.py) - Tracks scraper health and generates failure reports
- [email_alerts.py](utils/email_alerts.py) - Email notifications for urgent tenders

### Scoring System ([scoring_engine.py](scoring_engine.py))

Composite scoring algorithm with two dimensions:

1. **Fit Score (60%)** - Keyword density matching Mexel capabilities
2. **Industry Score (40%)** - Client industry value (power=10, mining=9, municipal=7, etc.)

**Priority Calculation**:
- Composite Score ≥ 7.0 → `HIGH`
- Composite Score ≥ 4.5 → `MEDIUM`
- Composite Score < 4.5 → `LOW`

**Company Suitability**:
- `mexel_suitability` is calculated for Mexel product fit
- Dashboard labels all classified tenders as Mexel

### Classification Rules ([keyword_rules.py](keyword_rules.py))

**Three-Profile System** (PHASE 2 - Strict Competence Rules):

1. **STRONG_MATCH_KEYWORDS** (Profile A: The Product)
   - Automatic match - specific chemical technologies or brand names
   - Examples: "mexel", "film forming amine", "scale inhibitor", "surfactant", "legionella"
   - Any match → Immediate INCLUDE

2. **SYSTEM_KEYWORDS** (Profile B1: The System)
   - Industrial water systems that Mexel serves
   - Examples: "cooling tower", "condenser", "boiler", "heat exchanger", "CRAC", "data center"
   - **Must be paired with ACTION keyword** to qualify

3. **ACTION_KEYWORDS** (Profile B2: The Action)
   - Services or chemical applications Mexel provides
   - Examples: "treatment", "chemical", "dosing", "efficiency", "PUE", "thermal efficiency"
   - **Must be paired with SYSTEM keyword** to qualify

4. **NEGATIVE_KEYWORDS** (Exclusions)
   - Targeted exclusions for non-Mexel work
   - Examples: "construction of", "split unit", "office air conditioning", "building hvac"
   - **Note**: General "hvac" removed - too broad, excludes data center CRAC/CRAH systems
   - Any match → Immediate EXCLUDE (overrides all other matches)

**Classification Logic**:
- NEGATIVE match → EXCLUDE
- STRONG_MATCH → INCLUDE
- (SYSTEM + ACTION) → INCLUDE
- Otherwise → EXCLUDE


### Dashboard Sync ([sync_dashboard.py](sync_dashboard.py))

Process:
1. Load active tenders from the Excel log + overlay new tenders from `output/new_tenders.json`
2. Generate static HTML with embedded JS/CSS (no external dependencies)
3. Create `dashboard/tenders.json` for client-side loading
4. Serve locally with `python3 -m http.server 8000`
5. QA checks ensure scraped count matches displayed count

**Features**:
- Virtual scrolling (loads 20 tenders at a time)
- Search across ref, title, description, source, client
- Filters: All, Mexel, HIGH, MEDIUM, LOW
- Calendar view with closing date visualization
- Countdown badges (urgent: ≤3 days, warning: ≤7 days)
- PWA manifest for mobile installation

## Phase 1 Intelligence Enhancements

Optional features (requires additional dependencies in [requirements.txt](requirements.txt)):

- **PDF Analysis** - Extracts requirements and deadlines from PDF URLs (requires `pdfplumber`, `PyPDF2`)
- **Semantic Deduplication** - ML-based duplicate detection using embeddings (requires `sentence-transformers`, `torch`, `scikit-learn`)
- **Bid Tracking** - Records win/loss outcomes and calculates performance metrics (no extra deps)
- **Multi-Channel Alerts** - Slack/SMS notifications for urgent tenders (requires `slack-sdk`, `twilio`)

Enable in [config.yaml](config.yaml) under `alerts` section.

## Deployment

### Local Dashboard Usage

1. Run `python sync_dashboard.py` to generate static files
2. Serve locally: `cd dashboard && python3 -m http.server 8000`

See [DEPLOYMENT.md](DEPLOYMENT.md) for full deployment guide.

### Local Automation (macOS)

```bash
# Daily scan at 8 AM
launchctl load ~/Library/LaunchAgents/com.tenderscan.sync.plist

# Weekly report on Monday 7 AM
launchctl load ~/Library/LaunchAgents/com.tenderscan.weekly.plist
```

See [com.tenderscan.daily.plist](com.tenderscan.daily.plist) and [com.tenderscan.weekly.plist](com.tenderscan.weekly.plist) for launchd configuration examples.

## Troubleshooting

### Common Issues

**"No module named 'scrapers'"**
- Ensure you're running from project root directory
- Check `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` is present in scripts

**Selenium errors (ChromeDriver not found)**
- Set `scrapers.enable_selenium: false` in [config.yaml](config.yaml) to disable Selenium scrapers
- For local development, run `python tools/setup_chromedriver.py` (see [CHROMEDRIVER_SETUP.md](CHROMEDRIVER_SETUP.md))

**Dashboard shows 0 tenders**
- Check `output/new_tenders.json` exists and has data
- Verify `sync_dashboard.py` completed without errors
- QA checks in sync script will log count mismatches

**Excel "Permission Denied" errors**
- Close Excel file before running tenderscan.py
- Check file path in `config.yaml` is correct and accessible

**405 Errors from etenders.gov.za API**
- Known issue with certain SOE scrapers (Eskom, SANRAL, Transnet, Umgeni via etenders API)
- These scrapers are disabled in [tenderscan.py:156-161](tenderscan.py#L156-L161)
- Use alternative scrapers where available (e.g., `eskom_direct.py` scrapes Eskom's bulletin directly)

## Critical Implementation Rules

1. **Never hardcode API keys** - Use environment variables or [.env](.env) file (see [.env.example](.env.example))
2. **Always validate tender data** - Use `TenderValidator` from [utils/data_validator.py](utils/data_validator.py) before processing
3. **Preserve Excel data** - [excel_writer.py](utils/excel_writer.py) uses append-only operations with duplicate detection to prevent data loss
4. **Maintain dashboard persistence** - [sync_dashboard.py](sync_dashboard.py) merges new tenders with existing ones (max 200) to avoid empty UI
5. **Classification before scoring** - tenderscan.py first excludes unwanted tenders via [keyword_rules.py](keyword_rules.py), then scores remaining tenders
6. **Scraper isolation** - Each scraper handles only data extraction; [tenderscan.py](tenderscan.py) handles all classification, scoring, and logging

## Git Workflow

- Main branch: `main`
- Run `python sync_dashboard.py` after scans to refresh the local dashboard
- Includes co-authorship attribution in commits (see Git Safety Protocol in [DEPLOYMENT.md](DEPLOYMENT.md))
