"""Comparable dev benchmark: TF-IDF, dense pgvector, and hybrid RRF."""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from agentic import RealRetriever  # noqa: E402
from baseline import TfidfIndex, hit, pack_context  # noqa: E402


def rrf(dense: list[dict[str, Any]], lexical: list[dict[str, Any]], k: int = 60) -> list[dict[str, Any]]:
    """Fuse ranked lists using standard reciprocal rank fusion."""
    by_id: dict[str, dict[str, Any]] = {}
    scores: dict[str, float] = {}
    ranks: dict[str, dict[str, int]] = {}
    for source, rows in (("dense", dense), ("lexical", lexical)):
        for rank, row in enumerate(rows, start=1):
            cid = row["id"]
            by_id.setdefault(cid, row)
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            ranks.setdefault(cid, {})[source] = rank
    return [
        {**by_id[cid], "score": scores[cid], "rrf_score": scores[cid],
         "dense_score": dense[ranks[cid]["dense"] - 1]["score"] if "dense" in ranks[cid] else None,
         "lexical_score": lexical[ranks[cid]["lexical"] - 1]["score"] if "lexical" in ranks[cid] else None,
         "dense_rank": ranks[cid].get("dense"), "lexical_rank": ranks[cid].get("lexical"),
         "strategy": "hybrid_rrf"}
        for cid in sorted(scores, key=lambda cid: (-scores[cid], cid))
    ]


def apply_filters(rows: list[dict[str, Any]], filters: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not filters:
        return rows
    allowed = {"section", "year", "document_id", "source"}
    unsupported = set(filters) - allowed
    if unsupported:
        raise ValueError(f"unsupported filter(s): {sorted(unsupported)}")

    def matches(row: dict[str, Any]) -> bool:
        for key, value in filters.items():
            actual = row.get(key)
            if actual is None and key == "document_id":
                actual = row.get("source_id")
            if actual is None:
                actual = row.get("metadata", {}).get(key)
            if actual != value:
                return False
        return True

    return [row for row in rows if matches(row)]


def evaluate_method(method: str, questions: list[dict[str, Any]], lexical: TfidfIndex,
                    dense_retriever: RealRetriever, *, top_k: int, candidate_k: int,
                    context_budget: int, index_seconds: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    traces = []
    # TF-IDF index is prepared once by the caller; elapsed here measures only question retrieval.
    api_calls = 0
    for question in questions:
        start = time.perf_counter()
        candidate_lists = None
        if method == "tfidf":
            results = apply_filters(
                lexical.search(question["question"], top_k=len(lexical.chunks)),
                question.get("filter"),
            )[:top_k]
        elif method == "dense":
            results = dense_retriever.search(
                question["question"], filters=question.get("filter"), top_k=top_k
            )
            api_calls += 1
        elif method == "hybrid_rrf":
            dense_rows = dense_retriever.search(
                question["question"], filters=question.get("filter"), top_k=candidate_k
            )
            lexical_rows = apply_filters(
                lexical.search(question["question"], top_k=len(lexical.chunks)),
                question.get("filter"),
            )[:candidate_k]
            candidate_lists = {"dense": dense_rows, "lexical": lexical_rows}
            api_calls += 1
            results = rrf(dense_rows, lexical_rows)[:top_k]
        else:
            raise ValueError(f"unknown method: {method}")

        elapsed_ms = (time.perf_counter() - start) * 1000
        context, context_ids = pack_context(results, budget=context_budget)
        marked = [{**row, "rank": rank, "hit": hit(row, question["gold"])}
                  for rank, row in enumerate(results, start=1)]
        traces.append({
            "query_id": question["id"], "split": question["split"], "question": question["question"],
            "method": method, "top_k": top_k, "candidate_k": candidate_k,
            "filter": question.get("filter"), "results": marked,
            "context": context, "context_ids": context_ids, "context_chars": len(context),
            "hit1": bool(marked and marked[0]["hit"]),
            "hit3": any(row["hit"] for row in marked[:3]),
            "context_hit": any(row["hit"] and row["id"] in context_ids for row in marked),
            "elapsed_ms": round(elapsed_ms, 3),
        })
        if candidate_lists is not None:
            traces[-1]["candidate_results"] = candidate_lists
    n = len(traces)
    summary = {
        "method": method, "split": questions[0]["split"], "n_answerable": n,
        "hit1": sum(t["hit1"] for t in traces),
        "hit1_rate": sum(t["hit1"] for t in traces) / n,
        "evidence_hit_at_3": sum(t["hit3"] for t in traces),
        "evidence_hit_at_3_rate": sum(t["hit3"] for t in traces) / n,
        "context_evidence": sum(t["context_hit"] for t in traces),
        "context_evidence_rate": sum(t["context_hit"] for t in traces) / n,
        "mean_query_ms": round(sum(t["elapsed_ms"] for t in traces) / n, 3),
        "embedding_api_calls": api_calls,
        "embedding_tokens": None,
        "service_cost_usd": None,
        "cost_note": "Provider token usage/pricing was not returned by the embedding endpoint; USD cost not inferred.",
        "lexical_index_seconds": index_seconds,
        "top_k": top_k, "candidate_k": candidate_k, "context_budget_chars": context_budget,
    }
    return traces, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark TF-IDF, dense pgvector, and hybrid RRF on dev")
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--output", type=Path, default=Path("starter/results/retrieval-step5"))
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--candidate-k", type=int, default=10)
    parser.add_argument("--context-budget", type=int, default=2500)
    args = parser.parse_args()
    if args.top_k < 3 or args.candidate_k < args.top_k:
        raise ValueError("top-k must be >= 3 and candidate-k must be >= top-k")

    chunks = json.loads((REPO / "data/day6_chunks.json").read_text(encoding="utf-8"))
    questions = json.loads((REPO / "data/questions.json").read_text(encoding="utf-8"))
    selected = [q for q in questions if q["split"] == args.split]
    if not selected:
        raise ValueError(f"No answerable questions for split {args.split}")

    index_start = time.perf_counter()
    lexical = TfidfIndex(chunks)
    index_seconds = time.perf_counter() - index_start
    dense_retriever = RealRetriever(strategy="A")
    all_traces = []
    summaries = []
    for method in ("tfidf", "dense", "hybrid_rrf"):
        traces, summary = evaluate_method(
            method, selected, lexical, dense_retriever,
            top_k=args.top_k, candidate_k=args.candidate_k,
            context_budget=args.context_budget, index_seconds=round(index_seconds, 6),
        )
        all_traces.extend(traces)
        summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False))

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "traces.json").write_text(
        json.dumps(all_traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "summary.json").write_text(
        json.dumps({"split": args.split, "n_questions": len(selected), "methods": summaries},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
