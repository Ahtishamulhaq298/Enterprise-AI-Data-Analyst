"""Explainability controller: global feature importance + local (per-row) explanations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_viewer
from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.job import Job, JobStatus, JobType
from app.models.user import User
from app.schemas.analysis import ExplainRequest
from app.services.explainability import global_explanation, local_explanation
from app.services.ingestion import load_dataframe

router = APIRouter()


def _load_job_and_frame(job_id: int, db: Session):
    job = db.get(Job, job_id)
    if not job or job.job_type != JobType.AUTOML or job.status != JobStatus.SUCCESS:
        raise HTTPException(status_code=404, detail="Successful AutoML job not found")
    dataset = db.get(Dataset, job.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Source dataset not found")
    df = load_dataframe(dataset.file_path)
    target = job.result.get("target_column")
    y = df[target] if target in df.columns else None
    X = df.drop(columns=[target]) if target in df.columns else df
    return job, X, y


@router.post("/global", summary="Global feature importance for a trained model")
def explain_global(payload: ExplainRequest, db: Session = Depends(get_db),
                   _: User = Depends(require_viewer)):
    job, X, y = _load_job_and_frame(payload.job_id, db)
    try:
        return {"job_id": job.id, **global_explanation(job.artifact_path, X, y, payload.top_k)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Explanation failed: {exc}")


@router.post("/local", summary="Explain a single prediction (row-level SHAP contributions)")
def explain_local(payload: ExplainRequest, db: Session = Depends(get_db),
                  _: User = Depends(require_viewer)):
    if payload.row_index is None:
        raise HTTPException(status_code=422, detail="row_index is required for local explanations")
    job, X, _y = _load_job_and_frame(payload.job_id, db)
    try:
        return {"job_id": job.id,
                **local_explanation(job.artifact_path, X, payload.row_index, payload.top_k)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Explanation failed: {exc}")