"""Loading uploaded tabular files into pandas + extracting column metadata."""
from pathlib import Path

import pandas as pd


def load_dataframe(file_path: str, nrows: int | None = None) -> pd.DataFrame:
    suffix = Path(file_path).suffix.lower()
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(file_path, nrows=nrows)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(file_path, nrows=nrows)
    if suffix == ".json":
        return pd.read_json(file_path)
    if suffix == ".parquet":
        return pd.read_parquet(file_path)
    raise ValueError(f"Unsupported file type: {suffix}")


def infer_column_meta(df: pd.DataFrame) -> dict:
    meta: dict = {}
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            kind = "numeric"
        elif pd.api.types.is_datetime64_any_dtype(s):
            kind = "datetime"
        elif s.nunique(dropna=True) <= max(20, int(0.05 * len(s))):
            kind = "categorical"
        else:
            kind = "text"
        meta[str(col)] = {
            "dtype": str(s.dtype),
            "semantic_type": kind,
            "missing_pct": round(float(s.isna().mean() * 100), 2),
            "unique": int(s.nunique(dropna=True)),
        }
    return meta