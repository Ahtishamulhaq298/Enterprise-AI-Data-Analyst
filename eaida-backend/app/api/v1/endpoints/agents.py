"""Multi-agent workflow controller."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.graph import run_analysis_workflow
from app.agents.tools import TOOL_REGISTRY, TOOL_SCHEMAS
from app.core.deps import require_analyst, require_viewer
from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.job import Job, JobStatus, JobType
from app.models.user import User
from app.schemas.rag import AgentRequest, AgentResponse

router = APIRouter()


@router.get("/tools", summary="List the tools available to the agents (function calling)")
def list_tools(_: User = Depends(require_viewer)):
    return {"count": len(TOOL_SCHEMAS), "tools": TOOL_SCHEMAS}


@router.post("/tools/{tool_name}", summary="Invoke a single tool directly")
def invoke_tool(tool_name: str, arguments: dict, _: User = Depends(require_analyst)):
    if tool_name not in TOOL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown tool '{tool_name}'")
    try:
        return {"tool": tool_name, "result": TOOL_REGISTRY[tool_name](**arguments)}
    except TypeError as exc:
        raise HTTPException(status_code=422, detail=f"Bad arguments: {exc}")


@router.post("/analyze", response_model=AgentResponse,
             summary="Run the full planner -> profiler -> modeler -> insight workflow")
def analyze(payload: AgentRequest, db: Session = Depends(get_db),
            user: User = Depends(require_analyst)):
    dataset = db.get(Dataset, payload.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    job = Job(job_type=JobType.AGENT, status=JobStatus.RUNNING, dataset_id=dataset.id,
              user_id=user.id, params=payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        state = run_analysis_workflow(dataset.file_path, dataset.id,
                                      payload.question, payload.target_column)
        response = AgentResponse(dataset_id=dataset.id, question=payload.question,
                                 steps=state.get("steps", []),
                                 final_answer=state.get("final_answer", ""))
        job.result = response.model_dump()
        job.status = JobStatus.SUCCESS
    except Exception as exc:
        job.status, job.error = JobStatus.FAILED, str(exc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Agent workflow failed: {exc}")
    finally:
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    return response