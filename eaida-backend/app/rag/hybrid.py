"""Hybrid retrieval = dense (Chroma) + sparse (BM25), fused with Reciprocal Rank Fusion."""
from __future__ import annotations

from rank_bm25 import BM25Okapi

from app.rag import vectorstore


def keyword_search(query: str, top_k: int = 10) -> list[dict]:
    corpus = vectorstore.all_chunks()
    if not corpus:
        return []
    tokenized = [c["text"].lower().split() for c in corpus]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.lower().split())
    ranked = sorted(zip(corpus, scores), key=lambda t: t[1], reverse=True)[:top_k]
    return [{**c, "score": round(float(s), 4)} for c, s in ranked if s > 0]


def reciprocal_rank_fusion(rankings: list[list[dict]], k: int = 60) -> list[dict]:
    fused: dict[str, dict] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            cid = hit["chunk_id"]
            entry = fused.setdefault(cid, {**hit, "score": 0.0})
            entry["score"] += 1.0 / (k + rank)
    out = sorted(fused.values(), key=lambda h: h["score"], reverse=True)
    for hit in out:
        hit["score"] = round(hit["score"], 5)
    return out


def hybrid_search(query: str, top_k: int = 5, mode: str = "hybrid") -> list[dict]:
    if mode == "semantic":
        return vectorstore.semantic_search(query, top_k)
    if mode == "keyword":
        return keyword_search(query, top_k)
    dense = vectorstore.semantic_search(query, top_k * 3)
    sparse = keyword_search(query, top_k * 3)
    return reciprocal_rank_fusion([dense, sparse])[:top_k]