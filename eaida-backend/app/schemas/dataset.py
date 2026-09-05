from datetime import datetime

from pydantic import BaseModel


class DatasetOut(BaseModel):
    id: int
    name: str
    description: str
    file_type: str
    n_rows: int
    n_cols: int
    columns_meta: dict
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DatasetPreview(BaseModel):
    dataset_id: int
    columns: list[str]
    rows: list[dict]