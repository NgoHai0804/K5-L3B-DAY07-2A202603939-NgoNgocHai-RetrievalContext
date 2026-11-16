"""Step 6: two improvement configurations on dev + error analysis + context grading.

Reference baseline (C0) is the Step 5 hybrid RRF. Improvements:
  I1 - deeper hybrid context: more candidates + larger context budget.
  I2 - LLM query rewriting before hybrid retrieval.

All runs use the same 386 Strategy A chunks, the same 19 dev answerable questions,
Hit@1 / Evidence Hit@3 at cutoff 3, and context packed with pack_context.
No test split is touched.
"""
import json
import os
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

SELECTION_CRITERIA = (
    "Chọn cấu hình theo thứ tự ưu tiên công bố trước khi chạy test: "
    "(1) Context Evidence Rate cao nhất; (2) Evidence Hit@3 cao nhất; "
    "(3) chi phí/thời gian thấp nhất. Test chưa được chạy ở bước này."
)


def make_rewriter():
    from openai import OpenAI

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    model = os.environ.get("REWRITE_MODEL", "openai/gpt-4o-mini")

    def rewrite(question: str) -> tuple[str, int]:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content":
                 "Rewrite the user's question into a short keyword search query for a legal-NLP "
                 "research corpus. Keep entity names and numbers. Output only the query."},
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            max_tokens=60,
        )
        text = (resp.choices[0].message.content or "").strip()
        usage = getattr(resp, "usage", None)
        tokens = (getattr(usage, "prompt_tokens", 0) or 0) + (getattr(usage, "completion_tokens", 0) or 0)
        return (text or question), tokens

    return rewrite


def grade_context(context_ids: list[str], chunk_map: dict[str, dict[str, Any]],
                  gold: list[dict[str, Any]], context_text: str) -> tuple[int, str]:
    for cid in context_ids:
        chunk = chunk_map.get(cid)
        if chunk and hit(chunk, gold):
            return 2, f"chunk {cid} đúng nguồn/trang và chứa evidence"
    for g in gold:
        if g["evidence"] in context_text:
            return 1, "evidence có trong context nhưng thiếu chunk đúng nguồn/trang"
    return 0, "không có evidence trong context"


def main() -> None:
    chunks = json.loads((REPO / "data/day6_chunks.json").read_text(encoding="utf-8"))
    questions = json.loads((REPO / "data/questions.json").read_text(encoding="utf-8"))
    dev = [q for q in questions if q["split"] == "dev"]
    chunk_map = {c["id"]: c for c in chunks}

    lexical = TfidfIndex(chunks)
    dense = RealRetriever(strategy="A")
    rewrite = make_rewriter()

    configs = {
        "C0_hybrid_baseline": {"top_k": 3, "budget": 2500, "candidate_k": 10, "rewrite": False},
        "I1_deep_context": {"top_k": 8, "budget": 4500, "candidate_k": 20, "rewrite": False},
        "I2_rewrite_hybrid": {"top_k": 5, "budget": 3500, "candidate_k": 10, "rewrite": True},
    }

    # Precompute retrieval per question once, reuse across configs.
    prepared: dict[str, dict[str, Any]] = {}
    total_rewrite_tokens = 0
    for q in dev:
        filters = q.get("filter")
        dense20 = dense.search(q["question"], filters=filters, top_k=20)
        lex20 = apply_filters(lexical.search(q["question"], top_k=len(chunks)), filters)[:20]
        rewritten, tokens = rewrite(q["question"])
        total_rewrite_tokens += tokens
        dense_rw = dense.search(rewritten, filters=filters, top_k=20)
        lex_rw = apply_filters(lexical.search(rewritten, top_k=len(chunks)), filters)[:20]
        prepared[q["id"]] = {
            "q": q, "dense20": dense20, "lex20": lex20,
            "dense_rw": dense_rw, "lex_rw": lex_rw, "rewritten": rewritten,
        }

    results_by_config: dict[str, list[dict[str, Any]]] = {}
    summaries = []
    for name, cfg in configs.items():
        traces = []
        for q in dev:
            data = prepared[q["id"]]
            dense_rows = data["dense_rw"] if cfg["rewrite"] else data["dense20"]
            dense_rows = dense_rows[:cfg["candidate_k"]]
            lex_rows = (data["lex_rw"] if cfg["rewrite"] else data["lex20"])[:cfg["candidate_k"]]
            fused = rrf(dense_rows, lex_rows)
            top = fused[:cfg["top_k"]]
            context, context_ids = pack_context(top, budget=cfg["budget"])
            grade, reason = grade_context(context_ids, chunk_map, q["gold"], context)
            marked = [{**row, "rank": i + 1, "hit": hit(row, q["gold"])}
                      for i, row in enumerate(top)]
            traces.append({
                "query_id": q["id"], "config": name, "split": q["split"],
                "question": q["question"], "used_query": data["rewritten"] if cfg["rewrite"] else q["question"],
                "filter": q.get("filter"), "results": marked,
                "context_ids": context_ids, "context_chars": len(context),
                "est_context_tokens": round(len(context) / 4),
                "hit1": bool(fused[:1] and hit(fused[0], q["gold"])),
                "hit3": any(hit(c, q["gold"]) for c in fused[:3]),
                "context_grade": grade, "context_reason": reason,
            })
        n = len(traces)
        grade_counts = {g: sum(1 for t in traces if t["context_grade"] == g) for g in (0, 1, 2)}
        summary = {
            "config": name, "split": "dev", "n_answerable": n,
            "hypothesis": {
                "C0_hybrid_baseline": "Mốc so sánh: hybrid RRF top-3, budget 2500.",
                "I1_deep_context": "Lấy sâu hơn (20 candidate, top-8, budget 4500) để evidence hạng 4-8 lọt vào context, tăng Context Evidence Rate; đánh đổi context lớn hơn.",
                "I2_rewrite_hybrid": "LLM viết lại câu hỏi thành query từ khóa trước khi hybrid, kỳ vọng tăng Hit@1/Hit@3 cho câu thiếu ngữ cảnh; đánh đổi thêm 1 LLM call/query.",
            }[name],
            "top_k": cfg["top_k"], "candidate_k": cfg["candidate_k"],
            "context_budget_chars": cfg["budget"], "context_unit": "ký tự (est tokens = chars/4)",
            "hit1": sum(t["hit1"] for t in traces), "hit1_rate": sum(t["hit1"] for t in traces) / n,
            "evidence_hit_at_3": sum(t["hit3"] for t in traces),
            "evidence_hit_at_3_rate": sum(t["hit3"] for t in traces) / n,
            "context_evidence_rate": grade_counts[2], "context_evidence_rate_value": grade_counts[2] / n,
            "context_grade_counts": {"0": grade_counts[0], "1": grade_counts[1], "2": grade_counts[2]},
            "mean_context_chars": round(sum(t["context_chars"] for t in traces) / n, 1),
            "mean_est_context_tokens": round(sum(t["est_context_tokens"] for t in traces) / n),
            "embedding_api_calls": n,
            "llm_rewrite_calls": n if cfg["rewrite"] else 0,
        }
        summaries.append(summary)
        results_by_config[name] = traces

    # Error analysis: questions missed by C0 but recovered by I1.
    c0 = {t["query_id"]: t for t in results_by_config["C0_hybrid_baseline"]}
    i1 = {t["query_id"]: t for t in results_by_config["I1_deep_context"]}
    i2 = {t["query_id"]: t for t in results_by_config["I2_rewrite_hybrid"]}
    error_analysis = []
    for qid in c0:
        if c0[qid]["context_grade"] < 2 or not c0[qid]["hit3"]:
            error_analysis.append({
                "query_id": qid,
                "question": c0[qid]["question"],
                "c0": {"hit1": c0[qid]["hit1"], "hit3": c0[qid]["hit3"], "ctx_grade": c0[qid]["context_grade"]},
                "i1": {"hit3": i1[qid]["hit3"], "ctx_grade": i1[qid]["context_grade"]},
                "i2": {"hit3": i2[qid]["hit3"], "ctx_grade": i2[qid]["context_grade"],
                       "rewritten": i2[qid]["used_query"]},
            })

    out = REPO / "starter/results/improvements-dev"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps({
        "selection_criteria": SELECTION_CRITERIA,
        "split": "dev", "n_questions": len(dev),
        "rewrite_tokens_total": total_rewrite_tokens,
        "total_embedding_api_calls": 2 * len(dev),
        "total_llm_rewrite_calls": len(dev),
        "cost_note": "Chat rewrite tokens counted from API usage; embedding endpoint returned no usage/pricing, so USD not inferred.",
        "configs": summaries,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "traces.json").write_text(json.dumps(results_by_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "error_analysis.json").write_text(json.dumps(error_analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for s in summaries:
        print(json.dumps(s, ensure_ascii=False))
    print("rewrite_tokens_total:", total_rewrite_tokens)
    print("errors analyzed:", len(error_analysis))


if __name__ == "__main__":
    main()