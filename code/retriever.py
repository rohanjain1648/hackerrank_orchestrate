"""
Retriever — two-stage retrieval: semantic search + re-ranking.
"""
from typing import List, Optional

from config import TOP_K_RETRIEVAL, TOP_K_CONTEXT
from indexer import CorpusIndex


class Retriever:
    """Retrieves and re-ranks relevant support docs for a given ticket."""

    def __init__(self, index: CorpusIndex):
        self._index = index

    def retrieve(
        self,
        query: str,
        company: Optional[str] = None,
        top_k: int = TOP_K_CONTEXT,
    ) -> List[dict]:
        """
        Retrieve top-k most relevant docs.

        Strategy:
        1. If company is known, search within that company's docs first
        2. Also search across all docs for cross-domain matches
        3. Re-rank by combining distance score + company match bonus
        4. Return top_k results
        """
        results = []
        company_norm = company.lower().strip() if company and company.lower() not in ("none", "nan", "") else None

        # Stage 1: Company-filtered search
        if company_norm:
            filtered = self._index.query(
                query_text=query,
                n_results=TOP_K_RETRIEVAL,
                company_filter=company_norm,
            )
            results.extend(filtered)

        # Stage 2: Global search (catches cross-domain or when company is unknown)
        global_results = self._index.query(
            query_text=query,
            n_results=TOP_K_RETRIEVAL,
            company_filter=None,
        )

        # Merge, deduplicate
        seen_ids = {r["id"] for r in results}
        for r in global_results:
            if r["id"] not in seen_ids:
                results.append(r)
                seen_ids.add(r["id"])

        # Stage 3: Re-rank with company bonus
        for r in results:
            score = 1.0 - r.get("distance", 1.0)  # convert distance to similarity
            if company_norm and r.get("company", "").lower() == company_norm:
                score += 0.15  # boost matching company docs
            r["relevance_score"] = score

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:top_k]

    def format_context(self, docs: List[dict]) -> str:
        """Format retrieved docs as context string for the LLM."""
        if not docs:
            return "No relevant support documentation found."

        parts = []
        for i, doc in enumerate(docs, 1):
            parts.append(
                f"--- Document {i} ---\n"
                f"Source: {doc.get('company', 'unknown').upper()} / {doc.get('category', 'General')}\n"
                f"Title: {doc.get('title', 'Untitled')}\n"
                f"URL: {doc.get('source_url', 'N/A')}\n"
                f"Content:\n{doc.get('text', '')}\n"
            )
        return "\n".join(parts)
