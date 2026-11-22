# Architecture Notes

```
START → planning → research → retrieval → risk → report/verify → END
                      ↑            ↑
                 planner.focus   planner intent + focus_queries
```

## Agent Responsibilities

1. **Planner** — LLM (Groq free / Ollama) produces intent, tasks, and focus queries that drive later nodes; heuristic plan if no LLM key
2. **Research** — news, market, and fundamentals collection, biased by planner focus queries
3. **RAG Evidence** — hybrid BM25 + in-process TF-IDF (RRF fusion) with citation IDs `E1…`; optional Qdrant dense path
4. **Risk Synthesis** — deterministic scores + optional LLM-refined risk/opportunity narratives
5. **Report/Verify** — LLM executive report with cited claims; two-stage groundedness (citation ID check + LLM support check); one RAG retry if verification fails

## LLM (free, lightweight, fast)

- Primary: **Groq** `qwen/qwen3.8-27b` via `GROQ_API_KEY` (free tier)
- Fallback: local **Ollama** when `ENABLE_OLLAMA=true`
- Without either: full pipeline still runs on heuristics/templates

## Demo Reliability

Sample corpora in `sample_data/` load on API startup so demos stay stable when live Yahoo/News APIs throttle.
