#!/bin/bash
# Start the lab: server in Docker, dashboard in your current terminal.
# Usage:
#   bash start.sh          — build and start everything
#   bash start.sh wipe     — destroy container + state, then restart fresh

set -e
cd "$(dirname "$0")"

if [[ "$1" == "wipe" ]]; then
  echo "Wiping lab..."
  docker compose down -v --remove-orphans
  rm -f requests.log
  echo "Clean. Rebuilding..."
fi

# Build and start server container in the background
docker compose up -d --build

echo ""
echo "  Server running at http://$(hostname -I | awk '{print $1}'):5000"
echo "  Container logs:  docker compose logs -f"
echo "  Wipe and reset:  bash start.sh wipe"
echo ""

# Run dashboard in this terminal so you can watch attacks live
pip install -q rich
python3 monitor/dashboard.py
