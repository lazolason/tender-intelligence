# Production Deployment Guide

## Overview

This guide covers deploying the Tender Intelligence System to production using **Vercel** for the dashboard and a separate Flask API backend.

**Architecture Note:** This system uses a unified architecture with clear separation of concerns:
- **Frontend**: Vercel-hosted static PWA (no server-side rendering)
- **Backend**: Flask API-only service (no dashboard rendering)

## Architecture

### Components

1. **Vercel Dashboard** - Static PWA hosted on Vercel (https://vercel.com)
   - Advanced UI with PWA offline support, virtual scrolling, caching
   - Reads from static `/tenders.json` file
   - No external API dependencies

2. **Flask API** - Backend service for automation (self-hosted or cloud)
   - API endpoints: `/api/run/*`, `/cron/*`, `/health`
   - No dashboard rendering (removed for consolidation)
   - Optional component for automation triggers

3. **Local Automation** - Scheduled scans via launchd/cron

## Pre-Deployment Checklist

- [ ] Vercel account created
- [ ] GitHub repository connected to Vercel
- [ ] Dashboard tested locally (`cd vercel-dashboard && python3 -m http.server 8000`)
- [ ] Flask API tested locally (optional: `python app.py`)

## Part 1: Deploy Dashboard to Vercel

### Step 1: Sync Dashboard Data

```bash
# Run the sync script to generate dashboard files
python sync_to_vercel.py

# This creates:
# - vercel-dashboard/index.html (with embedded data)
# - vercel-dashboard/tenders.json (full dataset)
```

### Step 2: Push to GitHub

```bash
git add vercel-dashboard/
git commit -m "Update dashboard data"
git push origin main
```

### Step 3: Deploy on Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **Import Project**
3. Select your GitHub repository
4. Configure project:
   - **Framework Preset:** None (static site)
   - **Root Directory:** `vercel-dashboard/`
   - **Build Command:** (leave empty, no build needed)
   - **Output Directory:** `.` (root of vercel-dashboard)
5. Click **Deploy**

### Step 4: Verify Dashboard

Visit your Vercel URL (e.g., `https://your-project.vercel.app`)

- [ ] Dashboard loads
- [ ] Tenders display correctly
- [ ] Filters work
- [ ] PWA installs on mobile

## Part 2: Deploy Flask API (Optional)

The Flask API provides automation endpoints for scheduled scans. You can deploy it to:

- **Self-hosted VPS** (DigitalOcean, AWS EC2, etc.)
- **Platform-as-a-Service** (any Python hosting)
- **Local machine** (for testing only)

### Environment Variables

```bash
PORT=5000                            # Flask server port
ENABLE_SELENIUM=false                # Disable Selenium scrapers in production
DEBUG=false                          # Never enable in production
TENDERSCAN_EMAIL_ENABLED=false       # Email alerts configuration
```

### Self-Hosted Deployment

```bash
# On your server
git clone https://github.com/your-username/tender-intelligence.git
cd tender-intelligence

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Configure email and other settings

# Run with Gunicorn
gunicorn app:app --bind 0.0.0.0:5000 --workers 2 --timeout 120
```

### Using systemd (Linux)

Create `/etc/systemd/system/tender-api.service`:

```ini
[Unit]
Description=Tender Intelligence API
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/tender-intelligence
Environment="PATH=/path/to/tender-intelligence/venv/bin"
EnvironmentFile=/path/to/tender-intelligence/.env
ExecStart=/path/to/tender-intelligence/venv/bin/gunicorn app:app --bind 0.0.0.0:5000 --workers 2 --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable tender-api
sudo systemctl start tender-api
sudo systemctl status tender-api
```

## Part 3: Automate Dashboard Updates

### Local Automation (macOS)

Create `~/Library/LaunchAgents/com.tenderscan.sync.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tenderscan.sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/venv/bin/python</string>
        <string>/path/to/sync_to_vercel.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/tender-sync.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/tender-sync.error</string>
</dict>
</plist>
```

Load the job:
```bash
launchctl load ~/Library/LaunchAgents/com.tenderscan.sync.plist
```

This syncs daily at 8 AM and auto-pushes to GitHub → Vercel deploys.

## Security Best Practices

### ✅ DO

- Store API keys in environment variables only
- Use `.env.example` with placeholder values
- Add `.env` to `.gitignore` (already configured)
- Rotate API keys periodically
- Monitor API usage in provider console
- Enable billing alerts

### ❌ DON'T

- Commit `.env` file to git
- Hardcode API keys in code
- Log sensitive data
- Share API keys in chat/email/Slack
- Expose API keys in client-side JavaScript

### Verify No Secrets in Git

```bash
# Check git history for exposed keys
git log --all -p | grep -i "sk-ant"

# Should return nothing if properly secured
```

## Troubleshooting

### Dashboard not updating

**Symptoms:** Changes not visible on Vercel
**Solutions:**
1. Check `sync_to_vercel.py` completed successfully
2. Verify git push succeeded: `git log --oneline -5`
3. Check Vercel deployment status in dashboard
4. Hard refresh browser (Cmd+Shift+R)

### Timeout Errors

**Cause:** External API slow or overloaded
**Solutions:**
1. API has 60s timeout (configurable in `app.py:407`)
2. Check API provider status page
3. Retry request manually
4. Contact API provider support if persistent

### Permission Denied / 401

**Cause:** API key lacks credits or is invalid
**Solutions:**
1. Log into API provider console
2. Add payment method and purchase credits
3. Wait 5-10 minutes for changes to propagate
4. Regenerate API key if needed

## Monitoring

### Vercel Deployments

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your project
3. View **Deployments** tab for history
4. Check **Logs** for errors

### Flask API Logs

```bash
# If using systemd
sudo journalctl -u tender-api -f

# If using screen/tmux
screen -r tender-api  # View running session
```

## Next Steps

- [ ] Set up custom domain on Vercel
- [ ] Add rate limiting to Flask API
- [ ] Implement caching for summaries
- [ ] Configure CORS properly for production
- [ ] Set up monitoring/alerting (UptimeRobot, etc.)
- [ ] Add automated backups for tender data

---

**Last Updated:** December 18, 2025
**Status:** Production Ready ✅
