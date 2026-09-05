"""RAG answer pipeline: retrieve -> build grounded prompt -> generate -> cite."""
from __future__ import annotations

from app.rag.hybrid import hybrid_search
from app.services.llm import chat

PROMPT = """Answer the QUESTION using only the CONTEXT below.
Cite sources inline as [S1], [S2] matching the context blocks.
If the context does not contain the answer, reply exactly:
"The knowledge base does not contain enough information to answer this."

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


def answer_question(question: str, top_k: int = 5, mode: str = "hybrid") -> dict:
    hits = hybrid_search(question, top_k=top_k, mode=mode)
    if not hits:
        return {"question": question, "mode": mode, "citations": [],
                "answer": "The knowledge base is empty or no relevant passage was found."}

    blocks = "\n\n".join(f"[S{i + 1}] {h['text'][:1200]}" for i, h in enumerate(hits))
    answer = chat(PROMPT.format(context=blocks, question=question))

    citations = [{
        "document_id": int(h["metadata"].get("document_id", 0)),
        "title": str(h["metadata"].get("title", "")),
        "chunk_id": h["chunk_id"],
        "score": float(h["score"]),
        "snippet": h["text"][:280],
    } for h in hits]

    return {"question": question, "answer": answer, "citations": citations, "mode": mode}