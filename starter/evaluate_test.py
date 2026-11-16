"""Step 7: evaluate the locked chosen config and the baseline on the held-out test split.

Configuration was locked in starter/results/step7-lock/CHOSEN_CONFIG.json before this ran.
No parameter is tuned here; test is used only for the final, independent evaluation.
"""
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
from benchmark_retrieval import apply_filters, rrf  # noqa: E402


def grade_context(context_ids, chunk_map, gold, context_text):
    for cid in context_ids:
        chunk = chunk_map.get(cid)
        if chunk and hit(chunk, gold):
            return 2, f"chunk {cid} đúng nguồn/trang và chứa evidence"
    for g in gold:
        if g["evidence"] in context_text:
            return 1, "evidence có trong context nhưng thiếu chunk đúng nguồn/trang"
    return 0, "không có evidence trong context"


def main() -> None:
    lock = json.loads((ROOT / "results/step7-lock/CHOSEN_CONFIG.json").read_text(encoding="utf-8"))
    assert lock["locked_before_test"] is True

    chunks = json.loads((REPO / "data/day6_chunks.json").read_text(encoding="utf-8"))
    questions = json.loads((REPO / "data/questions.json").read_text(encoding="utf-8"))
    test = [q for q in questions if q["split"] == "test"]
    chunk_map = {c["id"]: c for c in chunks}

    lexical = TfidfIndex(chunks)
    dense = RealRetriever(strategy="A")

    configs = {
        lock["baseline_config"]["name"]: {"kind": "tfidf", "top_k": lock["baseline_config"]["top_k"],
                                          "budget": lock["baseline_config"]["context_budget_chars"], "candidate_k": 0},
        lock["reference_config"]["name"]: {"kind": "hybrid", "top_k": lock["reference_config"]["top_k"],
                                           "budget": lock["reference_config"]["context_budget_chars"],
                                           "candidate_k": lock["reference_config"]["candidate_k"]},
        lock["chosen_config"]["name"]: {"kind": "hybrid", "top_k": lock["chosen_config"]["top_k"],
                                        "budget": lock["chosen_config"]["context_budget_chars"],
                                        "candidate_k": lock["chosen_config"]["candidate_k"]},
    }

    # Precompute dense/lexical candidates once per test question.
    prepared: dict[str, dict[str, Any]] = {}
    for q in test:
        filters = q.get("filter")
        t0 = time.perf_counter()
        dense20 = dense.search(q["question"], filters=filters, top_k=20)
        dense_ms = (time.perf_counter() - t0) * 1000
        lex20 = apply_filters(lexical.search(q["question"], top_k=len(chunks)), filters)[:20]
        prepared[q["id"]] = {"q": q, "dense20": dense20, "lex20": lex20, "dense_ms": dense_ms}

    summaries = []
    store: dict[str, list[dict[str, Any]]] = {}
    for name, cfg in configs.items():
        traces = []
        for q in test:
            d = prepared[q["id"]]
            start = time.perf_counter()
            if cfg["kind"] == "tfidf":
                top = d["lex20"][:cfg["top_k"]]
                dense_part = 0.0
            else:
                fused = rrf(d["dense20"][:cfg["candidate_k"]], d["lex20"][:cfg["candidate_k"]])
                top = fused[:cfg["top_k"]]
                dense_part = d["dense_ms"]
            context, context_ids = pack_context(top, budget=cfg["budget"])
            overhead_ms = (time.perf_counter() - start) * 1000
            grade, reason = grade_context(context_ids, chunk_map, q["gold"], context)
            marked = [{**row, "rank": i + 1, "hit": hit(row, q["gold"])} for i, row in enumerate(top)]
            traces.append({
                "query_id": q["id"], "config": name, "split": "test",
                "question": q["question"], "filter": q.get("filter"), "results": marked,
                "context_ids": context_ids, "context_chars": len(context),
                "est_context_tokens": round(len(context) / 4),
                "hit1": bool(top[:1] and hit(top[0], q["gold"])),
                "hit3": any(hit(c, q["gold"]) for c in top[:3]),
                "context_grade": grade, "context_reason": reason,
                "elapsed_ms": round(dense_part + overhead_ms, 3),
            })
        n = len(traces)
        gc = {g: sum(1 for t in traces if t["context_grade"] == g) for g in (0, 1, 2)}
        summaries.append({
            "config": name, "kind": cfg["kind"], "split": "test", "n_answerable": n,
            "top_k": cfg["top_k"], "candidate_k": cfg["candidate_k"], "context_budget_chars": cfg["budget"],
            "hit1": sum(t["hit1"] for t in traces), "hit1_rate": sum(t["hit1"] for t in traces) / n,
            "evidence_hit_at_3": sum(t["hit3"] for t in traces),
            "evidence_hit_at_3_rate": sum(t["hit3"] for t in traces) / n,
            "context_evidence_rate": gc[2], "context_evidence_rate_value": gc[2] / n,
            "context_grade_counts": {"0": gc[0], "1": gc[1], "2": gc[2]},
            "mean_context_chars": round(sum(t["context_chars"] for t in traces) / n, 1),
            "mean_est_context_tokens": round(sum(t["est_context_tokens"] for t in traces) / n),
            "mean_query_ms": round(sum(t["elapsed_ms"] for t in traces) / n, 3),
            "embedding_api_calls": n if cfg["kind"] == "hybrid" else 0,
            "service_cost_usd": None,
            "cost_note": "Embedding endpoint returned no usage/pricing; USD not inferred. TF-IDF has zero API cost.",
        })
        store[name] = traces

    out = ROOT / "results/step7-test"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps({"split": "test", "n_questions": len(test),
                                                   "locked_config": lock, "configs": summaries},
                                                  ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "traces.json").write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for s in summaries:
        print(json.dumps(s, ensure_ascii=False))


if __name__ == "__main__":
    main()