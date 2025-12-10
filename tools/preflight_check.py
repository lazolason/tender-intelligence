#!/usr/bin/env python3
# ==========================================================
# CHROMEDRIVER PRE-FLIGHT CHECK
# Run this before starting scrapers
# ==========================================================

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.chromedriver_manager import (
    verify_driver_alignment, print_driver_info, get_driver_path
)


def preflight_check():
    """
    Run pre-flight checks before scraping
    Returns: (passed: bool, warnings: list)
    """
    warnings = []
    
    # Check driver alignment
    aligned, chrome_major, driver_major, msg = verify_driver_alignment()
    
    if not aligned:
        if chrome_major and driver_major is None:
            warnings.append(
                f"⚠️  Chromedriver not installed.\n"
                f"   Chrome {chrome_major} detected but no driver found.\n"
                f"   Fix: python tools/setup_chromedriver.py"
            )
            return False, warnings
        elif chrome_major and driver_major and chrome_major != driver_major:
            warnings.append(
                f"⚠️  Version mismatch: Chrome {chrome_major} vs Driver {driver_major}\n"
                f"   This will likely cause Selenium flakiness.\n"
                f"   Fix: python tools/setup_chromedriver.py"
            )
    
    # Check driver is accessible
    driver_path = get_driver_path()
    if not driver_path:
        warnings.append("❌ Chromedriver binary not accessible")
        return False, warnings
    
    if aligned:
        return True, []  # All good, no warnings
    else:
        # Misaligned but driver exists - warn but allow to proceed
        return True, warnings


def main():
    print("\n" + "=" * 60)
    print("🚀 CHROMEDRIVER PRE-FLIGHT CHECK")
    print("=" * 60)
    
    passed, warnings = preflight_check()
    
    if warnings:
        for warning in warnings:
            print(f"\n{warning}")
    
    if passed:
        print("\n✅ Checks passed. Ready to scrape!")
        print_driver_info()
        return 0
    else:
        print("\n❌ Critical checks failed. Cannot proceed.")
        print("   Run: python tools/setup_chromedriver.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
