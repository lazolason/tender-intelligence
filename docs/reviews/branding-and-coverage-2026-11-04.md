# Branding and project-coverage check — 4 November 2026

Mexel and Phakathi logos were copied from their live websites into dashboard/branding and added to the dashboard header. Verified both images load at desktop and 320px width, with no document overflow. Assets are served locally. PWA description now identifies the combined portfolio; the installed-app icon remains the existing Tender Intelligence icon.

## Read-only source evidence

- eTenders public active listing: fetched all 2,020 advertised records, with pagination and total-count validation. Two classifier candidates, including the previously absent E3748GXMPHEN fuel-oil flow-meter project. This remains a specification/eligibility review candidate, not a proven capability match.
- Eskom Bulletin: fetched 320 published records (published does not necessarily mean currently open). One classifier candidate, the same flow-meter project. The exact MWP3022CX readvertisement was not established by this check.
- Cape Town portal: HTTP 200. Umngeni-uThukela: HTTP 200. Lepelle: redirects to /tenders/ and returns HTTP 200. These are reachability checks, not proof of full extraction.
- Magalies configured /tenders/ URL: HTTP 404. Homepage discovery returned 403, so no alternative endpoint was asserted or access control bypassed.

Raw bounded source summaries are in read-only-source-check-2026-11-04.json and supplementary-source-reachability-2026-11-04.json. No scan persistence, database rewrite or notifications were triggered. The saved dashboard snapshot was not replaced by these read-only checks.

## Fixes made

The default Eskom scraper cap was 50, while the endpoint returned 320 published records. Raised the default to 10,000. Removed the 100-character title and 500-character description truncation, which could discard relevant process requirements. Regression checks cover terms beyond the old limits and more than 50 records.

## Coverage assessment

Matching reflects the agreed combined portfolio and is substantially more precise than the earlier site/equipment keyword logic. It is not comprehensive project discovery or automatic bid qualification.

Remaining priorities:
1. Retrieve and analyse actual tender detail/attachment scope before rejecting ambiguous records. The current pipeline normally analyses PDFs only when the tender URL itself ends in .pdf; eTenders listing URLs usually do not. Commercial/technical scope hidden in PDFs or ZIPs can be missed.
2. Add a needs-review queue and maintain reviewed positive/negative examples, avoiding both broad false positives and over-strict exclusions.
3. Show per-source success, failure and extraction counts in the dashboard. A healthy JSON load alone is not evidence every source succeeded.
4. Resolve Magalies' unavailable direct source and verify supplementary parser extraction, not just HTTP reachability.
5. Use the existing daily source ingestion for monitor/display re-adverts based on scope wording as well as references. An exact reference can change on readvertisement. No separate automated watch or new notification has been configured.
6. Extend beyond public notices only through authorised/licensed private-sector sources or relevant additional portals. eTenders is broad coverage, not proof every buyer publishes there.

Validation: 270 Python tests passed; dashboard smoke passed, and logo rendering was inspected on desktop/mobile. No external deployment, commit or push.
