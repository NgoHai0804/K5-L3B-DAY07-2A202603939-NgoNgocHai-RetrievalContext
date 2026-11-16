"""Validate Step 6 improvement artifacts."""
import json
from pathlib import Path

p = Path("starter/results/improvements-dev")
summary = json.loads((p / "summary.json").read_text(encoding="utf-8"))
traces = json.loads((p / "traces.json").read_text(encoding="utf-8"))
errors = json.loads((p / "error_analysis.json").read_text(encoding="utf-8"))

print("selection_criteria present:", bool(summary.get("selection_criteria")))
print("configs:", [c["config"] for c in summary["configs"]])
print("n_questions:", summary["n_questions"], "| rewrite_tokens_total:", summary["rewrite_tokens_total"])

for name, rows in traces.items():
    n = len(rows)
    splits = {r["split"] for r in rows}
    grades = sorted({r["context_grade"] for r in rows})
    print(f"{name}: traces={n} splits={splits} grades={grades} "
          f"hit1={sum(r['hit1'] for r in rows)} hit3={sum(r['hit3'] for r in rows)}")
    assert splits == {"dev"}, "test split leaked into Step 6"
    assert all(len(r["results"]) <= 8 for r in rows)

print("error_analysis cases:", len(errors), [e["query_id"] for e in errors])
assert len(errors) >= 2
print("OK: Step 6 artifacts valid, dev-only, >=2 analyzed errors.")