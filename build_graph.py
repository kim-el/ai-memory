#!/usr/bin/env python3
"""Build a knowledge graph from conversation transcripts.
No LLM needed — entities via regex, edges via session co-occurrence.
Output: graph.json"""

import json, re, os, sqlite3, hashlib
from collections import defaultdict
from pathlib import Path

DB = os.path.expanduser("~/.ai-log/sessions.db")
OUT = Path(__file__).parent / "graph.json"

# ── Entity extractors ──────────────────────────────────────────

PATTERNS = [
    # Models
    (r'\b(parakeet[- ]tdt[- ]?(0\.?6b|1\.?1b|v\d)?)\b', 'model', 'Parakeet TDT'),
    (r'\b(whisper[- ](small|tiny|base|medium|large|mamak)?)\b', 'model', 'Whisper'),
    (r'\b(fun[- ]asr[- ]?(mlt[- ])?nano)\b', 'model', 'Fun-ASR-Nano'),
    (r'\b(deepseek[- ]v\d[\w.-]*|claude[- ]\d[\w.-]*)\b', 'model', 'LLM'),
    (r'\b(qwen\d[\w.-]*)\b', 'model', 'Qwen'),
    # Projects
    (r'\b(aria[- ](telegram[- ])?bridge|aria[- ]flash|aria[- ]pro|aria[- ]claude)\b', 'project', 'ARIA Bridge'),
    (r'\b(ai[- ]memory|ai_memory)\b', 'project', 'ai-memory'),
    (r'\b(graphify)\b', 'project', 'Graphify'),
    (r'\b(whisperkit|mamak.*ai|nemo.*finetune)\b', 'project', 'Whisperkit/Mamak'),
    # Tools
    (r'\b(tmux|tailscale|whisper\.cpp|llama\.cpp|llama[- ]cpp)\b', 'tool', None),
    (r'\b(vast\.?ai|vastai)\b', 'tool', 'vast.ai'),
    (r'\b(digitalocean|doctl)\b', 'tool', 'DigitalOcean'),
    (r'\b(telegram|bot father)\b', 'tool', 'Telegram'),
    (r'\b(github|jsonl|fts5|sqlite)\b', 'tool', None),
    # Data
    (r'\b(mesolitica|malaya[- ]speech|fleurs|common[- ]voice)\b', 'dataset', None),
    # Infrastructure
    (r'\b(rtx[- ]?3060|gpu|a100|mac[ -]?mini|m\d|apple silicon)\b', 'hardware', None),
    (r'\b(cuda[- ]?\d[\d.]*|nvjitlink)\b', 'stack', 'CUDA'),
    (r'\b(onnx|coreml|gguf|ggml|metal)\b', 'stack', None),
    (r'\b(huggingface|modelscope)\b', 'platform', None),
]

def extract_entities(text):
    """Extract entities from text. Returns list of (name, type, label)."""
    text_lower = text.lower()
    entities = []
    seen = set()
    for pattern, etype, label in PATTERNS:
        for match in re.finditer(pattern, text_lower):
            name = match.group(0).strip()
            if name in seen: continue
            seen.add(name)
            label = label or name.title()
            entities.append({"name": label.lower(), "type": etype})
    return entities

# ── Graph builder ──────────────────────────────────────────────

def build():
    db = sqlite3.connect(DB)
    rows = db.execute(
        "SELECT source, path, title, timestamp, content FROM sessions ORDER BY timestamp"
    ).fetchall()
    db.close()

    nodes = {}       # name → {type, weight, first_seen, last_seen}
    edges = defaultdict(lambda: {"weight": 0, "sessions": []})  # (a,b) → stats

    for source, path, title, ts, content in rows:
        if not content: continue
        entities = extract_entities(content)
        if len(entities) < 2: continue

        # Add nodes
        for e in entities:
            name = e["name"]
            if name not in nodes:
                nodes[name] = {"type": e["type"], "weight": 0, "first_seen": ts, "last_seen": ts}
            nodes[name]["weight"] += 1
            if ts and ts > nodes[name].get("last_seen", ""):
                nodes[name]["last_seen"] = ts

        # Add edges (all pairs in same session)
        for i in range(len(entities)):
            for j in range(i+1, len(entities)):
                a, b = sorted([entities[i]["name"], entities[j]["name"]])
                if a == b: continue
                key = f"{a}|{b}"
                edges[key]["weight"] += 1
                edges[key]["sessions"].append(ts[:10] if ts else "?")

    # ── Output ──────────────────────────────────────────────────
    graph = {
        "nodes": [
            {
                "id": name,
                "type": nodes[name]["type"],
                "weight": nodes[name]["weight"],
                "first_seen": nodes[name].get("first_seen","?")[:10],
                "last_seen": nodes[name].get("last_seen","?")[:10],
            }
            for name in sorted(nodes)
        ],
        "edges": [
            {
                "source": key.split("|")[0],
                "target": key.split("|")[1],
                "weight": edges[key]["weight"],
                "sessions": list(set(edges[key]["sessions"])),
            }
            for key in sorted(edges, key=lambda k: edges[k]["weight"], reverse=True)
        ],
        "meta": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "built": __import__('datetime').datetime.now().isoformat()
        }
    }

    with open(OUT, "w") as f:
        json.dump(graph, f, indent=2)

    # Quick stats
    top_nodes = sorted(nodes.items(), key=lambda x: x[1]["weight"], reverse=True)[:10]
    top_edges = sorted(edges.items(), key=lambda x: x[1]["weight"], reverse=True)[:10]

    print(f"Nodes: {len(nodes)}, Edges: {len(edges)}")
    print(f"\nTop nodes:")
    for name, data in top_nodes:
        print(f"  {name} ({data['type']}): {data['weight']} mentions")
    print(f"\nTop edges:")
    for key, data in top_edges:
        a, b = key.split("|")
        print(f"  {a} — {b}: {data['weight']} co-occurrences")
    print(f"\nWrote: {OUT}")

if __name__ == "__main__":
    build()
