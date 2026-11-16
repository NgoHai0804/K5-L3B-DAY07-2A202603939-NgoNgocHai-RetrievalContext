"""Validate Step 7 test evaluation artifacts."""
import json
from pathlib import Path

p = Path("starter/results/step7-test")
summary = json.loads((p / "summary.json").read_text(encoding="utf-8"))
traces = json.loads((p / "traces.json").read_text(encoding="utf-8"))

print("split:", summary["split"], "| n_questions:", summary["n_questions"])
print("locked_before_test:", summary["locked_config"]["locked_before_test"])
print("chosen:", summary["locked_config"]["chosen_config"]["name"])
print("configs:", [c["config"] for c in summary["configs"]])

for name, rows in traces.items():
    splits = {r["split"] for r in rows}
    assert splits == {"test"}, f"{name} leaked non-test split"
    assert len(rows) == summary["n_questions"]
    print(f"{name}: n={len(rows)} hit1={sum(r['hit1'] for r in rows)} "
          f"hit3={sum(r['hit3'] for r in rows)} "
          f"grades={ {g: sum(1 for r in rows if r['context_grade']==g) for g in (0,1,2)} }")

assert summary["locked_config"]["locked_before_test"] is True
assert {c["config"] for c in summary["configs"]} >= {"baseline_tfidf", "I1_deep_context"}
print("OK: Step 7 evaluated baseline + locked chosen config on the same test split.")