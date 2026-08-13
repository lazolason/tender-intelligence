#!/usr/bin/env python3
# ==========================================================
# CHROMEDRIVER SETUP AND DOWNLOADER
# Automatically downloads and installs correct version
# ==========================================================

import os
import sys
import json
import platform
import subprocess
import zipfile
import urllib.request
from pathlib import Path

# Add tools dir to path
sys.path.insert(0, str(Path(__file__).parent))
from chromedriver_manager import (
    DRIVER_DIR, PLATFORM, SYSTEM, DRIVER_EXT,
    get_chrome_version, get_installed_chromedriver_version,
    VERSION_LOCK_FILE, save_version_lock, print_driver_info
)

# Chrome for Testing (official Google binary)
CHROME_FOR_TESTING_URL = "https://googlechromelabs.github.io/chrome-for-testing"
DOWNLOAD_BASE = "https://storage.googleapis.com/chrome-for-testing-public"


def _load_json(url):
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read())


def _has_platform_download(entry, *, binary="chromedriver"):
    downloads = (entry.get("downloads") or {}).get(binary, [])
    return any(item.get("platform") == PLATFORM for item in downloads)


def download_chromedriver(version):
    """
    Download chromedriver for given version from Chrome for Testing
    """
    print(f"\n📥 Downloading chromedriver {version} for {PLATFORM}...")
    DRIVER_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download URL format
    download_url = f"{DOWNLOAD_BASE}/{version}/{PLATFORM}/chromedriver-{PLATFORM}.zip"
    
    temp_zip = DRIVER_DIR / "chromedriver.zip"
    driver_exe = DRIVER_DIR / f"chromedriver{DRIVER_EXT}"
    
    try:
        print(f"   URL: {download_url}")
        with urllib.request.urlopen(download_url, timeout=60) as resp:
            data = resp.read()
        with open(temp_zip, "wb") as f:
            f.write(data)
        print(f"   ✅ Downloaded")
        
        # Extract
        print(f"   Extracting...")
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            zip_ref.extractall(DRIVER_DIR)
        
        # Move to expected location (Chrome for Testing packages in subdirs)
        extracted_driver = None
        for item in DRIVER_DIR.rglob(f"chromedriver{DRIVER_EXT}"):
            if item != driver_exe:
                extracted_driver = item
                break
        
        if extracted_driver and extracted_driver != driver_exe:
            extracted_driver.replace(driver_exe)
        
        # Make executable
        if SYSTEM != "Windows":
            os.chmod(str(driver_exe), 0o755)
        
        # Clean up zip
        temp_zip.unlink()
        
        print(f"   ✅ Installed to {driver_exe}")
        return True
        
    except Exception as e:
        print(f"   ❌ Download failed: {e}")
        if temp_zip.exists():
            temp_zip.unlink()
        return False


def find_matching_version():
    """
    Find closest matching chromedriver version from Chrome for Testing
    """
    chrome_major, chrome_full, _ = get_chrome_version()
    
    if not chrome_major:
        print("❌ Chrome not found. Cannot determine driver version.")
        return None
    
    chrome_build = ".".join(str(chrome_full).split(".")[:3]) if chrome_full else ""
    print(f"\n🔍 Looking for chromedriver matching Chrome {chrome_full}...")
    
    try:
        data = _load_json(
            f"{CHROME_FOR_TESTING_URL}/latest-patch-versions-per-build-with-downloads.json"
        )
        build_entry = (data.get("builds") or {}).get(chrome_build)
        if build_entry and build_entry.get("version") and _has_platform_download(build_entry):
            version = build_entry["version"]
            print(f"   ✅ Exact build match found: {version}")
            return version
    except Exception as e:
        print(f"   ❌ Failed to fetch build-specific versions: {e}")

    try:
        data = _load_json(
            f"{CHROME_FOR_TESTING_URL}/latest-versions-per-milestone-with-downloads.json"
        )
        milestone = (data.get("milestones") or {}).get(str(chrome_major))
        if milestone and milestone.get("version") and _has_platform_download(milestone):
            version = milestone["version"]
            print(f"   ✅ Milestone match found: {version}")
            return version
        print(f"   ⚠️  No exact milestone match for Chrome {chrome_major}")
    except Exception as e:
        print(f"   ❌ Failed to fetch milestone versions: {e}")

    # Fallback to known good versions list
    try:
        data = _load_json(
            f"{CHROME_FOR_TESTING_URL}/known-good-versions-with-downloads.json",
        )
        versions = data.get("versions", [])

        # Try to match the full build first.
        for entry in reversed(versions):
            if entry.get("version", "").startswith(f"{chrome_build}.") and _has_platform_download(entry):
                print(f"   ✅ Fallback matched build {chrome_build}: {entry['version']}")
                return entry["version"]

        # Try to match milestone exactly
        for entry in versions:
            if str(entry.get("version", "")).startswith(f"{chrome_major}.") and entry.get("version") and _has_platform_download(entry):
                print(f"   ✅ Fallback matched milestone {chrome_major}: {entry['version']}")
                return entry["version"]

        # Otherwise use most recent version that has our platform binary
        for entry in reversed(versions):
            if _has_platform_download(entry) and entry.get("version"):
                print(f"   ✅ Fallback using available version: {entry['version']}")
                return entry["version"]
    except Exception as e:
        print(f"   ❌ Fallback fetch failed: {e}")

    return None


def setup_chromedriver():
    """
    Main setup function: download and verify chromedriver
    """
    print("\n" + "=" * 60)
    print("🔧 CHROMEDRIVER SETUP")
    print("=" * 60)
    
    # Check current state
    chrome_major, chrome_full, _ = get_chrome_version()
    result = get_installed_chromedriver_version()
    driver_major, driver_full = result if result else (None, None)
    
    if not chrome_major:
        print("❌ Chrome browser not found. Please install Chrome first.")
        sys.exit(1)
    
    # If already aligned, we're done
    if driver_major and driver_major == chrome_major:
        print(f"✅ Chromedriver already aligned with Chrome {chrome_full}")
        print_driver_info()
        return True
    
    if driver_major and driver_major != chrome_major:
        print(f"⚠️  Updating chromedriver: {driver_full} → Chrome {chrome_major}")
    else:
        print(f"📦 Installing chromedriver for Chrome {chrome_full}")
    
    # Find matching version
    version = find_matching_version()
    if not version:
        print("❌ Could not find matching chromedriver version")
        return False
    
    # Download and install
    if not download_chromedriver(version):
        print("❌ Installation failed")
        return False
    
    # Verify
    new_major, new_full = get_installed_chromedriver_version()
    if new_major == chrome_major:
        print(f"\n✅ SUCCESS: Chromedriver {new_full} installed and aligned")
        
        # Save version lock
        lock_data = {
            "chrome_version": chrome_full,
            "driver_version": new_full,
            "timestamp": str(Path(__file__).stat().st_mtime),
            "platform": PLATFORM
        }
        save_version_lock(lock_data)
        
        print_driver_info()
        return True
    else:
        print(f"❌ Verification failed: Driver still misaligned")
        return False


if __name__ == "__main__":
    success = setup_chromedriver()
    sys.exit(0 if success else 1)
