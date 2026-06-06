#!/bin/bash
# Append timestamped entry to the AI timeline log.
# Usage: capture "source" "location" "type" "content"
# Called by shell hooks, Claude onStop, etc.

LOG_DB="$HOME/.ai-log/timeline.db"

SOURCE="$1"
LOCATION="$2"
TYPE="$3"
CONTENT="$4"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ -z "$CONTENT" ] || [ -z "$SOURCE" ]; then
    exit 0
fi

# Escape single quotes for SQLite
CONTENT_ESC=$(echo "$CONTENT" | sed "s/'/''/g")

sqlite3 "$LOG_DB" "
CREATE TABLE IF NOT EXISTS timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    location TEXT DEFAULT '',
    entry_type TEXT DEFAULT 'event',
    content TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS timeline_fts USING fts5(
    source, location, entry_type, content,
    content='timeline', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS timeline_ai AFTER INSERT ON timeline BEGIN
    INSERT INTO timeline_fts(rowid, source, location, entry_type, content)
    VALUES (new.id, new.source, new.location, new.entry_type, new.content);
END;
INSERT INTO timeline (timestamp, source, location, entry_type, content)
VALUES ('$TIMESTAMP', '$SOURCE', '$LOCATION', '$TYPE', '$CONTENT_ESC');
" 2>/dev/null

echo "[captured] $TIMESTAMP | $SOURCE | $TYPE"
