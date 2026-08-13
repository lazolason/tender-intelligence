#!/usr/bin/env python3
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
DRIVER_DIR = TOOLS_DIR / "chromedriver"
DRIVER_EXE = "chromedriver"

# Platform detection
SYSTEM = platform.system()
if SYSTEM == "Darwin":
    PLATFORM = "mac-x64" if platform.machine() == "x86_64" else "mac-arm64"
    DRIVER_EXT = ""
elif SYSTEM == "Linux":
    PLATFORM = "linux64"
    DRIVER_EXT = ""
elif SYSTEM == "Windows":
    PLATFORM = "win64"
    DRIVER_EXT = ".exe"
else:
    PLATFORM = "unknown"
    DRIVER_EXT = ""

VERSION_LOCK_FILE = DRIVER_DIR / "version_lock.json"



def get_chrome_version():
    """Get installed Chrome version"""
    try:
        if SYSTEM == "Darwin":
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            cmd = [chrome_path, "--version"]
        elif SYSTEM == "Linux":
            cmd = ["google-chrome", "--version"]
        elif SYSTEM == "Windows":
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            cmd = [chrome_path, "--version"]
        else:
            return None, None, None
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        version_str = result.stdout.strip().split()[-1]
        major = version_str.split(".")[0]
        return major, version_str, chrome_path if SYSTEM in ["Darwin", "Windows"] else "google-chrome"
    except Exception:
        return None, None, None

def get_installed_chromedriver_version():
    """Get installed chromedriver version"""
    driver_path = DRIVER_DIR / f"chromedriver{DRIVER_EXT}"
    if not driver_path.exists():
        return None, None
    
    try:
        cmd = [str(driver_path), "--version"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        version_str = result.stdout.strip().split()[1]
        major = version_str.split(".")[0]
        return major, version_str
    except Exception:
        return None, None

def save_version_lock(data):
    """Save version lock file"""
    DRIVER_DIR.mkdir(parents=True, exist_ok=True)
    with open(VERSION_LOCK_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _extract_major(version: str | None) -> str | None:
    if not version:
        return None
    return str(version).split(".")[0]

def get_system_driver_path():
    fallbacks = [
        "/opt/homebrew/bin/chromedriver",
        "/usr/local/bin/chromedriver",
        "/usr/bin/chromedriver",
    ]
    for path in fallbacks:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    try:
        cmd = ["which", "chromedriver"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        path = result.stdout.strip()
        if path and os.path.exists(path) and os.access(path, os.X_OK):
            return path
    except Exception:
        pass
    return None

def verify_driver_alignment():
    chrome_major, chrome_full, _ = get_chrome_version()
    driver_major, driver_full = get_installed_chromedriver_version()

    if not chrome_major:
        return False, None, driver_major, "Google Chrome not found"

    system_driver = get_system_driver_path()
    if not driver_major and system_driver:
        try:
            result = subprocess.run(
                [system_driver, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            tokens = result.stdout.strip().split()
            if len(tokens) >= 2:
                driver_full = tokens[1]
                driver_major = _extract_major(driver_full)
        except Exception:
            driver_major = driver_major or None

    if not driver_major:
        return (
            False,
            chrome_major,
            None,
            f"Chrome {chrome_full} detected but no chromedriver is installed",
        )

    if chrome_major == driver_major:
        return True, chrome_major, driver_major, "Chrome and Chromedriver are aligned"

    return (
        False,
        chrome_major,
        driver_major,
        f"Version mismatch: Chrome {chrome_full} vs Chromedriver {driver_full or driver_major}",
    )

def get_driver_path():
    local_path = DRIVER_DIR / DRIVER_EXE
    if local_path.exists() and os.access(local_path, os.X_OK):
        return str(local_path)
    return get_system_driver_path()

def setup_environment():
    driver_dir = str(DRIVER_DIR)
    system_driver = get_system_driver_path()
    parts = [driver_dir]
    if system_driver:
        parts.append(str(Path(system_driver).parent))
    path_env = os.environ.get("PATH", "")
    os.environ["PATH"] = os.pathsep.join(parts + [path_env])

def print_driver_info():
    chrome_major, chrome_full, chrome_path = get_chrome_version()
    driver_major, driver_full = get_installed_chromedriver_version()
    driver_path = get_driver_path()
    print(f"Chrome Path: {chrome_path or 'Not found'}")
    print(f"Chrome Version: {chrome_full or 'Unknown'}")
    print(f"Driver Path: {driver_path or 'Not found'}")
    print(f"Driver Version: {driver_full or 'Unknown'}")
    return True

if __name__ == "__main__":
    print_driver_info()
