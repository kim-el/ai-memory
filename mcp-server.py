#!/usr/bin/env python3.14
"""MCP server v6 — chain-aware search."""

import sys, json, sqlite3, re, os, subprocess, time
from datetime import datetime, timezone
from collections import defaultdict

SESSIONS_DB = os.path.expanduser("~/.ai-log/sessions.db")
TIMELINE_DB = os.path.expanduser("~/.ai-log/timeline.db")
STOP = set("the a an is was are be been of to in on at for with and or not it this that by from what how when where who why do does did can will would should could i you we they me him her us them my your our their".split())

def fmt_fts5(q):
    q_clean = re.sub(r'[-.,?!:;"()]', ' ', q)
    terms = [t for t in re.findall(r'\w+', q_clean.lower()) if t not in STOP]
    return " OR ".join(f'"{t}"' for t in terms) if terms else q_clean

def get_chains(q):
    """Return sessions grouped by context chain, ordered by time."""
    fts = fmt_fts5(q)
    try:
        db = sqlite3.connect(SESSIONS_DB)
        try:
            rows = db.execute("SELECT s.source,s.title,s.timestamp,s.content,s.summary FROM sessions_fts f JOIN sessions s ON s.id=f.rowid WHERE sessions_fts MATCH ? ORDER BY rank LIMIT 15", (fts,)).fetchall()
        except:
            rows = db.execute("SELECT source,title,timestamp,content,summary FROM sessions WHERE content LIKE ? ORDER BY timestamp DESC LIMIT 15", ('%'+q.replace(' ','%')+'%',)).fetchall()
        db.close()
    except: return ""
    if not rows: return ""
    
    # Extract chain tag from summary or assign based on content
    chains = defaultdict(list)
    terms = set(re.findall(r'\w+', q.lower()))
    
    seen_titles = set()
    for source, title, ts, content, summary in rows:
        if not content: continue
        # Deduplicate: skip if we already have this title
        title_key = title[:60].lower()
        if title_key in seen_titles: continue
        seen_titles.add(title_key)
        
        # Determine chain tag (3 methods: summary, content, title)
        tag = None
        if summary:
            m = re.match(r'([\w|+-]+)\s*::', summary)
            if m: tag = m.group(1).split('|')[0]
        if not tag:
            cl = (content or '').lower()
            rules = [
                (r'\btax\b|LHDN|EPF|SOCSO|PnL|audit|profit|expense\b|deduction', 'tax-finance'),
                (r'parakeet|nemo|fine.?tun|WER\b|ASR|onnx|int8|torch.*2\.6|cuda\b|vastai|GPU', 'parakeet-asr'),
                (r'\bpos\b|nasi.*campur|restaurant|menu|customer|cashier|bungkus', 'nasi-campur-pos'),
                (r'deepseek|claude.*code|opencode\b|mcp|api.*key|anthropic|ai.memory|memory.system', 'ai-tools'),
                (r'memory|fts5|index|sqlite|recall|search\b|timeline', 'memory-system'),
                (r'handy|tailscale|websocket|server\b|tls|cert|port.*8\d{3}', 'stt-server'),
            ]
            for pat, t in rules:
                if re.search(pat, cl): tag = t; break
        if not tag:
            tl = (title or '').lower()
            if 'tax' in tl or 'LHDN' in tl: tag = 'tax-finance'
            elif 'parakeet' in tl or 'nemo' in tl: tag = 'parakeet-asr'
            elif 'pos' in tl or 'restaurant' in tl: tag = 'nasi-campur-pos'
        if not tag: tag = 'other' 
        
        # Extract facts: data-rich lines OR keyword-matched conceptual lines
        lines = [l.strip() for l in content.split(chr(10)) if len(l.strip()) > 25]
        scored = []
        for l in lines:
            s = 0
            if re.search(r'RM\s*[\d,]', l): s += 10
            if re.search(r'[\d]+%', l): s += 5
            if re.search(r'[\d]{4,}', l): s += 3
            if l.endswith('?'): s -= 5
            kw_overlap = len(set(re.findall(r'\w+',l.lower())) & terms)
            if kw_overlap >= 2: s += kw_overlap  # conceptual match boost
            if s > 0: scored.append((s, l))
        scored.sort(reverse=True)
        # Show data-rich if available, otherwise keyword-matched
        data_rich = [(s,l) for s,l in scored if s >= 3]
        facts = [l for _,l in (data_rich[:2] if data_rich else scored[:2])]
        if not facts:
            non_q = [l for l in lines if not l.endswith('?')][:1]
            facts = non_q if non_q else [content.split(chr(10))[0][:200]]
        
        chains[tag].append({
            'ts': ts or '?',
            'title': title,
            'source': source,
            'facts': facts
        })
    
    # Format: each chain as a chronological timeline
    result = []
    for tag, sessions in chains.items():
        sessions.sort(key=lambda s: (s['ts'] == '?', s['ts']), reverse=False); sessions.reverse()
        result.append(f"## 🔗 {tag.replace('-',' ').title()}")
        for s in sessions:
            clean_title = s['title']
            if clean_title.startswith('gemini-session-'):
                clean_title = 'Gemini: ' + clean_title[15:35]
            elif clean_title.startswith('opencode-ses_'):
                clean_title = 'OpenCode: ' + clean_title[13:33]
            elif clean_title.endswith('.json') or clean_title.endswith('.md'):
                clean_title = clean_title.rsplit('.',1)[0][:60]
            result.append(f"- [{s['ts'][:10]}] **{clean_title[:70]}**")
            for f in s['facts']:
                result.append(f"  {f[:200]}")
        result.append("")
    
    return chr(10).join(result) if result else ""

def search_docs(q):
    try:
        r = subprocess.run(["mdfind", q], capture_output=True, text=True, timeout=2)
        files = [f.strip() for f in r.stdout.split(chr(10)) if f.strip() and not f.startswith("/System/") and "node_modules" not in f]
        now = time.time(); scored = []
        for f in files:
            try:
                mtime = os.path.getmtime(f)
                age_hours = (now - mtime) / 3600
                score = 10 if age_hours < 1 else (5 if age_hours < 24 else (2 if age_hours < 168 else 0))
                p = f.lower()
                if any(w in p for w in ['recipe', 'pipeline', 'finetune']): score += 5
                elif any(w in p for w in ['experiment', 'whisperkit']): score += 3
                scored.append((score, f))
            except: pass
        scored.sort(key=lambda x: x[0], reverse=True)
        return chr(10).join("- %s" % f for _, f in scored[:5]) if scored else ""
    except: return ""

def graph_context(q):
    """Find related entities from the conversation graph."""
    graph_path = os.path.expanduser("~/Projects/conv-graph/graph.json")
    if not os.path.exists(graph_path): return ""
    try:
        with open(graph_path) as f: g = json.load(f)
    except: return ""
    terms = set(re.findall(r'\w+', q.lower())) - STOP
    nodes = {n["id"]: n for n in g["nodes"]}
    matches = []
    for name, data in nodes.items():
        score = sum(1 for t in terms if t in name)
        if score > 0:
            # Find top connected entities
            top = []
            for e in g["edges"]:
                if e["source"] == name: top.append((e["target"], e["weight"]))
                elif e["target"] == name: top.append((e["source"], e["weight"]))
            top.sort(key=lambda x: x[1], reverse=True)
            top_str = ", ".join(f"{t} ({w})" for t, w in top[:4])
            matches.append((score, name, data["type"], data["weight"], top_str))
    if not matches: return ""
    matches.sort(key=lambda x: (x[0], x[3]), reverse=True)
    lines = ["## 🔗 Graph"]
    for score, name, etype, weight, top_str in matches[:3]:
        lines.append(f"- **{name}** ({etype}, {weight}×): {top_str}")
    return "\n".join(lines) + "\n"

def search(q):
    qq = q.lower().strip()
    q_words = set(re.findall(r'\w+', qq))
    
    # Spotlight: strip question words for better file matching
    doc_q = ' '.join(w for w in re.findall(r'\w+', qq) if w not in STOP)[:5]
    
    # FAQ cache
    try:
        db = sqlite3.connect(TIMELINE_DB)
        db.execute("CREATE TABLE IF NOT EXISTS cache (query TEXT, result TEXT, created REAL)")
        rows = db.execute("SELECT query, result FROM cache WHERE created > ?", (time.time() - 1800,)).fetchall()
        db.close()
        for cq, result in rows:
            c_words = set(re.findall(r'\w+', cq))
            if len(q_words & c_words) / max(len(q_words), 1) > 0.6:
                return result + "\n\n> *(cached)*"
    except: pass
    
    chains = get_chains(qq)
    docs = search_docs(doc_q)
    graph_ctx = graph_context(qq)
    parts = []
    if chains: parts.append(chains)
    if docs: parts.append("## 📂 Documents\n" + docs)
    if graph_ctx: parts.append(graph_ctx)
    result = "\n".join(parts)[:2500] if parts else "Nothing found."
    
    if result != "Nothing found.":
        try:
            db = sqlite3.connect(TIMELINE_DB)
            db.execute("INSERT OR REPLACE INTO cache VALUES (?, ?, ?)", (qq, result, time.time()))
            db.commit(); db.close()
        except: pass
    return result

# MCP protocol
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try: req = json.loads(line)
    except: continue
    m, rid = req.get("method",""), req.get("id")
    if m == "initialize":
        r = {"jsonrpc":"2.0","id":rid,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"ai-memory","version":"6.0.0"}}}
    elif m == "tools/list":
        r = {"jsonrpc":"2.0","id":rid,"result":{"tools":[{"name":"ai_memory_search","description":"Search past conversations as chronological chains grouped by topic. Returns story arcs, not keyword soup.","inputSchema":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}]}}
    elif m == "tools/call":
        q = req.get("params",{}).get("arguments",{}).get("query","")
        r = {"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text": search(q)}]}}
    elif m == "notifications/initialized": continue
    else: r = {"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":f"Unknown: {m}"}}
    sys.stdout.write(json.dumps(r)+"\n")
    sys.stdout.flush()
