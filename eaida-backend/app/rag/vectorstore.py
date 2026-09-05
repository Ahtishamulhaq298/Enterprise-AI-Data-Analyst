"""ChromaDB persistent vector store + sentence-transformer embeddings."""
from __future__ import annotations

from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings
from loguru import logger

from app.core.config import settings

COLLECTION = "eaida_knowledge"


@lru_cache
def get_embedder():
    from sentence_transformers import SentenceTransformer
    logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
    return SentenceTransformer(settings.EMBEDDING_MODEL)


@lru_cache
def get_collection():
    client = chromadb.PersistentClient(
        path=settings.CHROMA_DIR,
        settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
    )
    return client.get_or_create_collection(name=COLLECTION,
                                           metadata={"hnsw:space": "cosine"})


def embed(texts: list[str]) -> list[list[float]]:
    return get_embedder().encode(texts, normalize_embeddings=True).tolist()


def add_chunks(document_id: int, title: str, chunks: list[str],
               visibility_role: str = "viewer") -> int:
    col = get_collection()
    ids = [f"doc{document_id}_chunk{i}" for i in range(len(chunks))]
    metadatas = [{"document_id": document_id, "title": title, "chunk_index": i,
                  "visibility_role": visibility_role} for i in range(len(chunks))]
    col.add(ids=ids, documents=chunks, embeddings=embed(chunks), metadatas=metadatas)
    return len(ids)


def delete_document(document_id: int) -> None:
    get_collection().delete(where={"document_id": document_id})


def semantic_search(query: str, top_k: int = 10, where: dict | None = None) -> list[dict]:
    col = get_collection()
    if col.count() == 0:
        return []
    res = col.query(query_embeddings=embed([query]),
                    n_results=min(top_k, col.count()),
                    where=where or None)
    hits = []
    for i in range(len(res["ids"][0])):
        distance = res["distances"][0][i] if res.get("distances") else 0.0
        hits.append({
            "chunk_id": res["ids"][0][i],
            "text": res["documents"][0][i],
            "metadata": res["metadatas"][0][i],
            "score": round(1.0 - float(distance), 4),
        })
    return hits


def all_chunks() -> list[dict]:
    col = get_collection()
    if col.count() == 0:
        return []
    data = col.get(include=["documents", "metadatas"])
    return [{"chunk_id": data["ids"][i], "text": data["documents"][i],
             "metadata": data["metadatas"][i]} for i in range(len(data["ids"]))]