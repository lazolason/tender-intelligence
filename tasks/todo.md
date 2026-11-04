# Task: HVAC Keyword Refinement

## Objective
Refine keyword classification to distinguish between general building HVAC (excluded) and data center precision cooling (included), aligning with Mexel's core business in critical infrastructure cooling.

## Risk Assessment: LOW
- Changes are additive (new keywords) and refinement (more specific exclusions)
- No changes to classification logic or scoring engine
- Backward compatible - existing matches still work
- Test validation confirms expected behavior

---

## Task Breakdown

### Discovery Phase
- [x] Reviewed current `NEGATIVE_KEYWORDS` configuration
- [x] Identified problem: "hvac" too broad, excludes data center cooling (CRAC, CRAH, CHR)
- [x] Mapped affected files: `keyword_rules.py`, `dashboard/write_rules.py`
- [x] Verified Mexel's business scope includes data center precision cooling

### Implementation Phase
- [x] **STRONG_MATCH_KEYWORDS**: Added `"surfactant"`, `"legionella"`, `"asme ptc 12.2"`
  - File: `keyword_rules.py` lines 16-17
  - Risk: LOW - Highly specific technical terms, no false positive risk

- [x] **SYSTEM_KEYWORDS**: Added data center cooling systems
  - File: `keyword_rules.py` lines 30-34
  - Added: `"crac"`, `"crah"`, `"chr"`, `"data center"`, `"data centre"`, `"computer room"`, `"server room"`, `"precision cooling"`, `"close control cooling"`
  - Risk: LOW - Requires ACTION pairing, won't match standalone

- [x] **ACTION_KEYWORDS**: Added data center efficiency metrics
  - File: `keyword_rules.py` lines 44-47
  - Added: `"pue"`, `"power usage effectiveness"`, `"vacuum recovery"`, `"thermal efficiency"`, `"condenser efficiency"`
  - Risk: LOW - Requires SYSTEM pairing, won't match standalone

- [x] **NEGATIVE_KEYWORDS**: Refined HVAC exclusions
  - File: `keyword_rules.py` lines 58-60
  - Removed: `"hvac"` (too broad)
  - Added: `"split unit"`, `"office air conditioning"`, `"building hvac"`, `"building air conditioning"`
  - Kept: `"ventilation"` (general building systems)
  - Risk: LOW - More specific exclusions reduce false negatives

- [x] Synchronized `dashboard/write_rules.py` with same changes
  - File: `dashboard/write_rules.py`
  - Risk: LOW - Maintains consistency between main and dashboard configs

### Validation Phase
- [x] Created test script `test_hvac_keywords.py`
  - Tests 8 scenarios: 4 data center (should INCLUDE), 4 building HVAC (should EXCLUDE)
  - All tests passed ✅

- [x] Updated documentation
  - File: `CLAUDE.md` lines 166-196
  - Updated Classification Rules section to reflect current three-profile system
  - Risk: LOW - Documentation only

- [x] Created change documentation
  - File: `hvac_keyword_update.md` (artifact)
  - Documents rationale, examples, and impact

---

## Testing Performed

### Test Results (from `test_hvac_keywords.py`)

**✅ INCLUDED (Correct - Data Center Cooling)**
1. "CRAC Unit Water Treatment" → System: CRAC, data center + Action: treatment, chemical
2. "Data Center PUE Optimization" → System: condenser, data center, precision cooling + Action: treatment, optimization, pue
3. "Computer Room Cooling Chemicals" → System: cooling water, CRAH, computer room, precision cooling + Action: chemical, chemistry
4. "Server Room Efficiency" → System: cooling water, data centre, server room + Action: treatment, efficiency, thermal efficiency

**❌ EXCLUDED (Correct - General Building HVAC)**
1. "Office HVAC Installation" → Negative: split unit
2. "Building Air Conditioning" → Negative: building air conditioning, ventilation
3. "Split Unit Maintenance" → Negative: split unit
4. "General Ventilation" → Negative: ventilation

### Regression Check
- Classification logic unchanged (still: NEGATIVE → STRONG_MATCH → SYSTEM+ACTION)
- Existing keywords still functional
- No breaking changes to `classify_engine.py` or `scoring_engine.py`

---

## Review Summary

### Changes Made
- **keyword_rules.py**: Added 3 strong match keywords, 8 system keywords, 5 action keywords; refined 5 negative keywords
- **dashboard/write_rules.py**: Synchronized with main keyword_rules.py
- **CLAUDE.md**: Updated Classification Rules section to reflect current system
- **test_hvac_keywords.py**: Created validation test (8 test cases)
- **hvac_keyword_update.md**: Created change documentation artifact

### Files Modified
1. [keyword_rules.py](file:///Users/lazolasonqishe/Documents/tender-intelligence/keyword_rules.py) - Main keyword configuration
2. [dashboard/write_rules.py](file:///Users/lazolasonqishe/Documents/tender-intelligence/dashboard/write_rules.py) - Dashboard sync copy
3. [CLAUDE.md](file:///Users/lazolasonqishe/Documents/tender-intelligence/CLAUDE.md) - Architecture documentation

### Risk Assessment: LOW
- **No logic changes**: Classification algorithm unchanged
- **Additive changes**: New keywords expand coverage without breaking existing matches
- **More specific exclusions**: Reduces false negatives (missed opportunities)
- **Tested and validated**: All test cases pass as expected
- **Backward compatible**: Existing tender classifications remain valid

### Potential Issues to Watch
- **Monitor for false positives**: "ventilation" still in NEGATIVE_KEYWORDS - may exclude some data center ventilation tenders if they don't mention CRAC/CRAH explicitly
- **Edge case**: Tenders mentioning "data center" + "ventilation" but not "CRAC" may be excluded
- **Recommendation**: Review next batch of classified tenders for any data center opportunities that were excluded

### Follow-up Items
- [ ] Re-run classification on historical tenders containing "CRAC", "CRAH", "data center cooling", "PUE"
- [ ] Monitor new tenders for data center opportunities previously missed
- [ ] Consider adding "data center ventilation" as exception to "ventilation" exclusion if false negatives occur

---

## Verification Results

### Tender Scan Execution (2026-01-24 18:38)
- [x] **Scrapers executed successfully**: 215 tenders scraped from 6 sources
  - Municipalities (Cape Town): 0
  - SOEs (Rand Water, Johannesburg Water, Transnet, Eskom, Anglo, Harmony, Seriti): 61
  - National Treasury (Selenium): 0
  - Johannesburg Water (Selenium): 10
  - Eskom Tender Bulletin: 50
  - Water Boards (Umgeni, Magalies, Lepelle): 94

- [x] **Classification working correctly**: 121 tenders excluded by keyword rules
  - Negative keyword matches: 'cleaning service', 'transformer', 'civil works', 'panel of', 'hydroelectric', 'construction of', 'garden service', 'commissioning support'
  - No competence profile match: Majority of tenders (no SYSTEM+ACTION pairing)

- [x] **Validation working correctly**: 94 invalid tenders (expired closing dates)
  - Most from Umgeni Water with dates in 2025/early 2026

- [x] **Result**: 0 new Mexel-relevant tenders
  - **Expected outcome**: Current batch contains no water treatment or thermal efficiency opportunities
  - **Keyword rules working as designed**: Excluding non-relevant tenders, ready to capture data center cooling when available

### Dashboard Sync Verification
- [x] Dashboard synced successfully: 2 historical tenders displayed in summary
- [x] Active list correctly shows 0 (both tenders expired Dec 2025)
- [x] QA check passed: 2 tenders scraped = 2 displayed
- [x] Dashboard accessible at http://localhost:8001

### Keyword Classification Validation
- [x] No false positives: No general HVAC tenders incorrectly included
- [x] System ready for data center cooling: New keywords (CRAC, CRAH, data center, PUE) active and ready to match
- [x] Exclusions working: Building HVAC terms ('split unit', 'office air conditioning', 'building hvac') successfully filtering

---

## Completion Status: ✅ COMPLETE

All tasks completed successfully. System now correctly distinguishes between general building HVAC (excluded) and data center precision cooling (included).


## Audit repair plan — 4 November 2026

Baseline: GitHub main ee8a3911f61b9db47f5758cf0c1b85949da43b05, isolated audit checkout. The active local scanner checkout contains prior uncommitted changes and will not be edited or reloaded.

Approval checkpoint: AI_RULES.md section 1 requires human approval of this plan before implementation.

- [ ] Redirect safety [MEDIUM]: validate each redirect before issuing its request, cap redirect hops, preserve TLS verification and existing request options. Files: utils/retry_tools.py; tests/test_network_security.py. Verify with an offline adapter proving a public URL cannot redirect a request to a private address.
- [ ] Backup correctness [LOW]: honour DB_PATH and allow isolated backup destinations; verify a backup contains the configured database. Files: utils/backup_database.py; new tests/test_backup_database.py.
- [ ] Daily workflow status [MEDIUM]: distinguish SMTP failure from no eligible tenders; report failed core jobs correctly through the API/CLI; write status atomically and honour runtime output settings. Preserve default boolean email APIs for existing callers. Files: daily_runner.py, app.py, utils/email_alerts.py, utils/run_status.py, tools/email_doctor.py and focused existing/new tests.
- [ ] Scraper coverage health [MEDIUM]: propagate underlying source failures through grouped scrapers and CLI artifacts while retaining valid partial results; align CI source selection with the active registry, avoiding retired or duplicate sources. Files: scrapers/base.py, scrapers/municipalities.py, scrapers/soes.py, scrapers/water_boards.py, scrapers/registry.py, tenderscan.py, tools/scrape_source.py, .github/workflows/update-dashboard-tenders.yml and focused regression tests.
- [ ] Development dependency advisories [MEDIUM]: update compatible dashboard tooling dependencies and verify any narrowly scoped dependency override. Do not run npm audit fix --force or downgrade ESLint to the obsolete version suggested by npm. Files: dashboard/package.json, dashboard/package-lock.json; adjust the CI audit gate only after verification.
- [ ] Regression verification [LOW]: run full Python tests, Ruff, dashboard tests/lint/typecheck and dependency audits. Use isolated temporary data and mocked notifications; no real alerts or production scan.
- [ ] Review delivery [LOW]: prepare audit report and complete patch; leave code uncommitted and unpushed pending explicit publication instruction.

Confirmed reproductions before changes:
- Public HTTPS redirect reached https://127.0.0.1/private before the current guard rejected it (offline requests adapter).
- A valid configured temporary DB existed, but backup_database() ignored DB_PATH and returned False.
- A mocked failed daily scan returned HTTP 200 with top-level status success.
- A mocked failed digest was labelled no_alerts_needed.
- A municipality fetch exception returned [] and the enclosing FunctionScraper.last_error remained None.

Baseline checks: 193 Python tests passed; 34 dashboard tests passed; Ruff, dashboard lint and typecheck passed. npm audit found 14 development dependency advisories (4 high, 10 moderate); runtime-only audit found none. No live scan, alert, scheduler change, commit or push was performed.


## Tender Intelligence repository audit and repairs — 4 November 2026

Status: implementation complete on review branch `fix/tender-audit-etenders-2026-11-04`; pull request #1 is open. The active operational checkout and its schedule/database were not changed.

- [x] Prevent unsafe redirect hops; preserve HTTPS/TLS checks, retry behaviour and response handling.
- [x] Honour configured database paths in backups and avoid creating a missing source database.
- [x] Report daily scan, sync and mail outcomes accurately through API and CLI; write run status atomically and respect configured output paths.
- [x] Propagate grouped source failures while preserving partial records; make eTenders the primary feed and align CI with active scrapers.
- [x] Update vulnerable Python and dashboard dependency pins; verify core and optional-ML Python environments plus dashboard audit.
- [x] Separate Mexel and Phakathi/REICON/ODACON classification and scoring; normalize matching; handle award/cancellation notices before brand routing.
- [x] Fix dashboard card overflow at narrow mobile widths and extend CI smoke coverage.
- [x] Update current scraper and keyword architecture documentation; prepare keyword routing report and full patch.
- [x] Reclassify the checked-in live tender snapshots against current company rules; remove out-of-scope records and keep both snapshot copies identical.
- [x] Verify Python tests (228 passed), Ruff, dashboard tests (34 passed), dashboard lint/typecheck, npm audit (0 vulnerabilities), live source parsing, and browser widths 320/390/768/1440 px.

Snapshot review: all 32 tender rows had been labelled PHAKATHI. Current rules classified all 32 as out of scope after adding a guard for mechanical butterfly-valve work that matched only because it mentioned a condenser. Both checked-in dashboard tender arrays are now empty and carry a scope-refresh count. All 16 separate planned-opportunity records were checked through their classifier and relevance gate and remain in their current categories.

Known transport limit: outbound URL validation blocks literal private/loopback targets and validates each redirect before requesting it; DNS rebinding is not covered by the current resolver-free guard.

## Website-based keyword correction — 2026-11-04
- [x] Read live company websites and user-confirmed display-supply scope (low risk).
- [x] Tighten keyword_rules.py and classify_engine.py to require capability signals (medium risk: stricter relevance filtering).
- [x] Review all 62 dashboard records without rewriting operational data; see review/keyword-review.md.
- [x] Verify classifier and broader regression suite: 240 passed; one existing snapshot metadata assertion separately reported.

Review: removed broad equipment/site/action false positives, preserved chemistry/process monitoring and display supply. No commit, push, scan, data refresh or scheduler reload. Follow-up: review source specifications and snapshot provenance; repair stale snapshot metadata test independently.

### Second website coverage review
- [x] Read full capability and delivery pages of both live websites.
- [x] Correct chemistry, preservation, instrumentation, monitoring and connectivity gaps; restrict Huawei scope.
- [x] 255 tests passed, existing snapshot-metadata test deselected; diff check passed.
- [x] Record source-to-rule mapping in review/website-coverage-check.md.

- [x] Add user-confirmed chemistry terms with process context; Huawei left unchanged in this update. 263 tests passed; existing snapshot-metadata check remains deselected.

## Combined portfolio matching
- [x] Trace database, scanner, procurement-plan and dashboard paths.
- [x] Add independent portfolio matches, capability tags and per-portfolio evidence while retaining legacy category compatibility.
- [x] Carry metadata through exports; update dashboard search, filters and counts for overlapping matches.
- [x] Verify mixed-scope export, exclusion and product-evidence separation: Python and dashboard checks passed; existing snapshot metadata check remains outstanding.
- [x] Prepare review/combined-portfolio-review.md and full patch. No production data or scheduling changed.

## Active repository cleanup
- [x] Back up tracked working tree, local edits, original snapshot and SQLite database.
- [x] Integrate current main and portfolio rules; preserve reviewed UI and local scanner settings.
- [x] Refresh published snapshot by scope; quarantine two unverified rows without deleting operational records.
- [x] Archive superseded plan and remove temporary worktrees after stashing review changes.
- [x] Verify 268 Python and 35 dashboard tests, lint, typecheck and browser smoke. No commit or push.

## Branding and source coverage
- [x] Add official Mexel/Phakathi logo assets and verify mobile/desktop loading.
- [x] Check public eTenders/Eskom feeds read-only and supplementary endpoint reachability.
- [x] Remove Eskom 50-record default cap and scope-text truncation; 270 Python tests passed, dashboard smoke passed.
- [x] Document remaining attachment, source-health, review-queue and portal coverage limits. No operational scan or notifications run.

## Document coverage and push
- [x] Preserve eTenders attachment links and perform bounded official-PDF checks before final classification.
- [x] Add needs-review queue, source health and stale/unverified indicators.
- [x] Refresh public-source snapshot without database writes or sends: 2 candidates, 82 review items; Magalies remains a visible partial failure.
- [x] Revalidate legacy labels on export so old false positives cannot reappear.
- [x] Verify Python, dashboard, source and browser checks; prepare release notes.
