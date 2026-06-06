#!/usr/bin/env python3
"""Build SQLite FTS5 index from AI session files. Customize SOURCES for your tools."""

import sqlite3, json, os, re, time
from pathlib import Path
from datetime import datetime

DB = os.path.expanduser("~/.ai-log/sessions.db")

# Customize: add paths to YOUR AI tool session files
SOURCES = {
    "claude": os.path.expanduser("~/.claude/projects"),
    "opencode": os.path.expanduser("~/.local/share/opencode"),
    "gemini": os.path.expanduser("~/.gemini"),
    # Add more sources here
}

def init_db():
    if os.path.exists(DB): os.remove(DB)
    db = sqlite3.connect(DB)
    db.execute("CREATE TABLE sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, path TEXT UNIQUE, title TEXT, timestamp TEXT, content TEXT, summary TEXT)")
    db.execute("CREATE VIRTUAL TABLE sessions_fts USING fts5(title, content, summary, content='sessions', content_rowid='id')")
    db.execute("CREATE TRIGGER sessions_ai AFTER INSERT ON sessions BEGIN INSERT INTO sessions_fts(rowid, title, content, summary) VALUES (new.id, new.title, new.content, new.summary); END")
    db.execute("CREATE TRIGGER sessions_ad AFTER DELETE ON sessions BEGIN INSERT INTO sessions_fts(sessions_fts, rowid, title, content, summary) VALUES('delete', old.id, old.title, old.content, old.summary); END")
    db.commit()
    return db

def main():
    print("Building AI memory index...")
    db = init_db()
    total = 0
    
    for source_name, source_path in SOURCES.items():
        base = Path(source_path)
        if not base.exists(): continue
        
        files = list(set(list(base.glob("**/*.json")) + list(base.glob("**/*.jsonl")) + list(base.glob("**/*.md")) + list(base.glob("**/*.txt"))))
        count = 0
        for fp in files:
            if fp.stat().st_size > 10_000_000: continue
            try:
                if fp.suffix == '.jsonl':
                    with open(fp) as f: content = '\n'.join(json.loads(line).get('text','') for line in f if len(line) > 100)
                elif fp.suffix == '.json':
                    with open(fp) as f: content = json.dumps(json.load(f))
                else:
                    with open(fp, encoding='utf-8', errors='ignore') as f: content = f.read()
                if len(content) < 100: continue
                ts = datetime.fromtimestamp(os.path.getmtime(fp)).strftime('%Y-%m-%d')
                db.execute("INSERT INTO sessions (source,path,title,timestamp,content,summary) VALUES (?,?,?,?,?,?)",
                           (source_name, str(fp), fp.stem[:200], ts, content, content[:400]))
                count += 1
                if count % 200 == 0: db.commit()
            except: pass
        db.commit()
        total += count
        print(f"  [{source_name}] {count} files")
    
    print(f"\nDone: {total} files indexed, {db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]} sessions, {os.path.getsize(DB)/1024/1024:.1f}MB")

if __name__ == "__main__":
    main()
