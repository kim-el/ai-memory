# AI Memory — Cross-Tool Agent Memory with Spotlight

A local-first memory system for AI coding agents. Auto-indexes conversations across Claude Code, OpenCode, Codex, and Gemini. Adds Spotlight document search, FAQ caching, and chain-aware (chronological) retrieval. Runs as an MCP server — any compatible agent discovers it natively.

## Features

- **Cross-tool**: One index for Claude, OpenCode, Codex, Gemini conversations
- **Spotlight integration**: Also searches documents, spreadsheets, and files on your Mac
- **Chain-aware search**: Returns results grouped by topic, ordered chronologically — not keyword soup
- **FAQ cache**: Similar questions return cached results in <1ms
- **Zero config**: Register as an MCP server once, works everywhere
- **No cloud**: All data stays local. SQLite FTS5 + macOS Spotlight
- **Append-only timeline**: Shell commands, session starts captured automatically

## Quick Start

```bash
# 1. Clone
git clone https://github.com/kim-el/ai-memory.git ~/.ai-log

# 2. Build index (one-time)
python3 ~/.ai-log/build-index.py

# 3. Register in Claude Code
# Add to ~/.claude.json projects.YOUR_PROJECT.mcpServers:
# {"ai-memory": {"type": "stdio", "command": "python3", "args": ["~/.ai-log/mcp-server.py"]}}

# 4. Add shell hooks (optional — captures terminal commands)
echo 'source ~/.ai-log/shell-init.sh' >> ~/.zshrc

# 5. Restart Claude Code. Agent auto-discovers ai_memory_search.
```

## How It Works

```
Agent asks question
    ↓
ai_memory_search(query) via MCP
    ↓
┌─────────────────────────────────┐
│ FAQ Cache (<1ms)                │
│ 60% word overlap → instant      │
├─────────────────────────────────┤
│ FTS5 Search (3ms)               │
│ Conversations grouped by topic  │
│ Ordered newest-first            │
├─────────────────────────────────┤
│ Spotlight/mdfind (100ms)        │
│ Every file on your Mac          │
├─────────────────────────────────┤
│ Merged + scored (20ms)          │
└─────────────────────────────────┘
    ↓
Agent gets context in <150ms
```

## Architecture

```
~/.ai-log/
├── mcp-server.py     MCP server — the brain
├── ai-memory         CLI tool for direct queries
├── capture.sh        Append events to timeline
├── smart-index.sh    Re-index when stale
├── shell-init.sh     Shell integration (silent)
├── disk-usage.sh     Track storage growth
├── archive.sh        Archive old data to external storage
├── sessions.db       FTS5 search index (auto-created)
└── timeline.db       Append-only event log (auto-created)
```

## Requirements

- Python 3.10+
- macOS (for Spotlight/mdfind — Linux fallback uses `find`)
- SQLite3 (built-in)

## Customization

Edit `mcp-server.py` to add your own context tags (domain rules for grouping conversations):

```python
# In get_chains(), add:
rules = [
    (r'frontend|react|css|component', 'frontend'),
    (r'api|endpoint|database|query', 'backend'),
    (r'deploy|docker|kubernetes|ci', 'devops'),
]
```

## Comparison

| Feature | AI Memory | Mem0 | Zep | Khoj |
|---------|-----------|------|-----|------|
| Auto-indexes AI chats | ✅ | ❌ | ❌ | ❌ |
| Document search | ✅ Spotlight | ❌ | ❌ | ✅ |
| FAQ cache | ✅ | ❌ | ❌ | ❌ |
| Chain-aware (topic+time) | ✅ | ❌ | ⚠️ | ❌ |
| No server | ✅ MCP stdio | ❌ | ❌ | ❌ |
| Cross-tool | ✅ | ⚠️ SDK | ⚠️ SDK | ❌ |
| Cost | Free | $249/mo | $99/mo | Free |

## License

MIT
