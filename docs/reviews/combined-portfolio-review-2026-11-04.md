# Combined portfolio matching

Portfolio qualification is independent, allowing MEXEL, REICON_ODACON and PHAKATHI capability tags on the same opportunity. REICON/ODACON remains associated with Phakathi. Each match carries its own capability list, matched keywords and reason. This identifies candidate scope, not tender eligibility or interchangeable product approvals.

The existing single category field is retained for storage/scoring compatibility; it does not suppress additional matches. Metadata is derived from stored title/description at export, without a database schema change. Scanner output, procurement plans and snapshot exports carry the metadata. Dashboard company filters and counts support overlapping companies; totals can overlap, while the all-tenders list does not duplicate records. Cards expose portfolio badges and search includes portfolio/capability terms.

Buyer/end-user names are not qualification rules. Historical MWP3022CX is a display-supply example; readvertisement date is unknown. No further Huawei rule changes were made during this update.

## Verified mixed-scope example

```json
{
  "portfolios": [
    "MEXEL",
    "REICON_ODACON",
    "PHAKATHI"
  ],
  "companies": [
    "Mexel",
    "Phakathi"
  ],
  "portfolio_matches": [
    {
      "portfolio": "MEXEL",
      "capabilities": [
        "Cooling-water chemistry",
        "Dosing and process monitoring"
      ],
      "matched_keywords": [
        "chemical dosing",
        "cooling water",
        "dosing",
        "surfactant",
        "treatment"
      ],
      "reason": "Cooling-water product/process scope"
    },
    {
      "portfolio": "REICON_ODACON",
      "capabilities": [
        "Water and steam-cycle chemistry"
      ],
      "matched_keywords": [
        "boiler",
        "corrosion inhibitors",
        "odacon"
      ],
      "reason": "REICON/ODACON chemistry scope; delivered through Phakathi"
    },
    {
      "portfolio": "PHAKATHI",
      "capabilities": [
        "Equipment, instrumentation and integration"
      ],
      "matched_keywords": [
        "chemical dosing",
        "online monitoring"
      ],
      "reason": "Specified equipment or process-integration scope"
    }
  ]
}
```

## Validation

266 Python tests passed with the existing snapshot-metadata test deselected; after adding an explicit overlapping database-to-export case, all 8 targeted export/procurement-plan tests passed. Dashboard: 35 tests, lint, typecheck and browser smoke passed. Diff whitespace check passed. The unresolved snapshot test expects legacy scope_refresh metadata absent from the checked-in data and does not call the classifier.

No production scan, database rewrite, dashboard refresh or scheduler reload was performed. Work is local and uncommitted on fix/eskom-monitor-keywords.

## Dry-run review of the 62 displayed-snapshot records

| Reference | Portfolio matches | Capabilities |
|---|---|---|
| E3789CXMWP | EXCLUDED |  |
| TPL/2026/07/0533/9677/RFQ | EXCLUDED |  |
| E3775GXMPGRO | EXCLUDED |  |
| PRDP 32/2025-26 | EXCLUDED |  |
| TPT/2026/10/1476/13514/RFQ | EXCLUDED |  |
| 57 OF 2026 | EXCLUDED |  |
| E3626GXMPKRI | EXCLUDED |  |
| WTE-2636ES | EXCLUDED |  |
| RFQJW054NS26-27 | PHAKATHI | Equipment, instrumentation and integration |
| ZNQP 04/08/2026 | EXCLUDED |  |
| E3656GXNOU | EXCLUDED |  |
| E3653GXNOU | EXCLUDED |  |
| MPMAT10677GX01 | EXCLUDED |  |
| RFB 3273/2026-(ERP NO 523017) | PHAKATHI | Equipment, instrumentation and integration |
| CSA/06/2026-27 | EXCLUDED |  |
| 9/3/1/445 | EXCLUDED |  |
| BID - 2646GS | EXCLUDED |  |
| E3614GXMPKEN | EXCLUDED |  |
| E3624GXMPGRO | EXCLUDED |  |
| SCM/2026/99/ENG | EXCLUDED |  |
| RW10420384/26 | EXCLUDED |  |
| E3610GXMPARN | EXCLUDED |  |
| E2192GXMPKRIR BIDDERS LIST | EXCLUDED |  |
| BID SAWS-453/26 | EXCLUDED |  |
| RFQ 12176 RE-ISSUE | EXCLUDED |  |
| RFP15/2026 | EXCLUDED |  |
| E3525GXMPMAT | EXCLUDED |  |
| E3455GXMPGRO | MEXEL | Dosing and process monitoring |
| POS9962 | EXCLUDED |  |
| BSM 06/27 | EXCLUDED |  |
| GSHPT91/2025 | EXCLUDED |  |
| E3445GCDMWP | EXCLUDED |  |
| E2896GXMPARNR | EXCLUDED |  |
| RE-ADVERT RFP OW-015/2026/27 | EXCLUDED |  |
| ERRATUM- SCMU5-26-27-0008 CHR | EXCLUDED |  |
| RFB 3287/2026 -(ERP NO 499010) | EXCLUDED |  |
| REQ0006100- READVERT | EXCLUDED |  |
| RFQ - 12353 | PHAKATHI | Equipment, instrumentation and integration |
| E2182GXMPGROR | EXCLUDED |  |
| SCMU5-26/27-0006 CHR | EXCLUDED |  |
| SCMU5-26/27-0008 CHR | EXCLUDED |  |
| 2026/047 | EXCLUDED |  |
| RFP14/2026 | EXCLUDED |  |
| NLM-EXT-26/023 | EXCLUDED |  |
| SCMU5-26/27-0005 CHR | EXCLUDED |  |
| SCMU5-26/27-0007 CHR | EXCLUDED |  |
| AHT26999 | EXCLUDED |  |
| 07/2026/2027 | EXCLUDED |  |
| E3364NTCSAMWP | EXCLUDED |  |
| E3378GXMPMAT | EXCLUDED |  |
| RFQ1940632 | EXCLUDED |  |
| E3374GXMPARN | EXCLUDED |  |
| FOSRBY-RFP-05-26/27 | EXCLUDED |  |
| E3157GXMPGRO | EXCLUDED |  |
| E3286CXMWP | EXCLUDED |  |
| RFP63/2026 | EXCLUDED |  |
| 002-2025-26 | EXCLUDED |  |
| TFR/2026/08/0002/114631/RFP | EXCLUDED |  |
| FOSRBY-RFP-10-26/27 | EXCLUDED |  |
| RFP OW-015/2026/27 | EXCLUDED |  |
| NT001 | MEXEL | Cooling-water chemistry |
| NT004 | REICON_ODACON | Water and steam-cycle chemistry |

NT001 and NT004 remain provenance concerns from the previous review; historical/seed records are not asserted to be live opportunities. The original snapshot is unchanged.

## Active checkout cleanup

Integrated into /Users/lazolasonqishe/tender-intelligence on cleanup/current-portfolio based on origin/main. Preserved the locally reviewed UI refresh (PR #2 is open and unmerged), RunAtLoad setting and daily duplicate-run guard. Original 62-row snapshot, working tree and database are backed up outside the repository. Current published snapshot has 4 candidates: 1 open and 3 closed. 56 out-of-scope records removed from publication; NT001 and NT004 quarantined as unverified (generic source labels and search URLs, no original advert). Source sync timestamp retained; this was not a fresh scan. Operational database and installed schedules untouched. Superseded root plan archived; temporary review worktrees removed after preserving changes in Git stash. Final Python suite: 268 passed; dashboard: 35 tests, lint/typecheck and browser smoke passed. No commit, push, merge or external deployment.
