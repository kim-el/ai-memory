#!/bin/bash
# Track ai-log disk usage over time
# Usage: disk-usage.sh           → show current
#        disk-usage.sh --snap    → save snapshot
#        disk-usage.sh --diff    → compare vs last snapshot

SNAPSHOT="$HOME/.ai-log/.disk_snap"

current() {
    echo "=== AI Memory Disk Usage ==="
    du -sh ~/.ai-log/*.db 2>/dev/null | while read size file; do
        name=$(basename "$file")
        count=""
        [ "$name" = "sessions.db" ] && count="($(sqlite3 "$file" "SELECT COUNT(*) FROM sessions" 2>/dev/null) sessions)"
        [ "$name" = "timeline.db" ] && count="($(sqlite3 "$file" "SELECT COUNT(*) FROM timeline" 2>/dev/null) entries)"
        echo "  $name  $size  $count"
    done
    echo ""
    echo "Total: $(du -sh ~/.ai-log | awk '{print $1}')"
    echo "Free:  $(df -h / | tail -1 | awk '{print $4}')"
    echo "Date:  $(date '+%Y-%m-%d %H:%M')"
}

snapshot() {
    du -s ~/.ai-log/*.db 2>/dev/null | awk '{print $2,$1}' > "$SNAPSHOT"
    echo "Snapshot saved: $(du -sh ~/.ai-log | awk '{print $1}') at $(date '+%H:%M')"
}

diff_snap() {
    if [ ! -f "$SNAPSHOT" ]; then
        echo "No snapshot. Run: disk-usage.sh --snap"
        return
    fi
    echo "=== Disk Growth ==="
    echo "Snapshot: $(cat "$SNAPSHOT" | awk '{sum+=$2} END {printf "%.1f MB", sum/1024}') at $(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$SNAPSHOT" 2>/dev/null)"
    echo "Now:      $(du -sh ~/.ai-log | awk '{print $1}')"
    echo ""
    for db in ~/.ai-log/*.db; do
        name=$(basename "$db")
        old_kb=$(grep "$db" "$SNAPSHOT" 2>/dev/null | awk '{print $2}')
        new_kb=$(du -sk "$db" | awk '{print $1}')
        [ -z "$old_kb" ] && old_kb=0
        diff=$((new_kb - old_kb))
        if [ $diff -gt 0 ]; then
            echo "  $name: +$(echo "scale=1; $diff/1024" | bc) MB"
        elif [ $diff -lt 0 ]; then
            echo "  $name: $(echo "scale=1; $diff/1024" | bc) MB"
        else
            echo "  $name: unchanged"
        fi
    done
}

case "${1:-current}" in
    --snap) snapshot ;;
    --diff) diff_snap ;;
    *) current ;;
esac
