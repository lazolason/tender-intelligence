# ==========================================================
# LOGGING TOOLSET
# Writes clean logs to scraper.log and console
# Handles log rotation and timestamp formatting
# ==========================================================

import os
from datetime import datetime

# ----------------------------------------------------------
# WRITE A SINGLE LOG ENTRY
# ----------------------------------------------------------
def write_log(log_file_path: str, message: str, level: str = "INFO"):
    """
    Writes one log line with timestamp.
    Example:
    [2025-11-27 10:32:15] [INFO] Starting scrape for National Treasury
    """

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level.upper()}] {message}\n"

    # Ensure directory exists
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    # Append to log
    with open(log_file_path, "a") as f:
        f.write(line)

    # Mirror to terminal console
    print(line.strip())

# ----------------------------------------------------------
# ROTATE LOG IF TOO BIG (auto-clean)
# ----------------------------------------------------------
def rotate_log_if_needed(log_file_path: str, max_entries: int = 5000):
    """
    Prevents log from growing uncontrollably.
    If > max_entries lines → keep only last 1000.
    """

    if not os.path.exists(log_file_path):
        return

    try:
        with open(log_file_path, "r") as f:
            lines = f.readlines()

        if len(lines) > max_entries:
            # Keep last 1000 lines
            trimmed = lines[-1000:]
            with open(log_file_path, "w") as f:
                f.writelines(trimmed)

            print(f"[LOG] Rotated log file. Trimmed to last 1000 entries.")

    except Exception as e:
        print(f"[LOG ERROR] Could not rotate log: {e}")

# ----------------------------------------------------------
# HIGH-LEVEL EVENTS
# ----------------------------------------------------------
def log_start(log_file_path: str, target: str):
    write_log(log_file_path, f"Starting scrape for: {target}", "INFO")

def log_end(log_file_path: str, total_found: int, total_added: int):
    write_log(log_file_path, f"Scrape complete. Found: {total_found}, Added: {total_added}", "INFO")

def log_error(log_file_path: str, message: str):
    write_log(log_file_path, f"ERROR → {message}", "ERROR")
