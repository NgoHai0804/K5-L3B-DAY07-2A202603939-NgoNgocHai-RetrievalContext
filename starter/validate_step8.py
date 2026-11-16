"""Validate Step 8 agent evaluation artifacts."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
cases = json.loads((REPO / "data/cases.json").read_text(encoding="utf-8"))
test_cases = {c["id"]: c for c in cases if c["split"] == "test"}


def check(run: str) -> None:
    base = REPO / "starter/results" / run
    traces = json.loads((base / "agent_traces.json").read_text(encoding="utf-8"))
    reviews = json.loads((base / "reviews.json").read_text(encoding="utf-8"))
    summary = json.loads((base / "summary.json").read_text(encoding="utf-8"))
    tracemap = {t["query_id"]: t for t in traces}
    revmap = {r["query_id"]: r for r in reviews}
    assert len(tracemap) == len(traces) == 10, f"{run}: duplicate/missing traces"
    assert len(revmap) == len(reviews) == 10, f"{run}: duplicate/missing reviews"
    assert set(tracemap) == set(test_cases) == set(revmap), f"{run}: id mismatch"
    for cid, case in test_cases.items():
        t = tracemap[cid]
        r = revmap[cid]
        assert isinstance(r["citation_support"], list)
        assert len(r["citation_support"]) == len(t["citations"]), f"{run}/{cid}: support length mismatch"
        if case["answerable"]:
            assert r["answer_grade"] in (0, 1, 2), f"{run}/{cid}: bad grade"
            if t["status"] == "abstain":
                assert r["answer_grade"] == 0, f"{run}/{cid}: abstain on answerable must be 0"
        else:
            assert isinstance(r["abstention_correct"], bool), f"{run}/{cid}: missing abstention_correct"
    assert summary["provider_errors"] == 0
    print(f"{run}: OK  tool_use={summary['tool_use']['n']}/{summary['tool_use']['N']} "
          f"grounded_mean={summary['grounded_answer']['mean']} "
          f"citation={summary['citation_validity']['n']}/{summary['citation_validity']['N']} "
          f"abstention={summary['abstention']['n']}/{summary['abstention']['N']} "
          f"false_abstention={summary['false_abstention']['n']}/{summary['false_abstention']['N']}")


check("agent-test")
check("agent-test-baseline")
print("OK: Step 8 artifacts valid.")