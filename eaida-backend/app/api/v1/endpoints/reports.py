"""Automated reporting controller."""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import require_analyst, require_viewer
from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.job import Job, JobStatus, JobType
from app.models.user import User
from app.schemas.analysis import JobOut, ReportRequest
from app.services.explainability import global_explanation
from app.services.ingestion import load_dataframe
from app.services.llm import chat
from app.services.reporting import build_markdown_report, save_markdown, save_pdf

router = APIRouter()


@router.post("/generate", response_model=JobOut,
             summary="Generate an automated analysis report (markdown or PDF)")
def generate(payload: ReportRequest, db: Session = Depends(get_db),
             user: User = Depends(require_analyst)):
    dataset = db.get(Dataset, payload.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    job = Job(job_type=JobType.REPORT, status=JobStatus.RUNNING, dataset_id=dataset.id,
              user_id=user.id, params=payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        profiling = automl = explanation = None
        if payload.profiling_job_id:
            pj = db.get(Job, payload.profiling_job_id)
            profiling = pj.result if pj else None
        if payload.automl_job_id:
            aj = db.get(Job, payload.automl_job_id)
            if aj and aj.status == JobStatus.SUCCESS:
                automl = aj.result
                try:
                    df = load_dataframe(dataset.file_path)
                    target = aj.result.get("target_column")
                    X = df.drop(columns=[target]) if target in df.columns else df
                    explanation = global_explanation(aj.artifact_path, X, top_k=10)
                except Exception:
                    explanation = None

        narrative = chat(
            "Write a 150-word executive summary for business stakeholders based on:\n"
            f"PROFILE: {str(profiling)[:2500]}\nMODELS: {str(automl)[:2000]}"
        )

        markdown = build_markdown_report(payload.title, dataset.name, profiling,
                                         automl, explanation, narrative)
        filename = f"report_{dataset.id}_{job.id}"
        artifact = (save_pdf(markdown, filename) if payload.format == "pdf"
                    else save_markdown(markdown, filename))

        job.artifact_path = artifact
        job.result = {"format": payload.format, "title": payload.title,
                      "markdown_preview": markdown[:2000]}
        job.status = JobStatus.SUCCESS
    except Exception as exc:
        job.status, job.error = JobStatus.FAILED, str(exc)
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobOut], summary="List generated reports")
def list_reports(db: Session = Depends(get_db), _: User = Depends(require_viewer)):
    return db.query(Job).filter(Job.job_type == JobType.REPORT).order_by(Job.id.desc()).all()


@router.get("/{job_id}/download", summary="Download a generated report file")
def download(job_id: int, db: Session = Depends(get_db), _: User = Depends(require_viewer)):
    job = db.get(Job, job_id)
    if not job or job.job_type != JobType.REPORT or not job.artifact_path:
        raise HTTPException(status_code=404, detail="Report not found")
    path = Path(job.artifact_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file missing on disk")
    media = "application/pdf" if path.suffix == ".pdf" else "text/markdown"
    return FileResponse(str(path), filename=path.name, media_type=media)