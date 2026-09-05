"""Multi-agent analysis workflow (LangGraph).

Agents:
  1. PlannerAgent   - decides which analysis steps are needed
  2. ProfilerAgent  - profiles the dataset and lists quality issues
  3. ModelerAgent   - runs AutoML when a target column is available
  4. InsightAgent   - retrieves knowledge-base context and writes the final answer

Falls back to a plain sequential runner if langgraph is not installed.
"""
from __future__ import annotations

from typing import Any, TypedDict

from loguru import logger

from app.rag.pipeline import answer_question
from app.services.automl import run_automl
from app.services.ingestion import load_dataframe
from app.services.llm import chat
from app.services.profiling import profile_dataframe


class AnalysisState(TypedDict, total=False):
    file_path: str
    dataset_id: int
    question: str
    target_column: str | None
    plan: list[str]
    profiling: dict
    modeling: dict
    kb_context: dict
    steps: list[dict[str, Any]]
    final_answer: str


def planner_agent(state: AnalysisState) -> AnalysisState:
    plan = ["profile"]
    if state.get("target_column"):
        plan.append("model")
    plan.append("insight")
    state["plan"] = plan
    state.setdefault("steps", []).append({"agent": "planner", "output": {"plan": plan}})
    return state


def profiler_agent(state: AnalysisState) -> AnalysisState:
    df = load_dataframe(state["file_path"])
    profile = profile_dataframe(df)
    state["profiling"] = profile
    state.setdefault("steps", []).append({
        "agent": "profiler",
        "output": {"shape": profile["shape"],
                   "issues": profile["quality_issues"][:5]}})
    return state


def modeler_agent(state: AnalysisState) -> AnalysisState:
    target = state.get("target_column")
    if not target:
        state.setdefault("steps", []).append(
            {"agent": "modeler", "output": {"skipped": "no target column supplied"}})
        return state
    try:
        df = load_dataframe(state["file_path"])
        result = run_automl(df, target, max_models=4, cv_folds=3)
        state["modeling"] = result
        state.setdefault("steps", []).append({
            "agent": "modeler",
            "output": {"best_model": result["best_model"]["name"],
                       "metrics": result["best_model"]["metrics"]}})
    except Exception as exc:
        logger.error(f"modeler_agent failed: {exc}")
        state.setdefault("steps", []).append({"agent": "modeler", "output": {"error": str(exc)}})
    return state


def insight_agent(state: AnalysisState) -> AnalysisState:
    kb = answer_question(state["question"], top_k=4)
    state["kb_context"] = kb

    profiling = state.get("profiling", {})
    modeling = state.get("modeling", {})
    prompt = f"""You are the lead data analyst. Write a clear, business-facing answer.

USER QUESTION: {state['question']}

DATASET PROFILE (summary):
- shape: {profiling.get('shape')}
- quality issues: {profiling.get('quality_issues', [])[:8]}
- numeric columns: {profiling.get('numeric_columns', [])[:15]}

MODELING RESULT:
{ {'best_model': modeling.get('best_model', {}).get('name'),
   'metrics': modeling.get('best_model', {}).get('metrics'),
   'task': modeling.get('task_type')} if modeling else 'no model trained'}

KNOWLEDGE BASE CONTEXT:
{kb.get('answer', '')[:1500]}

Produce: 1) direct answer, 2) key findings with numbers, 3) data quality warnings,
4) recommended next actions."""
    state["final_answer"] = chat(prompt)
    state.setdefault("steps", []).append({
        "agent": "insight",
        "output": {"citations": len(kb.get("citations", []))}})
    return state


def _build_graph():
    from langgraph.graph import END, StateGraph

    graph = StateGraph(AnalysisState)
    graph.add_node("planner", planner_agent)
    graph.add_node("profiler", profiler_agent)
    graph.add_node("modeler", modeler_agent)
    graph.add_node("insight", insight_agent)
    graph.set_entry_point("planner")
    graph.add_edge("planner", "profiler")
    graph.add_edge("profiler", "modeler")
    graph.add_edge("modeler", "insight")
    graph.add_edge("insight", END)
    return graph.compile()


def run_analysis_workflow(file_path: str, dataset_id: int, question: str,
                          target_column: str | None = None) -> AnalysisState:
    state: AnalysisState = {"file_path": file_path, "dataset_id": dataset_id,
                            "question": question, "target_column": target_column,
                            "steps": []}
    try:
        app_graph = _build_graph()
        return app_graph.invoke(state)
    except Exception as exc:
        logger.warning(f"LangGraph unavailable ({exc}); running sequential fallback")
        for node in (planner_agent, profiler_agent, modeler_agent, insight_agent):
            state = node(state)
        return state