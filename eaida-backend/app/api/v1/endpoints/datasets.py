"""Dataset controller: upload, list, preview, schema, delete."""
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_admin, require_analyst, require_viewer
from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.user import User
from app.schemas.dataset import DatasetOut, DatasetPreview
from app.services.ingestion import infer_column_meta, load_dataframe

router = APIRouter()

ALLOWED = {".csv", ".xlsx", ".xls", ".json", ".parquet", ".txt"}


@router.post("/upload", response_model=DatasetOut, status_code=201,
             summary="Upload a tabular dataset (analyst/admin)")
def upload_dataset(file: UploadFile = File(...), name: str = Form(""),
                   description: str = Form(""), db: Session = Depends(get_db),
                   user: User = Depends(require_analyst)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(status_code=400,
                            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED)}")

    stored_name = f"{uuid.uuid4().hex}{suffix}"
    dest = Path(settings.UPLOAD_DIR) / stored_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        df = load_dataframe(str(dest))
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Could not parse file: {exc}")

    dataset = Dataset(name=name or (file.filename or stored_name), description=description,
                      file_path=str(dest), file_type=suffix.lstrip("."),
                      n_rows=int(df.shape[0]), n_cols=int(df.shape[1]),
                      columns_meta=infer_column_meta(df), owner_id=user.id)
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    logger.info(f"Dataset {dataset.id} uploaded by user {user.id} ({df.shape})")
    return dataset


@router.get("", response_model=list[DatasetOut], summary="List datasets")
def list_datasets(skip: int = 0, limit: int = 50, db: Session = Depends(get_db),
                  _: User = Depends(require_viewer)):
    return db.query(Dataset).order_by(Dataset.id.desc()).offset(skip).limit(limit).all()


@router.get("/{dataset_id}", response_model=DatasetOut, summary="Get dataset metadata")
def get_dataset(dataset_id: int, db: Session = Depends(get_db),
                _: User = Depends(require_viewer)):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/preview", response_model=DatasetPreview,
            summary="Preview the first N rows")
def preview(dataset_id: int, rows: int = 20, db: Session = Depends(get_db),
            _: User = Depends(require_viewer)):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = load_dataframe(dataset.file_path, nrows=rows)
    df = df.where(df.notna(), None)
    return DatasetPreview(dataset_id=dataset_id,
                          columns=[str(c) for c in df.columns],
                          rows=df.head(rows).to_dict(orient="records"))


@router.get("/{dataset_id}/schema", summary="Column schema and inferred semantic types")
def schema(dataset_id: int, db: Session = Depends(get_db),
           _: User = Depends(require_viewer)):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"dataset_id": dataset_id, "n_rows": dataset.n_rows,
            "n_cols": dataset.n_cols, "columns": dataset.columns_meta}


@router.delete("/{dataset_id}", status_code=204, summary="Delete a dataset (admin only)")
def delete_dataset(dataset_id: int, db: Session = Depends(get_db),
                   _: User = Depends(require_admin)):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    Path(dataset.file_path).unlink(missing_ok=True)
    db.delete(dataset)
    db.commit()