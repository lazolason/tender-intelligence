#!/bin/bash

# ==========================================================
# TENDER INTELLIGENCE DASHBOARD LAUNCHER
# Standardizes the sequence to refresh and serve the dashboard.
# ==========================================================

# 1. Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "----------------------------------------------------"
echo "🚀 Starting Tender Intelligence Dashboard..."
echo "----------------------------------------------------"

# 2. Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️  Warning: Virtual environment (.venv) not found. Trying system python..."
fi

# 3. Refresh dashboard data
echo "📡 Refreshing dashboard data..."
python3 sync_dashboard.py

# 4. Check if app server is already running
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
    echo "ℹ️  Tender Intelligence app is already running on port 5001."
else
    echo "🌐 Starting Tender Intelligence app on port 5001..."
    ./serve_app.sh &
    # Allow a moment for server to start
    sleep 2
fi

# 5. Open browser
echo "✨ Opening dashboard in your default browser..."
open "http://localhost:5001"

echo "----------------------------------------------------"
echo "✅ Dashboard is live!"
echo "You can close this window. The server will run in the background."
echo "----------------------------------------------------"

# Stay open briefly so the user can see if any errors occurred
sleep 3
exit
