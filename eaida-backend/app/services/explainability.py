"""Model explainability: SHAP when available, permutation importance as fallback."""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance


def _feature_names(pipeline) -> list[str]:
    try:
        return list(pipeline.named_steps["prep"].get_feature_names_out())
    except Exception:
        return []


def global_explanation(artifact_path: str, X: pd.DataFrame, y=None,
                       top_k: int = 15) -> dict:
    bundle = joblib.load(artifact_path)
    pipe, cols = bundle["pipeline"], bundle["feature_columns"]
    X = X.reindex(columns=cols)
    sample = X.sample(min(len(X), 500), random_state=42)

    # 1) Try SHAP on tree-based models (fast + exact)
    try:
        import shap
        model = pipe.named_steps["model"]
        prep = pipe.named_steps["prep"]
        transformed = prep.transform(sample)
        if hasattr(transformed, "toarray"):
            transformed = transformed.toarray()
        explainer = shap.Explainer(model, transformed)
        values = explainer(transformed[:200])
        arr = np.abs(values.values)
        if arr.ndim == 3:
            arr = arr.mean(axis=2)
        importance = arr.mean(axis=0)
        names = _feature_names(pipe) or [f"f{i}" for i in range(len(importance))]
        pairs = sorted(zip(names, importance), key=lambda t: t[1], reverse=True)[:top_k]
        return {"method": "shap",
                "features": [{"feature": str(n), "importance": round(float(v), 6)}
                             for n, v in pairs]}
    except Exception:
        pass

    # 2) Fallback: permutation importance on raw columns
    if y is None:
        model = pipe.named_steps["model"]
        if hasattr(model, "feature_importances_"):
            names = _feature_names(pipe) or cols
            imp = model.feature_importances_
            pairs = sorted(zip(names, imp), key=lambda t: t[1], reverse=True)[:top_k]
            return {"method": "tree_feature_importance",
                    "features": [{"feature": str(n), "importance": round(float(v), 6)}
                                 for n, v in pairs]}
        return {"method": "unavailable", "features": []}

    y_sample = pd.Series(y).loc[sample.index]
    result = permutation_importance(pipe, sample, y_sample, n_repeats=5,
                                    random_state=42, n_jobs=-1)
    pairs = sorted(zip(cols, result.importances_mean), key=lambda t: t[1], reverse=True)[:top_k]
    return {"method": "permutation_importance",
            "features": [{"feature": str(n), "importance": round(float(v), 6)}
                         for n, v in pairs]}


def local_explanation(artifact_path: str, X: pd.DataFrame, row_index: int,
                      top_k: int = 15) -> dict:
    bundle = joblib.load(artifact_path)
    pipe, cols = bundle["pipeline"], bundle["feature_columns"]
    X = X.reindex(columns=cols)
    if row_index >= len(X):
        raise ValueError(f"row_index {row_index} is out of range ({len(X)} rows)")
    row = X.iloc[[row_index]]
    prediction = pipe.predict(row)[0]

    try:
        import shap
        prep, model = pipe.named_steps["prep"], pipe.named_steps["model"]
        background = prep.transform(X.sample(min(len(X), 100), random_state=42))
        transformed = prep.transform(row)
        if hasattr(background, "toarray"):
            background = background.toarray()
        if hasattr(transformed, "toarray"):
            transformed = transformed.toarray()
        explainer = shap.Explainer(model, background)
        values = explainer(transformed)
        arr = values.values[0]
        if arr.ndim == 2:
            arr = arr.mean(axis=1)
        names = _feature_names(pipe) or [f"f{i}" for i in range(len(arr))]
        pairs = sorted(zip(names, arr), key=lambda t: abs(t[1]), reverse=True)[:top_k]
        contributions = [{"feature": str(n), "contribution": round(float(v), 6)}
                         for n, v in pairs]
        method = "shap"
    except Exception:
        contributions, method = [], "unavailable"

    return {
        "method": method,
        "row_index": row_index,
        "prediction": float(prediction) if isinstance(prediction, (float, np.floating))
        else int(prediction),
        "input": {k: (None if pd.isna(v) else v) for k, v in row.iloc[0].to_dict().items()},
        "contributions": contributions,
    }