"""API v1 aggregate router - registers every controller."""
from fastapi import APIRouter

from app.api.v1.endpoints import (agents, auth, automl, datasets, evaluation,
                                  explain, features, health, profiling, rag, reports)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth & RBAC"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])
api_router.include_router(profiling.router, prefix="/profiling", tags=["Data Profiling"])
api_router.include_router(features.router, prefix="/features", tags=["Feature Engineering"])
api_router.include_router(automl.router, prefix="/automl", tags=["AutoML & Model Comparison"])
api_router.include_router(explain.router, prefix="/explain", tags=["Explainability"])
api_router.include_router(rag.router, prefix="/rag", tags=["Knowledge Base & RAG"])
api_router.include_router(agents.router, prefix="/agents", tags=["Multi-Agent Workflows"])
api_router.include_router(reports.router, prefix="/reports", tags=["Automated Reporting"])
api_router.include_router(evaluation.router, prefix="/evaluation", tags=["Evaluation"])