#!/bin/bash
# Run server + dashboard side by side in tmux
# Usage: bash start.sh

SESSION="flipper-lab"

if ! command -v tmux &>/dev/null; then
  echo "tmux not found — install with: sudo apt install tmux"
  exit 1
fi

cd "$(dirname "$0")"

pip install -q -r requirements.txt

tmux new-session -d -s "$SESSION" -x 220 -y 50

# Left pane: vulnerable server
tmux send-keys -t "$SESSION:0.0" "python3 server/app.py" Enter

# Right pane: live dashboard
tmux split-window -h -t "$SESSION"
tmux send-keys -t "$SESSION:0.1" "sleep 1 && python3 monitor/dashboard.py" Enter

tmux select-pane -t "$SESSION:0.0"
tmux attach -t "$SESSION"
