"""Full lab audit: data integrity, artifacts, and cross-check with the report."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
from baseline import validate  # noqa: E402

problems = []


def load(p):
    return json.loads((REPO / p).read_text(encoding="utf-8"))


chunks = load("data/day6_chunks.json")
questions = load("data/questions.json")
unanswerable = load("data/unanswerable_questions.json")
cases = load("data/cases.json")

# Chunks
if len(chunks) != 386:
    problems.append(f"chunks count {len(chunks)} != 386")
ids = [c["id"] for c in chunks]
if len(ids) != len(set(ids)):
    problems.append("duplicate chunk ids")
for c in chunks:
    for k in ("id", "text", "source_id", "source", "page", "metadata"):
        if k not in c or c[k] is None:
            problems.append(f"chunk {c.get('id')} missing {k}")

# Answerable questions
if len(questions) != 27:
    problems.append(f"questions count {len(questions)} != 27")
dev = [q for q in questions if q["split"] == "dev"]
test = [q for q in questions if q["split"] == "test"]
if (len(dev), len(test)) != (19, 8):
    problems.append(f"split counts dev/test = {len(dev)}/{len(test)} != 19/8")
qids = [q["id"] for q in questions]
if len(qids) != len(set(qids)):
    problems.append("duplicate question ids")
try:
    validate(chunks, questions)  # validates gold in one chunk, unique ids, split
except Exception as e:  # noqa: BLE001
    problems.append(f"validate failed: {e}")

# Unanswerable
if len(unanswerable) != 4:
    problems.append(f"unanswerable count {len(unanswerable)} != 4")
u_dev = [q for q in unanswerable if q["split"] == "dev"]
u_test = [q for q in unanswerable if q["split"] == "test"]
if (len(u_dev), len(u_test)) != (2, 2):
    problems.append(f"unanswerable split dev/test = {len(u_dev)}/{len(u_test)} != 2/2")
for q in unanswerable:
    if q.get("answerable") is not False:
        problems.append(f"{q['id']} answerable not false")
    if q.get("expected_behavior") != "search_and_abstain":
        problems.append(f"{q['id']} expected_behavior wrong")
    if not q.get("absence_reason"):
        problems.append(f"{q['id']} missing absence_reason")

# Cases
if len(cases) != 31:
    problems.append(f"cases count {len(cases)} != 31")
cids = [c["id"] for c in cases]
if len(cids) != len(set(cids)):
    problems.append("duplicate case ids")
if set(cids) != set(qids) | {q["id"] for q in unanswerable}:
    problems.append("case ids do not match questions + unanswerable")

# Artifacts referenced by the report
for p in [
    "starter/results/agent-dev/agent_traces.json",
    "starter/results/agent-test/agent_traces.json",
    "starter/results/agent-test/reviews.json",
    "starter/results/agent-test/summary.json",
    "starter/results/agent-test-baseline/agent_traces.json",
    "starter/results/agent-test-baseline/summary.json",
    "starter/results/retrieval-step5/summary.json",
    "starter/results/retrieval-step5/traces.json",
    "starter/results/improvements-dev/summary.json",
    "starter/results/improvements-dev/error_analysis.json",
    "starter/results/step7-test/summary.json",
    "starter/results/step7-lock/CHOSEN_CONFIG.json",
]:
    if not (REPO / p).exists():
        problems.append(f"missing artifact {p}")

# Report must exist with the correct name
if not (REPO / "report/individual/2A202603939_NgoNgocHai.md").exists():
    problems.append("missing student report file")

if problems:
    print("PROBLEMS:")
    for p in problems:
        print(" -", p)
    raise SystemExit(1)
print("AUDIT OK: data, splits, cases, artifacts, and report all consistent.")