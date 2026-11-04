# Combined portfolio and coverage release

The old site/equipment keyword combinations produced unrelated matches. The current rules require relevant chemistry, dosing, monitoring, equipment or integration scope, and permit overlapping Mexel / REICON-ODACON / Phakathi matches with separate evidence. Refurbishment and mechanical works are excluded. Reviewed display-supply scope remains included; no expanded Huawei scope was added.

Preserves the local UI refresh and adds official company logos. UI PR #2 remains open and is superseded in scope by this review branch; it was not merged by this task.

Coverage improvements: eTenders attachment links, bounded official PDF text review before final classification, manual-review queue, source-health display, full Eskom default listing capacity and untruncated scope text. Exports revalidate stale stored categories without changing database records.

Fresh public-source snapshot: eTenders 2,020 records, Eskom 320 published records, Cape Town 44, Water Boards 4 with partial failure (Magalies HTTP 404). After reference/date handling, 2 matched candidates and 82 review items; 15 PDFs read successfully. Processing limits and non-PDF/unreadable content remain explicit. The flow-meter project is a review candidate, not a confirmed bid qualification. No database writes, external sends, bookings or scheduler reload occurred during the refresh.

Validation: full Python suite 275 passed; one further download-size-limit regression plus affected export tests passed in a 13-test targeted run. Dashboard: 36 tests, lint, typecheck and browser smoke passed. Ruff and diff whitespace checks passed. Local browser confirmed source-health, review count and no horizontal overflow.

Pre-existing daily_runner.py and com.tenderscan.daily.plist edits are preserved locally and excluded from this commit. Original tracked files, snapshot, SQLite backup and local-change patch remain in the agent's backup directory. Historical implementation plan archived under docs/archive.
