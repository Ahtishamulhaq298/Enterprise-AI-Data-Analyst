"""Lightweight RAG evaluation (RAGAS when installed, heuristic metrics otherwise)."""
from __future__ import annotations

import numpy as np
from loguru import logger

from app.rag.pipeline import answer_question
from app.rag.vectorstore import embed


def _cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(va @ vb / denom) if denom else 0.0


def evaluate(questions: list[str], ground_truths: list[str] | None = None) -> dict:
    rows = []
    for i, q in enumerate(questions):
        result = answer_question(q, top_k=5)
        contexts = [c["snippet"] for c in result["citations"]]
        answer = result["answer"]

        vectors = embed([answer] + contexts) if contexts else [embed([answer])[0]]
        answer_vec, ctx_vecs = vectors[0], vectors[1:]
        faithfulness = float(np.mean([_cosine(answer_vec, c) for c in ctx_vecs])) if ctx_vecs else 0.0

        q_vec = embed([q])[0]
        relevancy = _cosine(q_vec, answer_vec)
        precision = float(np.mean([_cosine(q_vec, c) for c in ctx_vecs])) if ctx_vecs else 0.0

        row = {"question": q, "answer": answer, "n_contexts": len(contexts),
               "faithfulness": round(faithfulness, 4),
               "answer_relevancy": round(relevancy, 4),
               "context_precision": round(precision, 4)}
        if ground_truths and i < len(ground_truths):
            gt_vec = embed([ground_truths[i]])[0]
            row["answer_correctness"] = round(_cosine(gt_vec, answer_vec), 4)
        rows.append(row)

    keys = ["faithfulness", "answer_relevancy", "context_precision", "answer_correctness"]
    aggregate = {k: round(float(np.mean([r[k] for r in rows if k in r])), 4)
                 for k in keys if any(k in r for r in rows)}
    logger.info(f"RAG evaluation aggregate: {aggregate}")
    return {"aggregate": aggregate, "per_question": rows}