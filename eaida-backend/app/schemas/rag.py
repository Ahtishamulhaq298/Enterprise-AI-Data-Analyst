from typing import Literal

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: int
    title: str
    source: str
    n_chunks: int
    visibility_role: str

    class Config:
        from_attributes = True


class RAGQuery(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=20)
    mode: Literal["hybrid", "semantic", "keyword"] = "hybrid"
    dataset_id: int | None = None


class Citation(BaseModel):
    document_id: int
    title: str
    chunk_id: str
    score: float
    snippet: str


class RAGAnswer(BaseModel):
    question: str
    answer: str
    citations: list[Citation]
    mode: str


class AgentRequest(BaseModel):
    dataset_id: int
    question: str
    target_column: str | None = None


class AgentResponse(BaseModel):
    dataset_id: int
    question: str
    steps: list[dict]
    final_answer: str


class EvalRequest(BaseModel):
    questions: list[str]
    ground_truths: list[str] | None = None