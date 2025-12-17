# Production Deployment Guide

## Overview

This guide covers deploying the Tender Intelligence System with AI Summarization to production (Render cloud platform).

## Pre-Deployment Checklist

- [ ] Verify no sensitive data in git history
- [ ] All environment variables configured in Render dashboard
- [ ] Anthropic API key created with billing enabled
- [ ] Flask server tested locally
- [ ] Dashboard tested in production browser

## Environment Variables

### Required for AI Summarization

```bash
ANTHROPIC_API_KEY=sk-ant-...          # Your Anthropic API key (KEEP SECRET)
ANTHROPIC_MODEL=claude-sonnet-4-20250514  # Claude model version
PORT=5000                             # Flask server port
```

### Optional

```bash
ENABLE_SELENIUM=false                 # Disable Selenium scrapers on cloud
OUTPUT_DIR=./output                   # JSON output directory
TENDERSCAN_EMAIL_ENABLED=false        # Email alerts
DEBUG=false                           # Never enable in production
```

## Getting Anthropic API Key

1. Go to [Anthropic Console](https://console.anthropic.com)
2. Sign in or create account
3. Navigate to **API Keys** section
4. Click **Create Key**
5. Copy the key (starts with `sk-ant-`)
6. **IMPORTANT:** Add billing/credits to your account at [Plans & Billing](https://console.anthropic.com/account/billing/overview)
7. Verify credit balance before deploying

## Deploying to Render

### Step 1: Create .env File Locally

```bash
# Copy template
cp .env.example .env

# Edit .env with your values
# DO NOT commit .env to git
nano .env
```

### Step 2: Configure Render Dashboard

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Create new **Web Service** (or update existing)
3. Connect to GitHub repository
4. In **Environment** tab, add these variables:

| Variable | Value |
|----------|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` (your actual key) |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` |
| `PORT` | `5000` |
| `ENABLE_SELENIUM` | `false` |
| `DEBUG` | `false` |

### Step 3: Deploy

```bash
# Push to main branch
git add .
git commit -m "DEPLOYMENT: Add production environment variables"
git push origin main

# Render auto-deploys on main branch push
# Monitor deployment in Render dashboard
```

### Step 4: Verify Deployment

```bash
# Test API endpoint
curl -X POST https://<your-render-app>.onrender.com/api/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "tender": {
      "title": "Test Tender",
      "description": "Test description"
    }
  }'

# Expected response:
# {"summary": "• Scope of work...\n• Key requirements...\n• Deadlines..."}
```

## Security Best Practices

### ✅ DO

- Store API keys in Render environment variables only
- Use `.env.example` with placeholder values
- Add `.env` to `.gitignore` (already configured)
- Rotate API keys periodically
- Monitor API usage in Anthropic Console
- Enable billing alerts in Anthropic Console

### ❌ DON'T

- Commit `.env` file to git
- Hardcode API keys in code
- Log sensitive data
- Use development/test keys in production
- Share API keys in chat/email/Slack

### Verify No Secrets in Git

```bash
# Check git history for exposed keys
git log --all -p | grep -i "sk-ant"

# Should return nothing if properly secured
```

## Architecture

### Flask Backend (`app.py`)

- **Endpoint:** `POST /api/summarize`
- **Port:** 5000 (configurable via `PORT` env var)
- **Authentication:** None (server-side proxy to Claude API)
- **Rate Limiting:** None configured (implement if needed)

### Request Format

```json
{
  "tender": {
    "title": "Tender title",
    "description": "Tender description",
    "client": "Optional client name",
    "category": "Optional category",
    "ref": "Optional reference"
  }
}
```

### Response Format

```json
{
  "summary": "• Bullet point 1\n• Bullet point 2\n• Bullet point 3"
}
```

### Error Responses

```json
{
  "error": "API key not configured on server",
  "details": {
    "error": {
      "message": "Your credit balance is too low...",
      "type": "invalid_request_error"
    }
  }
}
```

## API Costs

Each summary request costs ~1-2 tokens × 2 input + 1-2 tokens × 15 output.

**Estimated costs:**
- 100 summaries/month: $0.01-0.05
- 1,000 summaries/month: $0.10-0.50
- 10,000 summaries/month: $1-5

See [Anthropic Pricing](https://www.anthropic.com/pricing) for latest rates.

## Troubleshooting

### 502 Bad Gateway

**Cause:** API key missing or invalid
**Solution:**
1. Check ANTHROPIC_API_KEY is set in Render env vars
2. Verify key format starts with `sk-ant-`
3. Ensure credits added to account

### Timeout Errors

**Cause:** Claude API slow or overloaded
**Solution:**
1. API has 60s timeout (configurable in `app.py:425`)
2. Retry with exponential backoff
3. Contact Anthropic support if persistent

### Permission Denied

**Cause:** API key lacks credits
**Solution:**
1. Go to [Plans & Billing](https://console.anthropic.com/account/billing/overview)
2. Add payment method
3. Purchase credits or enable auto-billing
4. Wait 5-10 minutes for propagation

## Monitoring

### Check Render Logs

```bash
# In Render dashboard, click Logs tab
# Filter for "POST /api/summarize"
```

### Monitor API Usage

1. Go to [Anthropic Console](https://console.anthropic.com)
2. Click **Usage** tab
3. View requests, tokens, costs
4. Set billing alerts

## Rollback

If deployment fails:

```bash
# In Render dashboard
# 1. Click "Environment" tab
# 2. Click "Rollback" button
# 3. Select previous working deployment
# 4. Click "Rollback"
```

## Next Steps

- [ ] Add rate limiting middleware
- [ ] Implement caching (Redis)
- [ ] Add model selection dropdown
- [ ] Set up monitoring/alerting
- [ ] Add auto-retry logic
- [ ] Configure CORS properly

---

**Last Updated:** Dec 17, 2025
**Deployed By:** Claude Code
**Status:** Production Ready ✅
