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
DOWNLOAD_BASE = "https://edgedl.me.chromium.org/chrome/chrome-for-testing"


def download_chromedriver(version):
    """
    Download chromedriver for given version from Chrome for Testing
    """
    print(f"\n📥 Downloading chromedriver {version} for {PLATFORM}...")
    
    # Download URL format
    download_url = f"{DOWNLOAD_BASE}/{version}/{PLATFORM}/chromedriver-{PLATFORM}.zip"
    
    temp_zip = DRIVER_DIR / "chromedriver.zip"
    driver_exe = DRIVER_DIR / f"chromedriver{DRIVER_EXT}"
    
    try:
        print(f"   URL: {download_url}")
        urllib.request.urlretrieve(download_url, str(temp_zip))
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
    
    print(f"\n🔍 Looking for chromedriver matching Chrome {chrome_major}.x...")
    
    try:
        # Fetch available versions
        response = urllib.request.urlopen(f"{CHROME_FOR_TESTING_URL}/api/v1/latest-versions-per-milestone")
        data = json.loads(response.read())
        
        for milestone in data.get("milestones", []):
            if str(milestone["milestone"]) == chrome_major:
                version = milestone["version"]
                print(f"   ✅ Found version {version}")
                return version
        
        print(f"   ⚠️  No exact match for Chrome {chrome_major}")
        return None
        
    except Exception as e:
        print(f"   ❌ Failed to fetch versions: {e}")
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
