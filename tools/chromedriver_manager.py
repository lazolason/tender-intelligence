#!/usr/bin/env python3
# ==========================================================
# CHROMEDRIVER MANAGER
# Manages driver version alignment with Chrome browser
# Isolates driver in ./tools/chromedriver/ for reproducibility
# ==========================================================

import os
import sys
import json
import subprocess
import platform
from pathlib import Path
from datetime import datetime

# Configuration
TOOLS_DIR = Path(__file__).parent
DRIVER_DIR = TOOLS_DIR / "chromedriver"
DRIVER_DIR.mkdir(parents=True, exist_ok=True)

VERSION_LOCK_FILE = DRIVER_DIR / "version_lock.json"

# Platform detection
SYSTEM = platform.system()  # Darwin (macOS), Linux, Windows
MACHINE = platform.machine()  # arm64, x86_64, etc.

# Supported platforms
PLATFORM_MAP = {
    ("Darwin", "arm64"): "mac-arm64",
    ("Darwin", "x86_64"): "mac-x64",
    ("Linux", "x86_64"): "linux64",
    ("Linux", "aarch64"): "linux-arm64",
    ("Windows", "AMD64"): "win64",
}

PLATFORM_KEY = (SYSTEM, MACHINE)
if PLATFORM_KEY not in PLATFORM_MAP:
    print(f"❌ Unsupported platform: {SYSTEM} {MACHINE}")
    sys.exit(1)

PLATFORM = PLATFORM_MAP[PLATFORM_KEY]

# File extensions
DRIVER_EXT = ".exe" if SYSTEM == "Windows" else ""


def get_chrome_version():
    """Get installed Chrome/Chromium version"""
    chrome_paths = {
        "Darwin": [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/usr/local/bin/google-chrome",
            "/usr/local/bin/chromium",
        ],
        "Linux": [
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/snap/bin/chromium",
        ],
        "Windows": [
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        ],
    }

    for path in chrome_paths.get(SYSTEM, []):
        if os.path.exists(path):
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                version_str = result.stdout.strip()
                # Extract version number: "Google Chrome 143.0.7499.40" → "143"
                parts = version_str.split()
                if parts:
                    version_num = parts[-1]  # Get last part (full version)
                    major_version = version_num.split(".")[0]  # Get major version
                    return major_version, version_num, path
            except Exception as e:
                pass

    # Try via 'which' or 'command' as fallback
    try:
        result = subprocess.run(
            ["which", "google-chrome"] if SYSTEM != "Windows" else ["where", "chrome"],
            capture_output=True,
            text=True,
            timeout=5
        )
        chrome_path = result.stdout.strip()
        if chrome_path and os.path.exists(chrome_path):
            result = subprocess.run(
                [chrome_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version_str = result.stdout.strip()
            parts = version_str.split()
            if parts:
                version_num = parts[-1]
                major_version = version_num.split(".")[0]
                return major_version, version_num, chrome_path
    except Exception:
        pass

    return None, None, None


def get_installed_chromedriver_version():
    """Get version of installed chromedriver binary"""
    driver_path = DRIVER_DIR / f"chromedriver{DRIVER_EXT}"
    
    if not driver_path.exists():
        return None
    
    try:
        result = subprocess.run(
            [str(driver_path), "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        version_str = result.stdout.strip()
        # Extract version: "ChromeDriver 143.0.7444.175 ..." → "143"
        parts = version_str.split()
        if len(parts) >= 2:
            version_num = parts[1]
            major_version = version_num.split(".")[0]
            return major_version, version_num
    except Exception as e:
        pass

    return None, None


def load_version_lock():
    """Load version lock info"""
    if VERSION_LOCK_FILE.exists():
        try:
            with open(VERSION_LOCK_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    
    return {}


def save_version_lock(data):
    """Save version lock info"""
    try:
        with open(VERSION_LOCK_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️  Failed to save version lock: {e}")


def verify_driver_alignment():
    """
    Check if chromedriver and Chrome versions are aligned.
    Returns: (aligned: bool, chrome_major, driver_major, message)
    """
    chrome_major, chrome_full, chrome_path = get_chrome_version()
    result = get_installed_chromedriver_version()
    driver_major, driver_full = result if result else (None, None)

    if not chrome_major:
        return False, None, None, f"❌ Chrome not found on system"

    if not driver_major:
        return False, chrome_major, None, f"❌ Chromedriver not installed at {DRIVER_DIR}"

    aligned = chrome_major == driver_major
    
    if aligned:
        message = f"✅ Versions aligned: Chrome {chrome_full} | Driver {driver_full}"
    else:
        message = f"⚠️  Version mismatch: Chrome {chrome_major} ({chrome_full}) vs Driver {driver_major} ({driver_full})"

    return aligned, chrome_major, driver_major, message


def print_driver_info():
    """Print chromedriver setup information"""
    print("\n" + "=" * 60)
    print("🔧 CHROMEDRIVER SETUP INFO")
    print("=" * 60)
    
    chrome_major, chrome_full, chrome_path = get_chrome_version()
    result = get_installed_chromedriver_version()
    driver_major, driver_full = result if result else (None, None)
    
    print(f"\nSystem: {SYSTEM} {MACHINE} ({PLATFORM})")
    print(f"Driver location: {DRIVER_DIR}")
    
    if chrome_path:
        print(f"\n📍 Chrome: {chrome_path}")
        print(f"   Version: {chrome_full} (Major: {chrome_major})")
    else:
        print(f"\n❌ Chrome not found")
    
    if driver_major:
        print(f"\n📍 Chromedriver: {DRIVER_DIR / f'chromedriver{DRIVER_EXT}'}")
        print(f"   Version: {driver_full} (Major: {driver_major})")
    else:
        print(f"\n❌ Chromedriver not installed")
    
    aligned, c_maj, d_maj, msg = verify_driver_alignment()
    print(f"\n{msg}")
    
    print("\n" + "=" * 60 + "\n")
    
    return aligned


def get_driver_path():
    """Return path to isolated chromedriver binary"""
    driver_path = DRIVER_DIR / f"chromedriver{DRIVER_EXT}"
    
    if not driver_path.exists():
        print(f"\n❌ Chromedriver not found at {driver_path}")
        print("   Run: python tools/setup_chromedriver.py")
        return None
    
    return str(driver_path)


def setup_environment():
    """Set up environment for Selenium to find driver"""
    driver_path = DRIVER_DIR / f"chromedriver{DRIVER_EXT}"
    
    if driver_path.exists():
        # Make executable (Unix-like)
        if SYSTEM != "Windows":
            os.chmod(str(driver_path), 0o755)
        
        # Add to PATH so Selenium can find it
        current_path = os.environ.get("PATH", "")
        if str(DRIVER_DIR) not in current_path:
            os.environ["PATH"] = f"{DRIVER_DIR}:{current_path}"


if __name__ == "__main__":
    print_driver_info()
