# Tender Intelligence

Local South African tender intelligence for the combined Mexel and Phakathi/REICON-ODACON portfolio. eTenders is the primary feed; relevance is determined locally from actual capability scope.

## Current matching approach

See [CLAUDE.md](CLAUDE.md#classification-rules-and-portfolio-matches) for the source-of-truth rules. Opportunities can match multiple portfolios and carry separate capability tags, keywords and reasons. Existing category fields remain for compatibility. No brand mention proves eligibility or product interchangeability.

## Local operation

Use `./serve_app.sh` for the local dashboard. Scan and sync commands and deployment details are documented in [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md). A scan can update the operational database and trigger configured notifications; run only within the authorised scope. Repository cleanup does not reload installed launchd jobs.

## Verification

Python: `.venv/bin/python -m pytest -q`.
Dashboard: `npm --prefix dashboard run test:run`, `lint`, `typecheck` and `test:smoke`.

Historic classification reports are retained as dated evidence, not current matching instructions. Backups and the operational database are preserved. Never commit `.env`, secrets or database files.

## Coverage and review

The dashboard includes source health and a specification-review queue. Official-source PDF attachments are checked within explicit limits; archives, scans, unreadable documents and budget-limited items remain for manual review. A match is not proof of eligibility. `tools/refresh_portfolio_snapshot.py` provides a public-source snapshot refresh without database writes or sends. Magalies' direct source currently fails with HTTP 404, so Water Boards coverage is partial.

## Search beyond the shortlist

Use **Search all captured notices** to search the full captured public feed, including uncertain and excluded records, by reference, scope, buyer and attachment name. Possible candidates remain separate from strong portfolio matches. No keyword signal means unassessed, not irrelevant. Source failures and unread attachments prevent any claim of zero misses; compare results against an independent feed to measure recall.
