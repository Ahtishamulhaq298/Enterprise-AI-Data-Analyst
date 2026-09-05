"""Feature-engineering controller: suggestions + apply transformations."""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_analyst, require_viewer
from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.user import User
from app.schemas.analysis import FeatureEngineeringRequest
from app.services.feature_engineering import apply_feature_engineering, suggest_features
from app.services.ingestion import infer_column_meta, load_dataframe

router = APIRouter()


@router.get("/suggest/{dataset_id}", summary="Suggest feature-engineering actions")
def suggest(dataset_id: int, target_column: str | None = None,
            db: Session = Depends(get_db), _: User = Depends(require_viewer)):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = load_dataframe(dataset.file_path)
    return {"dataset_id": dataset_id, "target_column": target_column,
            "suggestions": suggest_features(df, target_column)}


@router.post("/apply", summary="Apply feature engineering and (optionally) save a new dataset")
def apply(payload: FeatureEngineeringRequest, db: Session = Depends(get_db),
          user: User = Depends(require_analyst)):
    dataset = db.get(Dataset, payload.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    df = load_dataframe(dataset.file_path)
    transformed, applied = apply_feature_engineering(
        df, payload.target_column, payload.drop_high_cardinality,
        payload.create_date_parts, payload.create_interactions)

    response = {"source_dataset_id": dataset.id,
                "applied_transformations": applied,
                "new_shape": {"rows": int(transformed.shape[0]),
                              "columns": int(transformed.shape[1])},
                "new_columns": [str(c) for c in transformed.columns]}

    if payload.save_as_new_dataset:
        path = Path(settings.UPLOAD_DIR) / f"{uuid.uuid4().hex}.csv"
        transformed.to_csv(path, index=False)
        new_ds = Dataset(name=f"{dataset.name} (engineered)",
                         description=f"Derived from dataset {dataset.id}",
                         file_path=str(path), file_type="csv",
                         n_rows=int(transformed.shape[0]), n_cols=int(transformed.shape[1]),
                         columns_meta=infer_column_meta(transformed), owner_id=user.id)
        db.add(new_ds)
        db.commit()
        db.refresh(new_ds)
        response["new_dataset_id"] = new_ds.id
    return response