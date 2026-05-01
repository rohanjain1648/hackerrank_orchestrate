"""
Indexer — builds a TF-IDF semantic search index.
No external dependencies — pure Python with numpy for speed.
"""
import re
import math
import numpy as np
from typing import List, Optional
from collections import defaultdict

from schemas import CorpusChunk

def _tokenize(text: str) -> List[str]:
    """Simple alphanumeric tokenizer."""
    return re.findall(r'\b[a-z0-9]+\b', text.lower())

class CorpusIndex:
    """In-memory TF-IDF index."""

    def __init__(self):
        self._chunks: List[CorpusChunk] = []
        self._vocab = {}
        self._idf = []
        self._tfidf_matrix: Optional[np.ndarray] = None
        self._company_indices: dict = {}

    def build(self, chunks: List[CorpusChunk]) -> None:
        """Build TF-IDF matrix for all chunks."""
        self._chunks = chunks
        
        print(f"    Building TF-IDF index for {len(chunks)} chunks...")
        
        # 1. Build vocabulary and doc frequency
        doc_freqs = defaultdict(int)
        doc_tokens = []
        
        for chunk in chunks:
            # Add extra weight to titles by repeating them
            text = f"{chunk.title} {chunk.title} {chunk.text}"
            tokens = _tokenize(text)
            unique_tokens = set(tokens)
            doc_tokens.append(tokens)
            for token in unique_tokens:
                doc_freqs[token] += 1
                
        # 2. Assign indices to vocabulary and compute IDF
        num_docs = len(chunks)
        self._vocab = {token: idx for idx, token in enumerate(doc_freqs.keys())}
        vocab_size = len(self._vocab)
        
        self._idf = np.zeros(vocab_size, dtype=np.float32)
        for token, idx in self._vocab.items():
            # Standard IDF formula: log(N / (1 + df))
            self._idf[idx] = math.log(num_docs / (1.0 + doc_freqs[token]))
            
        # 3. Compute TF-IDF matrix
        print(f"    Computing TF-IDF matrix ({num_docs}x{vocab_size})...")
        matrix = np.zeros((num_docs, vocab_size), dtype=np.float32)
        
        for doc_idx, tokens in enumerate(doc_tokens):
            term_counts = defaultdict(int)
            for token in tokens:
                term_counts[token] += 1
                
            # Log normalization for TF
            for token, count in term_counts.items():
                vocab_idx = self._vocab[token]
                tf = 1.0 + math.log(count)
                matrix[doc_idx, vocab_idx] = tf * self._idf[vocab_idx]
                
        # L2 Normalize the matrix for faster cosine similarity
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._tfidf_matrix = matrix / norms
        
        # Build company index for fast filtering
        self._company_indices = {}
        for i, chunk in enumerate(chunks):
            company = chunk.company.lower()
            if company not in self._company_indices:
                self._company_indices[company] = []
            self._company_indices[company].append(i)

        print(f"  Indexed {len(chunks)} chunks")

    def _vectorize_query(self, query: str) -> np.ndarray:
        """Convert query string into normalized TF-IDF vector."""
        tokens = _tokenize(query)
        term_counts = defaultdict(int)
        for token in tokens:
            term_counts[token] += 1
            
        vec = np.zeros(len(self._vocab), dtype=np.float32)
        for token, count in term_counts.items():
            if token in self._vocab:
                vocab_idx = self._vocab[token]
                tf = 1.0 + math.log(count)
                vec[vocab_idx] = tf * self._idf[vocab_idx]
                
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def query(
        self,
        query_text: str,
        n_results: int = 10,
        company_filter: Optional[str] = None,
    ) -> List[dict]:
        """TF-IDF semantic search."""
        if self._tfidf_matrix is None:
            raise RuntimeError("Index not built. Call build() first.")

        query_vec = self._vectorize_query(query_text)
        
        # Fast exit if query is entirely unknown words
        if np.sum(query_vec) == 0:
            return []

        # Filter by company if specified
        if company_filter and company_filter.lower() in self._company_indices:
            indices = self._company_indices[company_filter.lower()]
            filtered_matrix = self._tfidf_matrix[indices]
            
            # Since both are L2 normalized, dot product == cosine similarity
            similarities = filtered_matrix @ query_vec
            
            top_k = min(n_results, len(indices))
            top_idx = np.argsort(similarities)[::-1][:top_k]

            results = []
            for idx in top_idx:
                orig_idx = indices[idx]
                chunk = self._chunks[orig_idx]
                results.append({
                    "id": chunk.chunk_id,
                    "text": chunk.text,
                    "title": chunk.title,
                    "company": chunk.company,
                    "category": chunk.category,
                    "source_url": chunk.source_url,
                    "distance": 1.0 - float(similarities[idx]),
                })
            return [r for r in results if r["distance"] < 1.0] # Only return actual matches
        else:
            # Search all
            similarities = self._tfidf_matrix @ query_vec
            top_k = min(n_results, len(self._chunks))
            top_idx = np.argsort(similarities)[::-1][:top_k]

            results = []
            for idx in top_idx:
                chunk = self._chunks[idx]
                results.append({
                    "id": chunk.chunk_id,
                    "text": chunk.text,
                    "title": chunk.title,
                    "company": chunk.company,
                    "category": chunk.category,
                    "source_url": chunk.source_url,
                    "distance": 1.0 - float(similarities[idx]),
                })
            return [r for r in results if r["distance"] < 1.0]

if __name__ == "__main__":
    from corpus_loader import load_corpus

    print("Loading corpus...")
    chunks = load_corpus()
    print("\nBuilding index...")
    idx = CorpusIndex()
    idx.build(chunks)
    print("\nTesting query: 'how to pause subscription'")
    results = idx.query("how to pause subscription", n_results=3, company_filter="hackerrank")
    for r in results:
        print(f"\n  [{r['company']}] {r['title'][:60]} (dist: {r['distance']:.3f})")
        print(f"  {r['text'][:150]}...")
