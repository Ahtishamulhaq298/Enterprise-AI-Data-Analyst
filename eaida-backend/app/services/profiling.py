"""Data profiling: shape, types, missing values, stats, correlations, quality issues."""
import numpy as np
import pandas as pd


def _json_safe(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def profile_dataframe(df: pd.DataFrame) -> dict:
    n_rows, n_cols = df.shape
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = [c for c in df.columns if c not in numeric_cols]

    columns = []
    for col in df.columns:
        s = df[col]
        entry = {
            "name": str(col),
            "dtype": str(s.dtype),
            "missing": int(s.isna().sum()),
            "missing_pct": round(float(s.isna().mean() * 100), 2),
            "unique": int(s.nunique(dropna=True)),
        }
        if col in numeric_cols:
            desc = s.describe()
            entry.update({
                "mean": _json_safe(desc.get("mean")),
                "std": _json_safe(desc.get("std")),
                "min": _json_safe(desc.get("min")),
                "q25": _json_safe(desc.get("25%")),
                "median": _json_safe(desc.get("50%")),
                "q75": _json_safe(desc.get("75%")),
                "max": _json_safe(desc.get("max")),
                "skew": _json_safe(s.skew()),
                "outliers_iqr": int(_count_iqr_outliers(s)),
            })
        else:
            top = s.value_counts(dropna=True).head(5)
            entry["top_values"] = {str(k): int(v) for k, v in top.items()}
        columns.append(entry)

    corr = {}
    if len(numeric_cols) >= 2:
        cm = df[numeric_cols].corr(numeric_only=True).round(3)
        corr = {str(c): {str(k): _json_safe(v) for k, v in cm[c].items()} for c in cm.columns}

    return {
        "shape": {"rows": int(n_rows), "columns": int(n_cols)},
        "duplicate_rows": int(df.duplicated().sum()),
        "memory_mb": round(float(df.memory_usage(deep=True).sum() / 1024 ** 2), 3),
        "numeric_columns": [str(c) for c in numeric_cols],
        "categorical_columns": [str(c) for c in cat_cols],
        "columns": columns,
        "correlations": corr,
        "quality_issues": detect_quality_issues(df),
    }


def _count_iqr_outliers(s: pd.Series) -> int:
    s = s.dropna()
    if s.empty:
        return 0
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    return int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())


def detect_quality_issues(df: pd.DataFrame) -> list[dict]:
    issues: list[dict] = []
    for col in df.columns:
        s = df[col]
        miss = float(s.isna().mean())
        if miss > 0.4:
            issues.append({"column": str(col), "issue": "high_missing",
                           "severity": "high", "detail": f"{miss:.1%} missing"})
        elif miss > 0.1:
            issues.append({"column": str(col), "issue": "missing_values",
                           "severity": "medium", "detail": f"{miss:.1%} missing"})
        if s.nunique(dropna=True) <= 1:
            issues.append({"column": str(col), "issue": "constant_column",
                           "severity": "high", "detail": "single unique value"})
        if s.dtype == object and s.nunique(dropna=True) > 0.9 * max(len(s), 1):
            issues.append({"column": str(col), "issue": "high_cardinality",
                           "severity": "medium", "detail": "almost unique text column"})
    if df.duplicated().sum() > 0:
        issues.append({"column": "*", "issue": "duplicate_rows", "severity": "medium",
                       "detail": f"{int(df.duplicated().sum())} duplicated rows"})
    return issues