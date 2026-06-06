#!/usr/bin/env python3
"""MCP server for conversation knowledge graph — 50 lines."""

import json, sys, os
from collections import defaultdict

GRAPH = os.path.join(os.path.dirname(__file__), "graph.json")

def load():
    with open(GRAPH) as f: return json.load(f)

def query(entity):
    g = load()
    nodes = {n["id"]: n for n in g["nodes"]}
    matches = [nodes[n] for n in nodes if entity.lower() in n]
    if not matches: return f"Nothing found for '{entity}'"

    out = []
    for match in matches[:2]:
        name = match["id"]
        out.append(f"## {name} ({match['type']})")
        out.append(f"{match['weight']} mentions | {match.get('first_seen','?')[:10]} → {match.get('last_seen','?')[:10]}")
        connected = []
        for e in g["edges"]:
            if e["source"] == name: connected.append((e["target"], e["weight"]))
            elif e["target"] == name: connected.append((e["source"], e["weight"]))
        connected.sort(key=lambda x: x[1], reverse=True)
        by_type = defaultdict(list)
        for target, w in connected:
            t = nodes.get(target, {}).get("type", "unknown")
            by_type[t].append((target, w))
        for t in ["model","project","tool","dataset","stack","hardware","platform"]:
            if t in by_type:
                items = ", ".join(f"{n} ({w})" for n, w in by_type[t][:5])
                out.append(f"[{t}] {items}")
        if connected:
            out.append(f"strongest: {connected[0][0]} ({connected[0][1]})")
        out.append("")
    return "\n".join(out)

def path(a, b):
    g = load()
    nodes = {n["id"]: n for n in g["nodes"]}
    am = [nodes[n] for n in nodes if a.lower() in n]
    bm = [nodes[n] for n in nodes if b.lower() in n]
    if not am or not bm:
        return "One or both not found"
    a_name, b_name = am[0]["id"], bm[0]["id"]
    adj = defaultdict(set)
    for e in g["edges"]:
        adj[e["source"]].add(e["target"])
        adj[e["target"]].add(e["source"])
    visited = {a_name}
    queue = [(a_name, [a_name])]
    while queue:
        node, p = queue.pop(0)
        if node == b_name:
            return f"Path ({len(p)-1} hops): {' → '.join(p)}"
        for neighbor in adj[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, p + [neighbor]))
    return "No path found"

# MCP protocol
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try: req = json.loads(line)
    except: continue
    m, rid = req.get("method",""), req.get("id")
    if m == "initialize":
        r = {"jsonrpc":"2.0","id":rid,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"conv-graph","version":"1.0.0"}}}
    elif m == "tools/list":
        r = {"jsonrpc":"2.0","id":rid,"result":{"tools":[
            {"name":"graph_query","description":"Query the conversation knowledge graph: what's connected to an entity?","inputSchema":{"type":"object","properties":{"entity":{"type":"string"}},"required":["entity"]}},
            {"name":"graph_path","description":"Find shortest connection path between two entities in the conversation graph","inputSchema":{"type":"object","properties":{"a":{"type":"string"},"b":{"type":"string"}},"required":["a","b"]}}
        ]}}
    elif m == "tools/call":
        p = req.get("params",{}).get("arguments",{})
        tool = req.get("params",{}).get("name","")
        if tool == "graph_query":
            text = query(p.get("entity",""))
        elif tool == "graph_path":
            text = path(p.get("a",""), p.get("b",""))
        else:
            text = f"Unknown tool: {tool}"
        r = {"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text": text}]}}
    elif m == "notifications/initialized": continue
    else: r = {"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":f"Unknown: {m}"}}
    sys.stdout.write(json.dumps(r)+"\n")
    sys.stdout.flush()
