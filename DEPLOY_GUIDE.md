# 🚀 TenderScan Deployment Guide

## ⚠️ Chromedriver Setup (CRITICAL for Scrapers)

**Before any scraping,** the chromedriver must be installed and aligned with your Chrome version.

### Initial Setup

```bash
python tools/setup_chromedriver.py
```

This automatically:
- Detects your Chrome version (e.g., 143.0.7499.40)
- Downloads matching chromedriver from Chrome for Testing
- Installs to `tools/chromedriver/` (isolated, not system-wide)
- Verifies alignment

### Environment Configuration

Configure your environment variables before running any scripts:

1. **Copy the template**:
   ```bash
   cp .env.example .env
   ```

2. **Configure required variables** in `.env`:
   - `SMTP_USER`: Your Gmail address
   - `SMTP_PASSWORD`: Gmail App Password
   - `DB_PATH`: Path to SQLite database (default: `data/tenders.db`)

The system uses `python-dotenv` to automatically load these values. Validation is performed on startup.

### Pre-Scrape Verification

Before running scrapers, verify driver readiness:

```bash
python tools/preflight_check.py
```

Outputs:
- Driver installed status ✅/❌
- Chrome ↔ Chromedriver version alignment ✅/⚠️
- Warnings about mismatches that cause Selenium flakiness

### When Chrome Updates

When Chrome auto-updates (e.g., 143 → 144):
```bash
python tools/setup_chromedriver.py
```

The script automatically detects the new version and downloads the matching driver.

**For details:** see `tools/README.md`

---

## Cloud Deployment on Render

### Step 1: Prepare Repository

1. Create a new GitHub repository
2. Push your `04_Automation` folder contents:

```bash
cd ~/Documents/MASTER/TENDERS/00_System/04_Automation
git init
git add .
git commit -m "TenderScan AI Engine v1.0"
git remote add origin https://github.com/YOUR_USERNAME/tenderscan.git
git push -u origin main
```

### Step 2: Deploy to Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New** → **Blueprint**
3. Connect your GitHub repository
4. Render will detect `render.yaml` automatically
5. Click **Apply**

### Step 3: Configure Chromedriver on Render

Update your `render.yaml` to run chromedriver setup during build:

```yaml
services:
  - type: web
    name: tender-intelligence
    env: python
    buildCommand: |
      pip install -r requirements.txt
      python tools/setup_chromedriver.py
    startCommand: gunicorn app:app
```

This ensures the driver is automatically downloaded and aligned on every deploy, even after Chrome auto-updates on the server.

### Step 4: Configure Environment Variables

In Render dashboard, set these environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `SMTP_SERVER` | Email server | `smtp.gmail.com` |
| `SMTP_PORT` | Email port | `587` |
| `SMTP_USER` | SMTP login username | `tenderscan@gmail.com` |
| `SMTP_PASSWORD` | App password | (from Gmail settings) |
| `EMAIL_FROM` | Sender address | `tenderscan@gmail.com` |
| `EMAIL_TO` | Recipients | `you@email.com,team@email.com` |
| `DB_PATH` | SQLite database path | `data/tenders.db` |
| `DASHBOARD_URL` | Public dashboard URL | `http://localhost:5001/` |

### Gmail App Password Setup

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication
3. Go to App Passwords
4. Generate password for "Mail"
5. Use this password in `SMTP_PASSWORD`

---

## Local Scheduling (macOS)

### Option A: Using cron

```bash
# Edit crontab
crontab -e

# Add these lines after creating .venv; replace the checkout path (runs at 08:00 daily, 09:00 Monday)
0 8 * * * cd "/absolute/path/to/tender-intelligence" && .venv/bin/python daily_runner.py >> logs/daily_scan.log 2>&1
0 9 * * 1 cd "/absolute/path/to/tender-intelligence" && .venv/bin/python weekly_report.py >> logs/weekly_report.log 2>&1
```

### Option B: Using launchd (Recommended for macOS)

The bundled plists are templates. Render them for the current checkout rather
than copying them directly, then review and bootstrap the rendered files:

```bash
.venv/bin/python tools/install_launchd_jobs.py
.venv/bin/python tools/install_launchd_jobs.py --install
plutil -lint ~/Library/LaunchAgents/com.tenderscan.app.plist
plutil -lint ~/Library/LaunchAgents/com.tenderscan.daily.plist
plutil -lint ~/Library/LaunchAgents/com.tenderscan.weekly.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.tenderscan.app.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.tenderscan.daily.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.tenderscan.weekly.plist
```

The app service keeps the dashboard and API live at `http://localhost:5001/`, while the daily and weekly jobs run on schedule.

The installer refuses to overwrite existing jobs unless you rerun it with
`--install --force`; stop or unload an existing job explicitly before replacing
it. Validate the templates for this checkout with `.venv/bin/python
utils/launchd_validator.py`.

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard home |
| `/health` | GET | Health check |
| `/api/tenders` | GET | List recent tender snapshot records |
| `/api/stats/bids` | GET | Bid outcome statistics |
| `/api/bids` | POST | Record a bid outcome (API key required) |
| `/api/summarize` | POST | Summarize a tender (API key and OpenAI key required) |
| `/api/run/daily` | POST | Trigger daily scan (API key required) |
| `/api/run/weekly` | POST | Generate weekly report (API key required) |
| `/cron/daily` | POST | Scheduler daily trigger (API key required) |
| `/cron/weekly` | POST | Scheduler weekly trigger (API key required) |

Protected endpoints fail closed with HTTP 503 when `API_KEY` is not configured. Send the key as `Authorization: Bearer <key>` or `X-API-Key: <key>`. Cross-origin API access is disabled unless `CORS_ORIGINS` explicitly lists trusted origins.

### Example: Trigger an authenticated daily scan

```bash
curl -X POST http://127.0.0.1:5001/api/run/daily \
  -H "Authorization: Bearer $API_KEY"
```

The service binds to `127.0.0.1` by default. Public deployment must terminate TLS at a trusted reverse proxy and should keep Gunicorn on loopback (for example, `GUNICORN_BIND=127.0.0.1:5001`). Expose Gunicorn directly only on a firewall-restricted private network.

Outbound scraper and document requests require HTTPS with certificate verification. Do not add `verify=False` workarounds. If your organization intercepts TLS, install its CA in the operating-system trust store or set `REQUESTS_CA_BUNDLE` to an approved PEM bundle. HTTP redirects to insecure or local/private literal-IP targets are rejected.

---

## CI/CD Pipeline

The project uses GitHub Actions for automated quality control:

- **Test and Lint**: Every push or pull request to `main` triggers a workflow that:
  - Runs `ruff` for code style and linting (line length limit: 120).
  - Runs `pytest` to execute all unit tests.
  - Checks code coverage and uploads reports to Codecov.

The workflow file is located at `.github/workflows/test-and-lint.yml`.

---

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
./serve_app.sh

# Access at http://localhost:5001
```

---

## Schedule Summary

| Task | Frequency | Time (SAST) | Description |
|------|-----------|-------------|-------------|
| Daily Scan | Daily | 08:00 | Scrape, score, email |
| Weekly Report | Monday | 09:00 | Generate dashboard |

---

## Support

For issues or questions, check the logs:
- Render: Dashboard → Logs
- Local app: `logs/app_server.log`
- Local daily job: `logs/daily_scan.log`
- Local weekly job: `logs/weekly_report.log`

For local app-service validation:

```bash
python3 utils/launchd_validator.py
curl http://localhost:5001/health
```
