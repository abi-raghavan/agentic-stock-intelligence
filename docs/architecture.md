# Architecture Notes

See root README for diagrams.

## Agent Responsibilities

1. Planner — intent parsing and task decomposition
2. Research — news, market, and fundamentals collection
3. RAG Evidence — hybrid retrieval with citation IDs
4. Risk Synthesis — opportunity/risk/confidence scoring
5. Report/Verify — executive report generation and claim verification

## Demo Reliability

The NVIDIA corpus in `sample_data/nvda_corpus.json` is loaded on API startup to ensure demo stability even when live APIs fail.
