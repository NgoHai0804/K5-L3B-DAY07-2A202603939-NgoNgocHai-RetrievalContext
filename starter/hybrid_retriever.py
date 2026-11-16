"""Hybrid (dense RRF + lexical) retriever adapter for the agent (chosen I1 method)."""
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from agentic import RealRetriever  # noqa: E402
from baseline import TfidfIndex  # noqa: E402
from benchmark_retrieval import apply_filters, rrf  # noqa: E402


class HybridRetriever:
    """Dense qwen3-embedding + TF-IDF fused with RRF, same as the chosen Step 7 config."""

    def __init__(self, strategy: str = "A", candidate_k: int = 20) -> None:
        self.candidate_k = candidate_k
        self.dense = RealRetriever(strategy=strategy)
        self.chunks = json.loads((REPO / "data/day6_chunks.json").read_text(encoding="utf-8"))
        self.lex = TfidfIndex(self.chunks)

    def search(self, query: str, *, filters: dict[str, Any] | None = None,
               top_k: int = 3) -> list[dict[str, Any]]:
        dense_rows = self.dense.search(query, filters=filters, top_k=self.candidate_k)
        lex_rows = apply_filters(self.lex.search(query, top_k=len(self.chunks)), filters)[: self.candidate_k]
        fused = rrf(dense_rows, lex_rows)
        return fused[:top_k]