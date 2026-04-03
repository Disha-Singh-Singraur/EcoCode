"""FastAPI server for the EcoCode environment.

Endpoints:
  POST /reset       → initial Observation
  POST /step        → Observation, Reward, done, info
  GET  /state       → current EnvironmentState
  GET  /tasks       → list of TaskInfo
  POST /grader      → GraderResult with full breakdown
  POST /baseline    → run baseline evaluation
"""

from typing import Any, Dict, List, Optional
import os
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from env.environment import EcoCodeEnv
from grader.grader import Grader
from models.schemas import (
    Action,
    GraderResult,
    Observation,
    Reward,
    TaskInfo,
    TestCase,
)
from tasks.definitions import TASKS, list_task_ids

app = FastAPI(
    title="EcoCode: Green Code Optimization Environment",
    description="OpenEnv-compatible environment for AI-driven code optimization",
    version="1.0.0",
)

# Global environment instance
env = EcoCodeEnv()
grader = Grader()


# ── Request / Response Models ──────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: Optional[str] = None


class StepRequest(BaseModel):
    rewritten_code: str


class GraderRequest(BaseModel):
    task_id: str
    rewritten_code: str


class StepResponse(BaseModel):
    observation: Observation
    reward: Reward
    done: bool
    info: Dict[str, Any]


class BaselineResponse(BaseModel):
    status: str
    message: str


# ── Endpoints ──────────────────────────────────────────────────────────

@app.post("/reset", response_model=Observation)
def reset_env(request: Optional[ResetRequest] = None):
    """Reset the environment with a task."""
    try:
        task_id = request.task_id if request else None
        obs = env.reset(task_id=task_id)
        return obs
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/step", response_model=StepResponse)
def step_env(request: StepRequest):
    """Apply an action and return the result."""
    try:
        action = Action(rewritten_code=request.rewritten_code)
        obs, reward, done, info = env.step(action)
        # Serialize GraderResult if present
        if "grader_result" in info:
            info["grader_result"] = info["grader_result"]
        return StepResponse(
            observation=obs,
            reward=reward,
            done=done,
            info=info,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/state")
def get_state():
    """Get the current environment state."""
    return env.state().model_dump()


@app.get("/tasks", response_model=List[TaskInfo])
def get_tasks():
    """Return metadata for all available tasks."""
    task_list = []
    for task_id in list_task_ids():
        task = TASKS[task_id]
        # Build a sample observation
        sample_obs = Observation(
            current_code=task["dirty_code"],
            original_code=task["dirty_code"],
            test_cases=[
                TestCase(input=tc["input"], expected_output=tc["expected_output"])
                for tc in task["test_cases"]
            ],
            difficulty=task["difficulty"],
            step_count=0,
        )
        task_list.append(
            TaskInfo(
                id=task["id"],
                description=task["description"],
                difficulty=task["difficulty"],
                sample_observation=sample_obs,
            )
        )
    return task_list


@app.post("/grader", response_model=GraderResult)
def grade_submission(request: GraderRequest):
    """Grade a code submission for a specific task."""
    if request.task_id not in TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task: {request.task_id}. "
                   f"Available: {list_task_ids()}",
        )
    task = TASKS[request.task_id]
    result = grader.grade(
        original_code=task["dirty_code"],
        rewritten_code=request.rewritten_code,
        test_cases=task["test_cases"],
    )
    return result


@app.post("/baseline")
def run_baseline():
    """Run baseline evaluation.

    Uses OpenAI API if OPENAI_API_KEY is set, otherwise falls back
    to deterministic rule-based solutions.
    """
    try:
        from scripts.baseline import run_baseline_evaluation
        results = run_baseline_evaluation()
        return {
            "status": "success",
            "mode": results["mode"],
            "average_score": results["average_score"],
            "success_rate": results["success_rate"],
            "tasks": results["tasks"],
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Baseline failed: {exc}",
        }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def root():
    """Health check / info endpoint with visual dashboard."""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>EcoCode Dashboard</h1><p>index.html not found</p>")


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
