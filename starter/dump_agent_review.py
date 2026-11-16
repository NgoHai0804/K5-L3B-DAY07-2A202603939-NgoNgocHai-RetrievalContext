"""Dump agent traces joined with gold + cited chunk text for manual review (Step 8)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
traces_file = REPO / sys.argv[1]
chunks = json.loads((REPO / "data/day6_chunks.json").read_text(encoding="utf-8"))
chunk_map = {c["id"]: c for c in chunks}
answerable = json.loads((REPO / "data/questions.json").read_text(encoding="utf-8"))
unanswerable = json.loads((REPO / "data/unanswerable_questions.json").read_text(encoding="utf-8"))
gold_by_id = {q["id"]: q for q in answerable}
unan_by_id = {q["id"]: q for q in unanswerable}

traces = json.loads(traces_file.read_text(encoding="utf-8"))


def has_gold_evidence(text: str, gold) -> bool:
    return any(g["evidence"] in text for g in gold)


for t in traces:
    qid = t["query_id"]
    print("=" * 90)
    print(f"[{qid}] status={t['status']} n_searches={t['n_searches']}")
    print("Q:", t["question"])
    if qid in gold_by_id:
        q = gold_by_id[qid]
        print("EXPECTED:", q["expected_answer"])
        print("GOLD:", q["gold"])
    else:
        u = unan_by_id[qid]
        print("UNANSWERABLE:", u["absence_reason"])
    print("ANSWER:", t["answer"])
    print("CITATIONS:", t["citations"])
    gold = gold_by_id.get(qid, {}).get("gold", [])
    for cid in t["citations"]:
        c = chunk_map.get(cid)
        if not c:
            print(f"  cite {cid}: (not a known chunk)")
            continue
        supports = has_gold_evidence(c["text"], gold) if gold else None
        print(f"  cite {cid}: page={c['page']} source={c['source_id']} gold_evidence_present={supports}")
        print("    text:", c["text"][:280].replace("\n", " "))
    if t.get("events"):
        for e in t["events"]:
            if e.get("event") == "search":
                print(f"  search query: {e['query']!r} filter={e.get('filter')} ids={e.get('context_ids')}")
            elif e.get("event") == "error":
                print("  ERROR:", e)