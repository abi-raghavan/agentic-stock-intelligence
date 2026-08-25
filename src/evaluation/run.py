
import argparse
import json
from pathlib import Path

from src.rag.retriever import HybridRetriever, reciprocal_rank_fusion


def evaluate_retrieval(data_dir: str) -> dict:
    retriever = HybridRetriever()
    count = retriever.load_sample_data(data_dir)
    query = "Should I be worried about NVIDIA export restrictions over the next 30 days?"
    rewritten, evidence = retriever.retrieve(query=query, ticker="NVDA", limit=5)
    hit = any("export" in item["snippet"].lower() for item in evidence)
    return {
        "documents_indexed": count,
        "rewritten_query": rewritten,
        "recall_at_5_export_topic": hit,
        "top_evidence": evidence,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline evaluation for retrieval quality")
    parser.add_argument("--data-dir", default="sample_data")
    args = parser.parse_args()
    results = evaluate_retrieval(args.data_dir)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
