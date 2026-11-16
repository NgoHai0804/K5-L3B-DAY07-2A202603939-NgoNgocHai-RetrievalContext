"""Evaluate dense retriever (RealRetriever) hit quality on a split using the gold evidence."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from agentic import RealRetriever

REPO = ROOT.parent
chunks = json.loads((REPO / "data" / "day6_chunks.json").read_text(encoding="utf-8"))
questions = json.loads((REPO / "data" / "questions.json").read_text(encoding="utf-8"))


def hit(chunk, gold):
    return any(chunk["source_id"] == g["source_id"] and chunk["page"] == g["page"] and g["evidence"] in chunk["text"] for g in gold)


def main():
    split = sys.argv[1] if len(sys.argv) > 1 else "dev"
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    retriever = RealRetriever()
    sel = [q for q in questions if q["split"] == split]
    hit1 = hit3 = hitk = 0
    rows = []
    for q in sel:
        res = retriever.search(q["question"], filters=q.get("filter"), top_k=top_k)
        marks = [hit(c, q["gold"]) for c in res]
        rank = next((i + 1 for i, m in enumerate(marks) if m), None)
        hit1 += bool(marks and marks[0])
        hit3 += any(marks[:3])
        hitk += rank is not None
        rows.append((q["id"], rank, len(res)))
    print(f"split={split} n={len(sel)} top_k={top_k}")
    print(f"Hit@1 = {hit1}/{len(sel)} ({hit1/len(sel):.3f})")
    print(f"Evidence Hit@3 = {hit3}/{len(sel)} ({hit3/len(sel):.3f})")
    print(f"Evidence Hit@{top_k} = {hitk}/{len(sel)} ({hitk/len(sel):.3f})")
    for r in rows:
        print(f"  {r[0]}: rank={r[1]} returned={r[2]}")


if __name__ == "__main__":
    main()
