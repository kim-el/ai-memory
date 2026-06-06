#!/bin/bash
LAST_INDEX="$HOME/.ai-log/.last_index"
INTERVAL=3600
if [ -f "$LAST_INDEX" ]; then
    now=$(date +%s)
    last=$(cat "$LAST_INDEX")
    if [ $((now - last)) -ge $INTERVAL ]; then
        python3.14 "$HOME/.ai-log/.build_index.py" >/dev/null 2>&1
        date +%s > "$LAST_INDEX"
    fi
else
    date +%s > "$LAST_INDEX"
fi
