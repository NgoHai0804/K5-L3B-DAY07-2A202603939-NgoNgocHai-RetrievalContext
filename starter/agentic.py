"""Agent loop and real model/retriever adapters for Day 7.

Connects to the real Day 6 PostgreSQL + pgvector store and calls real models via OpenRouter.
"""
import json
import os
import re
from pathlib import Path
from typing import Any, Protocol

from dotenv import load_dotenv
from baseline import pack_context

load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parents[1] / ".env")


class Controller(Protocol):
    def decide(self, question: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        """Call a real model with a search tool; return normalized action.

        Search: {'action': 'search', 'query': '...'}.
        Final: {'action': 'answer', 'answer': '...', 'citations': ['chunk-id']}.
        Citations must also appear as [chunk-id] in the answer text.
        """
        ...


class Retriever(Protocol):
    def search(self, query: str, *, filters: dict[str, Any] | None, top_k: int) -> list[dict[str, Any]]:
        """Query the real Day 6 vector store with a compatible query embedding.

        Return each chunk's id, text, source_id, source, page, metadata and score.
        The query embedding model and dimension must match the document index.
        """
        ...


def run_agent(question: str, controller: Controller, retriever: Retriever, *,
              filters: dict[str, Any] | None = None, max_searches: int = 4,
              top_k: int = 3, budget: int = 800) -> dict[str, Any]:
    """Return answer, citation IDs and trace; no benchmark gold enters this loop.

    A final answer without valid citations, an empty context, and a search limit
    lead to abstention. This only checks citation IDs, not semantic grounding.
    Provider/retriever errors propagate; no silent mock fallback.
    """
    if not question.strip() or max_searches < 1 or top_k < 1 or budget < 1:
        raise ValueError('question, max_searches, top_k hoặc budget không hợp lệ')
    history: list[dict[str, Any]] = []
    chunks: dict[str, dict[str, Any]] = {}
    candidates: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    for _ in range(max_searches + 1):
        action = controller.decide(question, history)
        if action.get('action') == 'search':
            if sum(e['event'] == 'search' for e in events) >= max_searches:
                return {'status': 'abstain', 'answer': 'Không đủ bằng chứng để trả lời.', 'citations': [], 'events': events + [{'event': 'search_limit'}]}
            query = action.get('query')
            if not isinstance(query, str) or not query.strip():
                raise ValueError('search query phải là chuỗi không rỗng')
            results = retriever.search(query, filters=filters, top_k=top_k)
            if len(results) > top_k or len({r['id'] for r in results}) != len(results):
                raise ValueError('retriever phải trả tối đa top_k chunk ID duy nhất')
            candidates.extend(results)
            context, ids = pack_context(candidates, budget=budget)
            chunks = {c['id']: c for c in candidates if c['id'] in ids}
            events.append({'event': 'search', 'query': query, 'filter': filters, 'results': results,
                           'context': context, 'context_ids': ids})
            # Send only the latest cumulative context; avoid multiplying the budget.
            history = [{'tool': 'search', 'queries': [e['query'] for e in events if e['event'] == 'search'],
                        'context': context, 'context_ids': ids}]
        elif action.get('action') == 'answer':
            answer, citations = action.get('answer'), action.get('citations')
            if not isinstance(answer, str) or not isinstance(citations, list) or any(not isinstance(i, str) for i in citations):
                raise ValueError('answer/citations không hợp lệ')
            valid = bool(answer.strip() and citations and all(i in chunks and f'[{i}]' in answer for i in citations))
            if valid:
                return {'status': 'answered', 'answer': answer, 'citations': citations, 'events': events + [{'event': 'answer'}]}
            return {'status': 'abstain', 'answer': 'Không đủ bằng chứng để trả lời.', 'citations': [], 'events': events + [{'event': 'invalid_or_missing_citations'}]}
        else:
            raise ValueError('action phải là search hoặc answer')
    return {'status': 'abstain', 'answer': 'Không đủ bằng chứng để trả lời.', 'citations': [], 'events': events}


class RealRetriever:
    """Real retriever querying Day 6 pgvector store using real qwen3-embedding-8b."""

    def __init__(self, db_url: str | None = None, model: str = "qwen/qwen3-embedding-8b",
                 strategy: str = "A", api_key: str | None = None) -> None:
        self.db_url = db_url or os.environ.get(
            "DATABASE_URL",
            "postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab"
        )
        self.model = model
        self.strategy = strategy
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY missing from environment")

        from openai import OpenAI
        self._client = OpenAI(api_key=self.api_key, base_url="https://openrouter.ai/api/v1")

    def _embed(self, text: str) -> list[float]:
        resp = self._client.embeddings.create(model=self.model, input=[text])
        return resp.data[0].embedding

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        import psycopg

        vec = self._embed(query)
        vec_literal = "[" + ",".join(format(float(x), ".10g") for x in vec) + "]"

        where = ["strategy = %s"]
        params: list[Any] = [self.strategy]
        if filters:
            allowed = {"section", "year", "document_id", "source"}
            for k, v in filters.items():
                if k in allowed:
                    where.append(f"{k} = %s")
                    params.append(v)
        where_sql = " AND ".join(where)
        sql = f"""
            SELECT id, text, document_id, source, page, metadata,
                   1 - (embedding <=> %s::vector) AS score
            FROM chunks
            WHERE {where_sql}
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """
        with psycopg.connect(self.db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, [vec_literal, *params, vec_literal, top_k])
                rows = cur.fetchall()

        results: list[dict[str, Any]] = []
        seen = set()
        for r in rows:
            cid = r[0]
            if cid in seen:
                continue
            seen.add(cid)
            results.append({
                "id": cid,
                "text": r[1],
                "source_id": r[2],
                "source": r[3],
                "page": r[4],
                "metadata": r[5] or {},
                "score": float(r[6])
            })
        return results[:top_k]


class RealController:
    """Real controller calling an LLM (e.g. openai/gpt-4o-mini) via OpenRouter."""

    def __init__(self, model: str | None = None, api_key: str | None = None,
                 base_url: str = "https://openrouter.ai/api/v1") -> None:
        self.model = model or os.environ.get("AGENT_MODEL", "openai/gpt-4o-mini")
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY missing from environment")

        from openai import OpenAI
        self._client = OpenAI(api_key=self.api_key, base_url=base_url)

    def decide(self, question: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        if not history:
            system_msg = (
                "You are an AI research assistant coordinating legal information retrieval.\n"
                "Output ONLY a valid JSON object.\n"
                "To search the document collection, generate a search action with concise keywords:\n"
                '{"action": "search", "query": "<search query>"}'
            )
            user_msg = f"User Question: {question}\nGenerate a search action:"
        else:
            context = history[-1].get("context", "")
            context_ids = history[-1].get("context_ids", [])
            system_msg = (
                "You are a strict, grounded AI assistant answering questions about legal NLP survey papers.\n"
                "Rules:\n"
                "1. Answer ONLY using facts directly stated in the provided context chunks.\n"
                "2. Every claim in your answer MUST cite its supporting chunk using [chunk_id] directly in the text.\n"
                "3. If the context has sufficient evidence, output:\n"
                '   {"action": "answer", "answer": "<answer text with [chunk_id]>", "citations": ["chunk_id", ...]}\n'
                "4. If the context is empty or lacks evidence and cannot be answered, output:\n"
                '   {"action": "answer", "answer": "Không đủ bằng chứng để trả lời.", "citations": []}\n'
                "5. If you believe a different search query might find the answer, output:\n"
                '   {"action": "search", "query": "<new search query>"}\n'
                "6. Output MUST be valid JSON only, no markdown wrapping, no explanation."
            )
            user_msg = (
                f"Question: {question}\n\n"
                f"Available Context Chunks (Valid IDs: {context_ids}):\n"
                f"{context}\n\n"
                "Decide the next action (answer with citations, abstain, or search again):"
            )

        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        raw_text = resp.choices[0].message.content.strip()
        try:
            action = json.loads(raw_text)
        except Exception:
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                action = json.loads(match.group(0))
            else:
                action = {"action": "answer", "answer": "Không đủ bằng chứng để trả lời.", "citations": []}

        if action.get("action") not in ("search", "answer"):
            action["action"] = "answer"
            action["answer"] = "Không đủ bằng chứng để trả lời."
            action["citations"] = []
        return action

