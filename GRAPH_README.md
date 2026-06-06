# conv-graph

Conversation knowledge graph — maps everything you've discussed with AI agents into a queryable graph. No LLM needed.

## How it works

```
Transcripts → regex entity extraction → co-occurrence edges → graph.json → queries
```

- **Entities**: models, projects, tools, datasets, hardware, stacks — extracted via 20 regex patterns
- **Edges**: two entities mentioned in the same session = linked (weighted by co-occurrence count)
- **Queries**: `python3 query_graph.py parakeet` shows all connected entities grouped by type

## Usage

```bash
python3 build_graph.py          # Reads ~/.ai-log/sessions.db → graph.json
python3 query_graph.py parakeet # Everything connected to Parakeet
python3 query_graph.py --path whisper "aria bridge"  # How are they connected?
```

## Sample output

```
$ python3 query_graph.py parakeet

  parakeet tdt (model)
  94 mentions | first: 2025-12-24 | last: 2026-06-06

  [model] whisper (121), llm (69), qwen (21), fun-asr-nano (9)
  [project] whisperkit/mamak (215), ai-memory (46), aria bridge (27)
  [tool] vast.ai (125), github (86), whisper.cpp (32)
  [dataset] mesolitica (34), fleurs (34), common voice (55)
  [stack] cuda (184), onnx (84), coreml (46)
```

## Files

- `build_graph.py` — extracts entities from indexed transcripts, builds graph.json (~100 lines)
- `query_graph.py` — queries the graph: entity neighborhood + shortest path (~100 lines)
- `graph.json` — the graph data

## vs ai-memory

| | ai-memory | conv-graph |
|---|---|---|
| Search type | FTS5 keyword search | Graph neighborhood |
| Answers | "Which files contain X?" | "What's connected to X?" |
| Strength | Fast, simple | Structured, typed |
