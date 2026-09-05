"""AutoML controller: train, compare, leaderboard, predict, download model."""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from loguru import logger
from sqlalchemy.orm import Session

from app.core.deps import require_analyst, require_viewer
from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.job import Job, JobStatus, JobType
from app.models.user import User
from app.schemas.analysis import AutoMLRequest, JobOut, PredictRequest
from app.services.automl import predict_with_model, run_automl
from app.services.ingestion import load_dataframe

router = APIRouter()


@router.post("/train", response_model=JobOut,
             summary="Train and compare candidate models (AutoML)")
def train(payload: AutoMLRequest, db: Session = Depends(get_db),
          user: User = Depends(require_analyst)):
    dataset = db.get(Dataset, payload.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    job = Job(job_type=JobType.AUTOML, status=JobStatus.RUNNING, dataset_id=dataset.id,
              user_id=user.id, params=payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        df = load_dataframe(dataset.file_path)
        result = run_automl(df, payload.target_column, payload.task_type,
                            payload.test_size, payload.cv_folds, payload.max_models,
                            payload.random_state, job_id=job.id)
        job.artifact_path = result.pop("artifact_path")
        job.result = result
        job.status = JobStatus.SUCCESS
        logger.info(f"AutoML job {job.id} best model: {result['best_model']['name']}")
    except Exception as exc:
        job.status, job.error = JobStatus.FAILED, str(exc)
        logger.error(f"AutoML job {job.id} failed: {exc}")
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs", response_model=list[JobOut], summary="List AutoML jobs")
def list_jobs(dataset_id: int | None = None, db: Session = Depends(get_db),
              _: User = Depends(require_viewer)):
    query = db.query(Job).filter(Job.job_type == JobType.AUTOML)
    if dataset_id:
        query = query.filter(Job.dataset_id == dataset_id)
    return query.order_by(Job.id.desc()).all()


@router.get("/jobs/{job_id}", response_model=JobOut, summary="Get one AutoML job")
def get_job(job_id: int, db: Session = Depends(get_db), _: User = Depends(require_viewer)):
    job = db.get(Job, job_id)
    if not job or job.job_type != JobType.AUTOML:
        raise HTTPException(status_code=404, detail="AutoML job not found")
    return job


@router.get("/jobs/{job_id}/leaderboard", summary="Model comparison leaderboard")
def leaderboard(job_id: int, db: Session = Depends(get_db),
                _: User = Depends(require_viewer)):
    job = db.get(Job, job_id)
    if not job or job.job_type != JobType.AUTOML:
        raise HTTPException(status_code=404, detail="AutoML job not found")
    if job.status != JobStatus.SUCCESS:
        raise HTTPException(status_code=409, detail=f"Job status is {job.status.value}")
    return {"job_id": job.id, "task_type": job.result.get("task_type"),
            "best_model": job.result.get("best_model"),
            "leaderboard": job.result.get("leaderboard", [])}


@router.post("/predict", summary="Run inference with a trained model")
def predict(payload: PredictRequest, db: Session = Depends(get_db),
            _: User = Depends(require_viewer)):
    job = db.get(Job, payload.job_id)
    if not job or job.job_type != JobType.AUTOML or not job.artifact_path:
        raise HTTPException(status_code=404, detail="Trained model not found for this job")
    try:
        return {"job_id": job.id, **predict_with_model(job.artifact_path, payload.records)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Prediction failed: {exc}")


@router.get("/jobs/{job_id}/model", summary="Download the trained model artifact")
def download_model(job_id: int, db: Session = Depends(get_db),
                   _: User = Depends(require_analyst)):
    job = db.get(Job, job_id)
    if not job or not job.artifact_path or not Path(job.artifact_path).exists():
        raise HTTPException(status_code=404, detail="Model artifact not found")
    return FileResponse(job.artifact_path, filename=Path(job.artifact_path).name,
                        media_type="application/octet-stream")