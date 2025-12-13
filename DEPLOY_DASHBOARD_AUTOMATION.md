# Dashboard Auto-Sync (Recommended)

The deployed dashboard reads `vercel-dashboard/tenders.json` from the same Vercel site. Because it’s a static asset, it only changes when the file is updated in Git and redeployed.

This repo includes a GitHub Actions workflow that automatically rebuilds and commits `vercel-dashboard/tenders.json` on a schedule, which triggers Vercel’s auto-deploy.

## Workflow

- File: `.github/workflows/update-dashboard-tenders.yml`
- Schedule: daily at **06:05 UTC** (≈ **08:05 SAST**)
- Manual run: GitHub → Actions → “Update dashboard tenders.json” → Run workflow

The workflow:
1. Checks out `main`
2. Installs Python deps from `requirements.txt`
3. Runs `python tools/build_dashboard_snapshot.py`
4. Commits + pushes `vercel-dashboard/tenders.json` if it changed

## Notes

- The snapshot builder uses **non-Selenium** scrapers for CI stability.
- If all scrapes return zero tenders, the script **does not overwrite** the existing `vercel-dashboard/tenders.json` (prevents wiping the dashboard due to transient failures).

## Required GitHub settings

- Repo → Settings → Actions → General → Workflow permissions:
  - Set to **Read and write permissions**

