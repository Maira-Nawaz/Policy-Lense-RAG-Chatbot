"""
Manual single-query smoke test for the RAG pipeline, ahead of the full
evaluation harness.

Usage:
    python3 test_query.py "What is our refund policy for enterprise customers in Germany?" \\
        --jurisdiction DE --segment enterprise
"""
import argparse
import json

from rag_pipeline import answer_query


def main():
    parser = argparse.ArgumentParser(description="Run a single query through the PolicyLens RAG pipeline.")
    parser.add_argument("query", help="The question to ask.")
    parser.add_argument("--jurisdiction", default=None, help="e.g. DE, US, UK")
    parser.add_argument("--segment", default=None, help="e.g. enterprise, smb, full_time, contractor")
    parser.add_argument("--department", default=None, help="e.g. Finance, HR, Legal")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print every reranked candidate's title + rerank_score, before truncation to top-k.",
    )
    args = parser.parse_args()

    result = answer_query(
        args.query,
        jurisdiction=args.jurisdiction,
        segment=args.segment,
        department=args.department,
        debug=args.debug,
    )

    print(f"Behavior: {result['behavior']}")
    print(f"Latency:  {result.get('latency_ms')} ms")
    print()
    print("Answer:")
    print(result.get("answer"))

    if result.get("cited_documents"):
        print()
        print(f"Cited documents: {', '.join(result['cited_documents'])}")
    if result.get("retrieved_chunk_ids"):
        print(f"Retrieved chunk ids: {result['retrieved_chunk_ids']}")
    if result.get("error_detail"):
        print()
        print(f"Error detail: {result['error_detail']}")

    if args.debug and result.get("debug_candidates"):
        print()
        print("--- Reranked candidates (all, before top-k truncation) ---")
        for candidate in result["debug_candidates"]:
            print(f"  {candidate['rerank_score']:.4f}  {candidate['title']}")

    print()
    print("--- Full result (JSON) ---")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
