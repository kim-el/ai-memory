#!/bin/bash
# Archive old AI sessions to external storage
# Usage: archive.sh /Volumes/SSD/ai-archive [months]

ARCHIVE_TO="${1:-/Volumes/SSD/ai-archive}"
MONTHS="${2:-3}"  # keep last 3 months on Mac, move older

SOURCES=(
    "$HOME/.claude/projects"
    "$HOME/.local/share/opencode"
    "$HOME/.gemini"
    "$HOME/Projects/data-collection/raw"
    "$HOME/Projects/data-collection/temporary/sessions"
)

CUTOFF=$(date -v-${MONTHS}m +%s 2>/dev/null || date -d "${MONTHS} months ago" +%s)

echo "Archiving files older than ${MONTHS} months to ${ARCHIVE_TO}..."
echo "Cutoff: $(date -r $CUTOFF '+%Y-%m-%d' 2>/dev/null || date -d @$CUTOFF '+%Y-%m-%d')"
echo ""

total=0
for src in "${SOURCES[@]}"; do
    [ -d "$src" ] || continue
    count=$(find "$src" -type f -not -name '.DS_Store' -mtime +$((MONTHS*30)) 2>/dev/null | wc -l)
    [ "$count" -eq 0 ] && continue
    
    dest="$ARCHIVE_TO/$(echo "$src" | sed "s|$HOME/||; s|/|_|g")"
    mkdir -p "$dest"
    
    echo "[$src] Found $count old files → $dest"
    find "$src" -type f -not -name '.DS_Store' -mtime +$((MONTHS*30)) -print0 2>/dev/null | \
        xargs -0 -I{} sh -c '
            rel=$(echo "{}" | sed "s|'$src'/||")
            mkdir -p "'$dest'/$(dirname "$rel")"
            mv "{}" "'$dest'/$rel" 2>/dev/null
        '
    total=$((total + count))
done

echo ""
echo "Archived $total files. Rebuild index after archiving:"
echo "  python3.14 ~/.ai-log/.build_index.py"
echo ""
echo "Archive paths added to index scan automatically."
echo "To restore: mv $ARCHIVE_TO/* ~/"
