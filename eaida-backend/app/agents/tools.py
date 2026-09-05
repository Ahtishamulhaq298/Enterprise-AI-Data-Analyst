"""Function-calling tools the agents can invoke."""
from __future__ import annotations

import pandas as pd

from app.rag.pipeline import answer_question
from app.services.automl import run_automl
from app.services.feature_engineering import suggest_features
from app.services.ingestion import load_dataframe
from app.services.profiling import profile_dataframe


def tool_profile_dataset(file_path: str) -> dict:
    """Profile a dataset file and return summary statistics + quality issues."""
    return profile_dataframe(load_dataframe(file_path))


def tool_suggest_features(file_path: str, target_column: str | None = None) -> list[dict]:
    """Suggest feature-engineering actions for a dataset."""
    return suggest_features(load_dataframe(file_path), target_column)


def tool_train_models(file_path: str, target_column: str) -> dict:
    """Train and compare candidate models on the dataset."""
    return run_automl(load_dataframe(file_path), target_column, max_models=4, cv_folds=3)


def tool_search_knowledge_base(question: str) -> dict:
    """Search the enterprise knowledge base with hybrid RAG."""
    return answer_question(question, top_k=5)


def tool_column_statistics(file_path: str, column: str) -> dict:
    """Return descriptive statistics for one column."""
    df: pd.DataFrame = load_dataframe(file_path)
    if column not in df.columns:
        return {"error": f"column '{column}' not found"}
    s = df[column]
    if pd.api.types.is_numeric_dtype(s):
        return {"column": column, "stats": s.describe().round(4).to_dict()}
    return {"column": column,
            "top_values": {str(k): int(v) for k, v in s.value_counts().head(10).items()}}


TOOL_REGISTRY = {
    "profile_dataset": tool_profile_dataset,
    "suggest_features": tool_suggest_features,
    "train_models": tool_train_models,
    "search_knowledge_base": tool_search_knowledge_base,
    "column_statistics": tool_column_statistics,
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "profile_dataset", "description": tool_profile_dataset.__doc__,
        "parameters": {"type": "object", "properties": {"file_path": {"type": "string"}},
                       "required": ["file_path"]}}},
    {"type": "function", "function": {
        "name": "suggest_features", "description": tool_suggest_features.__doc__,
        "parameters": {"type": "object", "properties": {
            "file_path": {"type": "string"}, "target_column": {"type": "string"}},
            "required": ["file_path"]}}},
    {"type": "function", "function": {
        "name": "train_models", "description": tool_train_models.__doc__,
        "parameters": {"type": "object", "properties": {
            "file_path": {"type": "string"}, "target_column": {"type": "string"}},
            "required": ["file_path", "target_column"]}}},
    {"type": "function", "function": {
        "name": "search_knowledge_base", "description": tool_search_knowledge_base.__doc__,
        "parameters": {"type": "object", "properties": {"question": {"type": "string"}},
                       "required": ["question"]}}},
    {"type": "function", "function": {
        "name": "column_statistics", "description": tool_column_statistics.__doc__,
        "parameters": {"type": "object", "properties": {
            "file_path": {"type": "string"}, "column": {"type": "string"}},
            "required": ["file_path", "column"]}}},
]