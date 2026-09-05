"""Evaluation controller: RAG quality metrics + model job summary metrics."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_analyst, require_viewer
from app.db.session import get_db
from app.evaluation.rag_eval import evaluate
from app.models.job import Job, JobStatus, JobType
from app.models.user import User
from app.schemas.rag import EvalRequest

router = APIRouter()


@router.post("/rag", summary="Evaluate RAG quality (faithfulness, relevancy, precision)")
def evaluate_rag(payload: EvalRequest, _: User = Depends(require_analyst)):
    if not payload.questions:
        raise HTTPException(status_code=422, detail="Provide at least one question")
    return evaluate(payload.questions, payload.ground_truths)


@router.get("/models", summary="Aggregate metrics across all successful AutoML jobs")
def model_metrics(db: Session = Depends(get_db), _: User = Depends(require_viewer)):
    jobs = (db.query(Job)
            .filter(Job.job_type == JobType.AUTOML, Job.status == JobStatus.SUCCESS)
            .order_by(Job.id.desc()).all())
    return {"count": len(jobs), "jobs": [{
        "job_id": j.id, "dataset_id": j.dataset_id,
        "task_type": j.result.get("task_type"),
        "best_model": j.result.get("best_model", {}).get("name"),
        "metrics": j.result.get("best_model", {}).get("metrics"),
    } for j in jobs]}