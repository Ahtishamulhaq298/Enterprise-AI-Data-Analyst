from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ProfilingRequest(BaseModel):
    dataset_id: int
    sample_rows: int = 100_000


class FeatureEngineeringRequest(BaseModel):
    dataset_id: int
    target_column: str | None = None
    drop_high_cardinality: bool = True
    create_date_parts: bool = True
    create_interactions: bool = False
    save_as_new_dataset: bool = True


class AutoMLRequest(BaseModel):
    dataset_id: int
    target_column: str
    task_type: Literal["auto", "classification", "regression"] = "auto"
    test_size: float = Field(default=0.2, gt=0.05, lt=0.6)
    cv_folds: int = Field(default=3, ge=2, le=10)
    max_models: int = Field(default=6, ge=1, le=10)
    random_state: int = 42


class PredictRequest(BaseModel):
    job_id: int
    records: list[dict[str, Any]]


class ExplainRequest(BaseModel):
    job_id: int
    top_k: int = 15
    row_index: int | None = None       # None => global explanation


class ReportRequest(BaseModel):
    dataset_id: int
    automl_job_id: int | None = None
    profiling_job_id: int | None = None
    title: str = "Automated Data Analysis Report"
    format: Literal["markdown", "pdf"] = "pdf"


class JobOut(BaseModel):
    id: int
    job_type: str
    status: str
    dataset_id: int
    user_id: int
    params: dict
    result: dict
    artifact_path: str
    error: str
    created_at: datetime
    finished_at: datetime | None

    class Config:
        from_attributes = True