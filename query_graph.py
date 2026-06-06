#!/usr/bin/env python3
"""Query the conversation knowledge graph."""

import json, sys
from collections import defaultdict

with open(__file__.rsplit("/", 1)[0] + "/graph.json") as f:
    g = json.load(f)

nodes = {n["id"]: n for n in g["nodes"]}
edges = g["edges"]

def query(entity):
    """Find everything connected to an entity."""
    entity = entity.lower()
    matches = [nodes[n] for n in nodes if entity in n]
    if not matches:
        print(f"Nothing found for '{entity}'")
        return

    for match in matches[:3]:  # Show top 3 matches
        name = match["id"]
        print(f"\n{'='*60}")
        print(f"  {name} ({match['type']})")
        print(f"  {match['weight']} mentions | first: {match.get('first_seen','?')} | last: {match.get('last_seen','?')}")
        print(f"{'='*60}")

        # Connected entities sorted by edge weight
        connected = []
        for e in edges:
            if e["source"] == name:
                connected.append((e["target"], e["weight"], e.get("sessions", [])))
            elif e["target"] == name:
                connected.append((e["source"], e["weight"], e.get("sessions", [])))

        connected.sort(key=lambda x: x[1], reverse=True)

        # Group by type
        by_type = defaultdict(list)
        for target, weight, sessions in connected:
            t = nodes.get(target, {}).get("type", "unknown")
            by_type[t].append((target, weight))

        for t in ["model", "project", "tool", "dataset", "stack", "hardware", "platform"]:
            if t in by_type:
                items = by_type[t][:5]
                lines = ", ".join(f"{name} ({w})" for name, w in items)
                print(f"  [{t}] {lines}")

        if connected:
            top = connected[0]
            print(f"\n  Strongest link: {top[0]} (weight: {top[1]})")

def path(a, b):
    """Find shortest connection path between two entities."""
    a, b = a.lower(), b.lower()
    a_matches = [nodes[n] for n in nodes if a in n]
    b_matches = [nodes[n] for n in nodes if b in n]
    if not a_matches or not b_matches:
        print("One or both not found")
        return

    a_name = a_matches[0]["id"]
    b_name = b_matches[0]["id"]

    # Build adjacency
    adj = defaultdict(set)
    for e in edges:
        adj[e["source"]].add(e["target"])
        adj[e["target"]].add(e["source"])

    # BFS
    visited = {a_name}
    queue = [(a_name, [a_name])]
    while queue:
        node, path_nodes = queue.pop(0)
        if node == b_name:
            print(f"Path ({len(path_nodes)-1} hops): {' → '.join(path_nodes)}")
            return
        for neighbor in adj[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path_nodes + [neighbor]))

    print(f"No path found between '{a_name}' and '{b_name}'")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 query_graph.py <entity>")
        print("       python3 query_graph.py --path <a> <b>")
        sys.exit(1)

    if sys.argv[1] == "--path" and len(sys.argv) >= 4:
        path(sys.argv[2], sys.argv[3])
    else:
        query(sys.argv[1])
