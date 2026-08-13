# Archived Scrapers

These scrapers have been deprecated and are no longer used by the main pipeline.
They are kept here for reference only.

## `eskom.py`
**Deprecated:** Replaced by `eskom_direct.py`
**Reason:** The old scraper used the etenders.gov.za API which returns 405 errors.
`eskom_direct.py` scrapes Eskom's own tender bulletin directly via REST API with
Selenium fallback, providing more reliable and comprehensive results.

## `transnet.py`
**Deprecated:** No replacement
**Reason:** The etenders.gov.za API returns 405 errors for Transnet. No alternative
endpoint has been identified. Transnet tenders are still captured via the National
Treasury eTenders portal scraper (`national_treasury_selenium.py`).
