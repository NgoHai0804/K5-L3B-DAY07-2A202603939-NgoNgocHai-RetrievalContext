"""Validate Step 5 retrieval benchmark artifacts."""
import json
from pathlib import Path

p = Path("starter/results/retrieval-step5")
s = json.loads((p / "summary.json").read_text(encoding="utf-8"))
t = json.loads((p / "traces.json").read_text(encoding="utf-8"))

print("summary methods:", [m["method"] for m in s["methods"]])
print("n_questions:", s["n_questions"], "| traces:", len(t))

req = {"id", "text", "source_id", "source", "page", "metadata", "score", "rank", "hit"}
problems = []
for x in t:
    if x["split"] != "dev":
        problems.append(("split", x["query_id"]))
    if len(x["results"]) > x["top_k"]:
        problems.append(("top_k", x["query_id"]))
    for r in x["results"]:
        missing = req - set(r)
        if missing:
            problems.append(("missing-fields", x["query_id"], sorted(missing)))
    ids = [r["id"] for r in x["results"]]
    if len(ids) != len(set(ids)):
        problems.append(("dup-ids", x["query_id"]))

h = [x for x in t if x["method"] == "hybrid_rrf"]
no_cand = [x["query_id"] for x in h if "candidate_results" not in x]
print("hybrid traces missing candidates:", no_cand)
print("problems:", problems[:5], "| total problems:", len(problems))

methods = {}
for x in t:
    methods.setdefault(x["method"], set()).add(x["query_id"])
print("query sets equal across methods:", len({frozenset(v) for v in methods.values()}) == 1)
print("all fields ok:", not problems)