# 🔧 Chromedriver Setup Guide

## Quick Start

### 1. Install Chromedriver (First Time Only)

```bash
cd /Users/lazolasonqishe/Documents/tender-intelligence
python tools/setup_chromedriver.py
```

**What it does:**
- Detects your Chrome browser version
- Downloads matching chromedriver from Chrome for Testing (official Google)
- Installs to `tools/chromedriver/` (isolated, reproducible)
- Verifies alignment

**Output:**
```
✅ SUCCESS: Chromedriver 143.0.7244.125 installed and aligned
Chrome: /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
Version: 143.0.7499.40 (Major: 143)
Chromedriver: /Users/lazolasonqishe/Documents/tender-intelligence/tools/chromedriver/chromedriver
Version: 143.0.7244.125 (Major: 143)
✅ Versions aligned: Chrome 143 | Driver 143
```

### 2. Verify Before Scraping

Before running any scraper:

```bash
python tools/preflight_check.py
```

**Output (all good):**
```
✅ Checks passed. Ready to scrape!
[driver info...]
```

**Output (misaligned):**
```
⚠️  Version mismatch: Chrome 143 vs Driver 142
   This will likely cause Selenium flakiness.
   Fix: python tools/setup_chromedriver.py
```

### 3. Run Daily Scan

```bash
python daily_runner.py
```

The scraper now:
- Uses isolated driver at `tools/chromedriver/chromedriver`
- Verifies alignment on startup
- Warns if versions diverge
- Fails fast if driver not found

---

## Automatic Updates (When Chrome Updates)

Chrome auto-updates frequently (usually every 4 weeks). When it updates:

**Option A: Manual Update**
```bash
python tools/setup_chromedriver.py
```

**Option B: Automated (Recommended for CI/Servers)**

Update your CI config to run setup before each scrape:

**Render (render.yaml):**
```yaml
services:
  - type: cron
    name: daily-tender-scan
    runtime: python-3.11
    buildCommand: |
      pip install -r requirements.txt
      python tools/setup_chromedriver.py
    command: python daily_runner.py
    schedule: "0 6 * * *"  # 6 AM daily
```

**GitHub Actions (.github/workflows/scrape.yml):**
```yaml
- name: Setup Chromedriver
  run: python tools/setup_chromedriver.py
  
- name: Run Daily Scan
  run: python daily_runner.py
```

---

## Commands Reference

| Command | Purpose |
|---------|---------|
| `python tools/setup_chromedriver.py` | Download & install/update driver |
| `python tools/preflight_check.py` | Verify driver is ready (run before scraping) |
| `python tools/chromedriver_manager.py` | Show version info & status |

---

## Troubleshooting

### "Chrome not found"
Install Google Chrome from https://google.com/chrome

### "Chromedriver not found / Version mismatch"
```bash
python tools/setup_chromedriver.py
```

### Selenium timeouts / connection refused
Usually caused by version mismatch:
```bash
python tools/preflight_check.py  # Check status
python tools/setup_chromedriver.py  # Update if needed
```

### "ModuleNotFoundError: No module named 'tools'"
Ensure you're running scripts from project root:
```bash
cd /Users/lazolasonqishe/Documents/tender-intelligence
python tools/setup_chromedriver.py
```

---

## Under the Hood

### Driver Isolation
- Driver stored in `tools/chromedriver/` (not system PATH)
- Prevents conflicts with global/system drivers
- Reproducible across machines & CI

### Version Alignment
- Detects Chrome major version (e.g., `143.0.7499.40` → `143`)
- Downloads exact matching driver from Chrome for Testing
- Fails fast if versions diverge

### Startup Verification
- `national_treasury_selenium.py` checks versions on driver init
- Warns if misaligned (non-blocking)
- Uses explicit `Service(driver_path)` to control driver location

---

## Learn More

- [Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/) – Official driver source
- [DEPLOY_GUIDE.md](../DEPLOY_GUIDE.md) – Cloud deployment with driver setup
- [tools/README.md](./README.md) – Detailed API reference
