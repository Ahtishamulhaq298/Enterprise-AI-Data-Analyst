"""Data profiling controller."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_analyst, require_viewer
from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.job import Job, JobStatus, JobType
from app.models.user import User
from app.schemas.analysis import JobOut, ProfilingRequest
from app.services.ingestion import load_dataframe
from app.services.profiling import profile_dataframe

router = APIRouter()


@router.post("/run", response_model=JobOut, summary="Run a full profiling job on a dataset")
def run_profiling(payload: ProfilingRequest, db: Session = Depends(get_db),
                  user: User = Depends(require_analyst)):
    dataset = db.get(Dataset, payload.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    job = Job(job_type=JobType.PROFILING, status=JobStatus.RUNNING,
              dataset_id=dataset.id, user_id=user.id, params=payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        df = load_dataframe(dataset.file_path, nrows=payload.sample_rows)
        job.result = profile_dataframe(df)
        job.status = JobStatus.SUCCESS
    except Exception as exc:
        job.status, job.error = JobStatus.FAILED, str(exc)
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}", response_model=JobOut, summary="Fetch a profiling job result")
def get_profiling(job_id: int, db: Session = Depends(get_db),
                  _: User = Depends(require_viewer)):
    job = db.get(Job, job_id)
    if not job or job.job_type != JobType.PROFILING:
        raise HTTPException(status_code=404, detail="Profiling job not found")
    return job


@router.get("/dataset/{dataset_id}/quality", summary="Quick data-quality check (no job saved)")
def quality_check(dataset_id: int, db: Session = Depends(get_db),
                  _: User = Depends(require_viewer)):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    profile = profile_dataframe(load_dataframe(dataset.file_path))
    return {"dataset_id": dataset_id, "shape": profile["shape"],
            "duplicate_rows": profile["duplicate_rows"],
            "quality_issues": profile["quality_issues"]}


@router.get("/dataset/{dataset_id}/correlations", summary="Numeric correlation matrix")
def correlations(dataset_id: int, db: Session = Depends(get_db),
                 _: User = Depends(require_viewer)):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    profile = profile_dataframe(load_dataframe(dataset.file_path))
    return {"dataset_id": dataset_id, "correlations": profile["correlations"]}