# 🚀 TenderScan Deployment Guide

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

### Step 3: Configure Environment Variables

In Render dashboard, set these environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `SMTP_SERVER` | Email server | `smtp.gmail.com` |
| `SMTP_PORT` | Email port | `587` |
| `SENDER_EMAIL` | Your email | `tenderscan@gmail.com` |
| `SENDER_PASSWORD` | App password | (from Gmail settings) |
| `RECIPIENT_EMAILS` | Recipients | `you@email.com,team@email.com` |

### Gmail App Password Setup

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Factor Authentication
3. Go to App Passwords
4. Generate password for "Mail"
5. Use this password in `SENDER_PASSWORD`

---

## Local Scheduling (macOS)

### Option A: Using cron

```bash
# Edit crontab
crontab -e

# Add these lines (runs at 6 AM daily, 7 AM Monday)
0 6 * * * cd ~/Documents/MASTER/TENDERS/00_System/04_Automation && /usr/bin/python3 daily_runner.py >> /tmp/tenderscan.log 2>&1
0 7 * * 1 cd ~/Documents/MASTER/TENDERS/00_System/04_Automation && /usr/bin/python3 weekly_report.py >> /tmp/tenderscan.log 2>&1
```

### Option B: Using launchd (Recommended for macOS)

Create `~/Library/LaunchAgents/com.tenderscan.daily.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.tenderscan.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/lazolasonqishe/Documents/MASTER/TENDERS/00_System/04_Automation/daily_runner.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/tenderscan-daily.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/tenderscan-daily-error.log</string>
</dict>
</plist>
```

Load the scheduler:
```bash
launchctl load ~/Library/LaunchAgents/com.tenderscan.daily.plist
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard home |
| `/health` | GET | Health check |
| `/api/stats` | GET | Tender statistics |
| `/api/tenders` | GET | List recent tenders |
| `/api/score` | POST | Score a tender |
| `/run/daily` | GET | Trigger daily scan |
| `/run/weekly` | GET | Generate weekly report |
| `/report/weekly` | GET | View weekly dashboard |

### Example: Score a Tender via API

```bash
curl -X POST https://your-app.onrender.com/api/score \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Cooling Water Treatment Chemicals",
    "description": "Supply of scale inhibitors for power station",
    "client": "Eskom",
    "closing_date": "2025-12-15"
  }'
```

---

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Access at http://localhost:5000
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
- Local: `/tmp/tenderscan.log`
