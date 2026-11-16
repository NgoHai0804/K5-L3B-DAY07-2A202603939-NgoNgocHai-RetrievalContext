import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter"))
from benchmark_retrieval import apply_filters, rrf


class RetrievalBenchmarkTests(unittest.TestCase):
    def test_rrf_combines_rankings_and_deduplicates_ids(self):
        dense = [{"id": "a", "score": 0.9}, {"id": "b", "score": 0.8}]
        lexical = [{"id": "b", "score": 0.7}, {"id": "c", "score": 0.6}]

        results = rrf(dense, lexical, k=0)

        self.assertEqual([row["id"] for row in results], ["b", "a", "c"])
        self.assertEqual(results[0]["score"], 1.5)
        self.assertEqual(results[0]["dense_rank"], 2)
        self.assertEqual(results[0]["lexical_rank"], 1)
        self.assertEqual(len({row["id"] for row in results}), 3)

    def test_filters_match_source_id_for_document_id(self):
        rows = [
            {"id": "a", "source_id": "doc-a", "metadata": {"section": "overview"}},
            {"id": "b", "source_id": "doc-b", "metadata": {"section": "overview"}},
        ]

        results = apply_filters(rows, {"document_id": "doc-a", "section": "overview"})

        self.assertEqual([row["id"] for row in results], ["a"])

    def test_rejects_unsupported_filter(self):
        with self.assertRaises(ValueError):
            apply_filters([], {"password": "secret"})


if __name__ == "__main__":
    unittest.main()
