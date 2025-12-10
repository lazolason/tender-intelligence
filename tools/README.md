# Tools for Chromedriver Management & Verification

This directory contains utilities for managing the Selenium chromedriver binary with version alignment checks.

## Files

- **`chromedriver_manager.py`** – Core driver management library
  - Version detection (Chrome & Chromedriver)
  - Alignment verification
  - Isolated driver path management
  - Environment setup

- **`setup_chromedriver.py`** – Automated driver installer
  - Detects Chrome version
  - Downloads matching chromedriver from Chrome for Testing
  - Installs to isolated `./tools/chromedriver/` directory
  - Verifies alignment

- **`preflight_check.py`** – Pre-scrape validation
  - Checks driver availability
  - Verifies version alignment
  - Warns of mismatches before scraping starts

## Quick Start

### Initial Setup

```bash
cd /Users/lazolasonqishe/Documents/tender-intelligence
python tools/setup_chromedriver.py
```

This will:
1. Detect your Chrome version (e.g., 143)
2. Download matching chromedriver
3. Install to `tools/chromedriver/` (isolated from system)
4. Verify alignment

### Before Each Scraper Run

```bash
python tools/preflight_check.py
```

This validates that your driver is ready and warns of version mismatches.

### Manual Version Check

```bash
python tools/chromedriver_manager.py
```

Displays:
- Chrome version & path
- Chromedriver version & path
- Alignment status

## How It Works

### Isolation
- Driver is stored in **`./tools/chromedriver/`** (not system PATH)
- Prevents conflicts with system/global drivers
- Reproducible across environments (CI/servers)

### Alignment
- Detects Chrome major version (e.g., `143.0.7499.40` → `143`)
- Finds matching chromedriver from Chrome for Testing API
- Fails fast if versions diverge

### Environment Setup
- `chromedriver_manager.py` adds driver dir to `PATH` automatically
- Scrapers use `Service(driver_path)` for explicit control
- No reliance on system chromedriver

## Troubleshooting

### "Chromedriver not found"
```bash
python tools/setup_chromedriver.py
```

### "Version mismatch" warning
```bash
python tools/setup_chromedriver.py
```

### Selenium timeouts / flaky scrapes
Usually caused by version mismatch. Run setup script and verify alignment:
```bash
python tools/preflight_check.py
```

## Chrome Updates

When Chrome auto-updates (e.g., 143 → 144), run setup again:
```bash
python tools/setup_chromedriver.py
```

The script will automatically download the new matching driver.

## CI/CD Integration

For servers/CI, ensure `setup_chromedriver.py` runs on deployment:

```bash
# In your CI config (e.g., Render Procfile, GitHub Actions)
python tools/setup_chromedriver.py && python daily_runner.py
```

This ensures the driver is always aligned, even after Chrome auto-updates.

## Platform Support

- **macOS** (arm64, x86_64)
- **Linux** (x86_64, aarch64)
- **Windows** (x86_64)

---

For more details, see `scraper/national_treasury_selenium.py` and `daily_runner.py`.
