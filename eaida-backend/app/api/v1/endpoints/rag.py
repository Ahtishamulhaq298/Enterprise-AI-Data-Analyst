"""Knowledge-base / RAG controller: document ingestion, hybrid search, grounded Q&A."""
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_admin, require_analyst, require_viewer
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.rag import vectorstore
from app.rag.chunking import chunk_text, extract_text
from app.rag.hybrid import hybrid_search
from app.rag.pipeline import answer_question
from app.schemas.rag import DocumentOut, RAGAnswer, RAGQuery

router = APIRouter()

ALLOWED = {".pdf", ".docx", ".txt", ".md", ".csv"}


@router.post("/documents", response_model=DocumentOut, status_code=201,
             summary="Upload a document and index it into the vector store")
def upload_document(file: UploadFile = File(...), title: str = Form(""),
                    visibility_role: str = Form("viewer"),
                    db: Session = Depends(get_db), user: User = Depends(require_analyst)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Unsupported type '{suffix}'")

    dest = Path(settings.UPLOAD_DIR) / f"kb_{uuid.uuid4().hex}{suffix}"
    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    text = extract_text(str(dest))
    chunks = chunk_text(text)
    if not chunks:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="No extractable text found in document")

    doc = Document(title=title or (file.filename or dest.name), source=str(dest),
                   content=text[:20000], n_chunks=len(chunks),
                   visibility_role=visibility_role, owner_id=user.id)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    vectorstore.add_chunks(doc.id, doc.title, chunks, visibility_role)
    logger.info(f"Indexed document {doc.id} ({len(chunks)} chunks)")
    return doc


@router.get("/documents", response_model=list[DocumentOut], summary="List indexed documents")
def list_documents(db: Session = Depends(get_db), _: User = Depends(require_viewer)):
    return db.query(Document).order_by(Document.id.desc()).all()


@router.delete("/documents/{document_id}", status_code=204,
               summary="Delete a document and its vectors (admin only)")
def delete_document(document_id: int, db: Session = Depends(get_db),
                    _: User = Depends(require_admin)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    vectorstore.delete_document(document_id)
    Path(doc.source).unlink(missing_ok=True)
    db.delete(doc)
    db.commit()


@router.post("/search", summary="Hybrid / semantic / keyword retrieval (no LLM)")
def search(payload: RAGQuery, _: User = Depends(require_viewer)):
    hits = hybrid_search(payload.question, payload.top_k, payload.mode)
    return {"query": payload.question, "mode": payload.mode, "hits": hits}


@router.post("/query", response_model=RAGAnswer,
             summary="Grounded question answering with citations")
def query(payload: RAGQuery, _: User = Depends(require_viewer)):
    return answer_question(payload.question, payload.top_k, payload.mode)


@router.get("/stats", summary="Vector store statistics")
def stats(_: User = Depends(require_viewer)):
    return {"collection": vectorstore.COLLECTION,
            "chunks": vectorstore.get_collection().count(),
            "embedding_model": settings.EMBEDDING_MODEL}