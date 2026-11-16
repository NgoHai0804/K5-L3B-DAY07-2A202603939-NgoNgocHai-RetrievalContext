"""Run the real agent over a split and save traces for agent_metrics.py.

- RealController (LLM via OpenRouter) + RealRetriever (Day 6 pgvector).
- Provider/retriever errors are recorded with status "error" (not hidden).
- No benchmark gold enters the agent loop.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from agentic import RealController, RealRetriever, run_agent  # noqa: E402

REPO = ROOT.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Chạy agent thật trên một split và lưu trace")
    parser.add_argument("--split", choices=("dev", "test"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-searches", type=int, default=3)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--budget", type=int, default=2500)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    cases = json.loads((REPO / "data" / "cases.json").read_text(encoding="utf-8"))
    selected = [c for c in cases if c["split"] == args.split]

    retriever = RealRetriever()
    controller = RealController(model=args.model)

    traces = []
    for case in selected:
        qid = case["id"]
        started = time.perf_counter()
        try:
            result = run_agent(
                case["question"], controller, retriever,
                filters=case.get("filter"),
                max_searches=args.max_searches, top_k=args.top_k, budget=args.budget,
            )
            status = result["status"]
            answer = result["answer"]
            citations = result["citations"]
            events = result["events"]
        except Exception as exc:  # provider/retriever errors reported separately
            status = "error"
            answer = ""
            citations = []
            events = [{"event": "error", "error_type": type(exc).__name__, "message": str(exc)[:300]}]
        elapsed_ms = (time.perf_counter() - started) * 1000
        trace = {
            "query_id": qid,
            "split": args.split,
            "question": case["question"],
            "answerable": case["answerable"],
            "status": status,
            "answer": answer,
            "citations": citations,
            "events": events,
            "n_searches": sum(e.get("event") == "search" for e in events),
            "elapsed_ms": round(elapsed_ms, 1),
        }
        traces.append(trace)
        print(f"{qid}: {status} citations={len(citations)} searches={trace['n_searches']} {elapsed_ms:.0f}ms")

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "agent_traces.json").write_text(
        json.dumps(traces, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "split": args.split,
        "n": len(traces),
        "answered": sum(t["status"] == "answered" for t in traces),
        "abstain": sum(t["status"] == "abstain" for t in traces),
        "error": sum(t["status"] == "error" for t in traces),
        "config": {"max_searches": args.max_searches, "top_k": args.top_k,
                   "budget": args.budget, "model": controller.model},
    }
    (args.output / "agent_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
