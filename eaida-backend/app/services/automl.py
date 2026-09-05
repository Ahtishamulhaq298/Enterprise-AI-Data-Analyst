"""AutoML engine: task detection, preprocessing pipeline, multi-model training + comparison."""
from __future__ import annotations

import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (GradientBoostingClassifier, GradientBoostingRegressor,
                              RandomForestClassifier, RandomForestRegressor)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import (accuracy_score, f1_score, mean_absolute_error,
                             mean_squared_error, precision_score, r2_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from app.core.config import settings


def detect_task_type(y: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(y) and y.nunique(dropna=True) > 20:
        return "regression"
    return "classification"


def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    num_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = [c for c in X.columns if c not in num_cols]
    numeric_pipe = Pipeline([("imputer", SimpleImputer(strategy="median")),
                             ("scaler", StandardScaler())])
    cat_pipe = Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                         ("ohe", OneHotEncoder(handle_unknown="ignore", max_categories=25))])
    return ColumnTransformer([("num", numeric_pipe, num_cols),
                              ("cat", cat_pipe, cat_cols)], remainder="drop")


def candidate_models(task: str, random_state: int = 42) -> dict:
    if task == "classification":
        models = {
            "LogisticRegression": LogisticRegression(max_iter=1000),
            "DecisionTree": DecisionTreeClassifier(random_state=random_state),
            "RandomForest": RandomForestClassifier(n_estimators=200, random_state=random_state),
            "GradientBoosting": GradientBoostingClassifier(random_state=random_state),
        }
        try:
            from xgboost import XGBClassifier
            models["XGBoost"] = XGBClassifier(
                n_estimators=250, learning_rate=0.1, max_depth=6,
                eval_metric="logloss", random_state=random_state)
        except Exception:
            pass
        try:
            from lightgbm import LGBMClassifier
            models["LightGBM"] = LGBMClassifier(random_state=random_state, verbose=-1)
        except Exception:
            pass
        return models

    models = {
        "LinearRegression": LinearRegression(),
        "Ridge": Ridge(),
        "DecisionTree": DecisionTreeRegressor(random_state=random_state),
        "RandomForest": RandomForestRegressor(n_estimators=200, random_state=random_state),
        "GradientBoosting": GradientBoostingRegressor(random_state=random_state),
    }
    try:
        from xgboost import XGBRegressor
        models["XGBoost"] = XGBRegressor(n_estimators=250, learning_rate=0.1,
                                         max_depth=6, random_state=random_state)
    except Exception:
        pass
    try:
        from lightgbm import LGBMRegressor
        models["LightGBM"] = LGBMRegressor(random_state=random_state, verbose=-1)
    except Exception:
        pass
    return models


def _classification_metrics(y_true, y_pred, y_proba=None) -> dict:
    avg = "binary" if len(np.unique(y_true)) == 2 else "macro"
    out = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, average=avg, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, average=avg, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, average=avg, zero_division=0)), 4),
    }
    if y_proba is not None and len(np.unique(y_true)) == 2:
        try:
            out["roc_auc"] = round(float(roc_auc_score(y_true, y_proba[:, 1])), 4)
        except Exception:
            pass
    return out


def _regression_metrics(y_true, y_pred) -> dict:
    mse = float(mean_squared_error(y_true, y_pred))
    return {
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "mse": round(mse, 4),
        "rmse": round(float(np.sqrt(mse)), 4),
    }


def run_automl(df: pd.DataFrame, target_column: str, task_type: str = "auto",
               test_size: float = 0.2, cv_folds: int = 3, max_models: int = 6,
               random_state: int = 42, job_id: int | None = None) -> dict:
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found in dataset")

    df = df.dropna(subset=[target_column])
    X = df.drop(columns=[target_column])
    y = df[target_column]

    task = detect_task_type(y) if task_type == "auto" else task_type
    if task == "classification" and y.dtype == object:
        y = y.astype("category").cat.codes

    stratify = y if (task == "classification" and y.value_counts().min() >= 2) else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify)

    preprocessor = build_preprocessor(X)
    models = candidate_models(task, random_state)
    leaderboard: list[dict] = []
    fitted: dict[str, Pipeline] = {}

    for name, estimator in list(models.items())[:max_models]:
        pipe = Pipeline([("prep", preprocessor), ("model", estimator)])
        started = time.perf_counter()
        try:
            pipe.fit(X_train, y_train)
            y_pred = pipe.predict(X_test)
            proba = pipe.predict_proba(X_test) if hasattr(pipe, "predict_proba") else None
            metrics = (_classification_metrics(y_test, y_pred, proba) if task == "classification"
                       else _regression_metrics(y_test, y_pred))
            scoring = "f1_weighted" if task == "classification" else "r2"
            cv = cross_val_score(pipe, X_train, y_train, cv=cv_folds,
                                 scoring=scoring, n_jobs=-1)
            leaderboard.append({
                "model": name,
                "metrics": metrics,
                "cv_mean": round(float(cv.mean()), 4),
                "cv_std": round(float(cv.std()), 4),
                "train_seconds": round(time.perf_counter() - started, 2),
                "status": "success",
            })
            fitted[name] = pipe
        except Exception as exc:  # keep the leaderboard going if one model fails
            leaderboard.append({"model": name, "status": "failed", "error": str(exc)})

    primary = "f1" if task == "classification" else "r2"
    ranked = sorted([r for r in leaderboard if r["status"] == "success"],
                    key=lambda r: r["metrics"].get(primary, -1e9), reverse=True)
    if not ranked:
        raise RuntimeError("All candidate models failed to train")

    best_name = ranked[0]["model"]
    best_pipe = fitted[best_name]

    Path(settings.MODEL_DIR).mkdir(parents=True, exist_ok=True)
    artifact = str(Path(settings.MODEL_DIR) / f"model_job_{job_id or int(time.time())}.joblib")
    joblib.dump({"pipeline": best_pipe, "task": task, "target": target_column,
                 "feature_columns": X.columns.tolist()}, artifact)

    return {
        "task_type": task,
        "target_column": target_column,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "feature_columns": X.columns.tolist(),
        "leaderboard": ranked + [r for r in leaderboard if r["status"] == "failed"],
        "best_model": {"name": best_name, **ranked[0]},
        "artifact_path": artifact,
    }


def predict_with_model(artifact_path: str, records: list[dict]) -> dict:
    bundle = joblib.load(artifact_path)
    pipe, cols = bundle["pipeline"], bundle["feature_columns"]
    frame = pd.DataFrame(records).reindex(columns=cols)
    preds = pipe.predict(frame)
    out = {"predictions": [float(p) if isinstance(p, (np.floating, float)) else int(p)
                           for p in preds]}
    if hasattr(pipe, "predict_proba"):
        out["probabilities"] = pipe.predict_proba(frame).round(4).tolist()
    return out