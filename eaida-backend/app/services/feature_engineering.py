"""Automated feature engineering: suggestions + transformation pipeline."""
import numpy as np
import pandas as pd


def suggest_features(df: pd.DataFrame, target_column: str | None = None) -> list[dict]:
    suggestions: list[dict] = []
    for col in df.columns:
        if col == target_column:
            continue
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            if abs(float(s.skew(skipna=True) or 0)) > 1.0 and (s.dropna() >= 0).all():
                suggestions.append({"column": str(col), "action": "log_transform",
                                    "reason": "highly skewed non-negative numeric column"})
            if s.isna().mean() > 0:
                suggestions.append({"column": str(col), "action": "impute_median",
                                    "reason": "missing numeric values"})
        elif pd.api.types.is_datetime64_any_dtype(s) or _looks_like_date(s):
            suggestions.append({"column": str(col), "action": "extract_date_parts",
                                "reason": "date column -> year/month/day/dayofweek"})
        else:
            nun = s.nunique(dropna=True)
            if nun <= 15:
                suggestions.append({"column": str(col), "action": "one_hot_encode",
                                    "reason": f"low cardinality ({nun})"})
            elif nun <= 100:
                suggestions.append({"column": str(col), "action": "frequency_encode",
                                    "reason": f"medium cardinality ({nun})"})
            else:
                suggestions.append({"column": str(col), "action": "drop_column",
                                    "reason": f"very high cardinality ({nun})"})
    return suggestions


def _looks_like_date(s: pd.Series) -> bool:
    if s.dtype != object:
        return False
    sample = s.dropna().astype(str).head(50)
    if sample.empty:
        return False
    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    return parsed.notna().mean() > 0.8


def apply_feature_engineering(df: pd.DataFrame, target_column: str | None = None,
                              drop_high_cardinality: bool = True,
                              create_date_parts: bool = True,
                              create_interactions: bool = False) -> tuple[pd.DataFrame, list[str]]:
    out = df.copy()
    applied: list[str] = []

    for col in list(out.columns):
        if col == target_column:
            continue
        s = out[col]

        if create_date_parts and (pd.api.types.is_datetime64_any_dtype(s) or _looks_like_date(s)):
            dt = pd.to_datetime(s, errors="coerce", format="mixed")
            out[f"{col}_year"] = dt.dt.year
            out[f"{col}_month"] = dt.dt.month
            out[f"{col}_day"] = dt.dt.day
            out[f"{col}_dayofweek"] = dt.dt.dayofweek
            out.drop(columns=[col], inplace=True)
            applied.append(f"{col}: extracted date parts")
            continue

        if pd.api.types.is_numeric_dtype(s):
            if s.isna().any():
                out[col] = s.fillna(s.median())
                applied.append(f"{col}: median imputation")
            if abs(float(out[col].skew(skipna=True) or 0)) > 1.0 and (out[col] >= 0).all():
                out[f"{col}_log"] = np.log1p(out[col])
                applied.append(f"{col}: log1p feature added")
        else:
            nun = s.nunique(dropna=True)
            if nun > 100 and drop_high_cardinality:
                out.drop(columns=[col], inplace=True)
                applied.append(f"{col}: dropped (high cardinality)")
            elif nun > 15:
                freq = s.value_counts(normalize=True)
                out[f"{col}_freq"] = s.map(freq).fillna(0)
                out.drop(columns=[col], inplace=True)
                applied.append(f"{col}: frequency encoded")
            else:
                out[col] = s.fillna("missing").astype(str)
                applied.append(f"{col}: kept as categorical (one-hot at training time)")

    if create_interactions:
        num_cols = out.select_dtypes(include=[np.number]).columns.tolist()
        num_cols = [c for c in num_cols if c != target_column][:4]
        for i in range(len(num_cols)):
            for j in range(i + 1, len(num_cols)):
                a, b = num_cols[i], num_cols[j]
                out[f"{a}_x_{b}"] = out[a] * out[b]
                applied.append(f"{a} x {b}: interaction feature")

    return out, applied