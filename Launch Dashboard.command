#!/bin/zsh
# Open the existing app without refreshing or replacing its tender snapshot.
set -euo pipefail
cd "$(dirname "$0")"
URL="http://127.0.0.1:5001"
if ! curl --silent --fail --max-time 3 "$URL/" >/dev/null; then
    if lsof -nP -iTCP:5001 -sTCP:LISTEN -t >/dev/null; then
        echo "Port 5001 is occupied but the dashboard is not responding."
        exit 1
    fi
    mkdir -p logs
    nohup ./serve_app.sh >>logs/app_server.log 2>>logs/app_server_error.log </dev/null &
    ready=false
    for attempt in {1..20}; do
        if curl --silent --fail --max-time 2 "$URL/" >/dev/null; then
            ready=true
            break
        fi
        sleep 1
    done
    if [[ "$ready" != true ]]; then
        echo "Dashboard did not start. See logs/app_server_error.log."
        exit 1
    fi
fi
open "$URL/"
