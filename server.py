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

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
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

# Allow HF Spaces iframe embedding and CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_frame_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "ALLOWALL"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

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
def reset_env(request: ResetRequest):
    """Reset the environment with a task."""
    try:
        obs = env.reset(task_id=request.task_id)
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
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EcoCode Dashboard</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px auto; max-width: 800px; line-height: 1.6; color: #333; }
            h1 { color: #2e7d32; }
            .card { border: 1px solid #ddd; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f5f5f5; }
            .eco { color: #2e7d32; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🌱 EcoCode Dashboard</h1>
        <div class="card">
            <p><strong>Status:</strong> Online</p>
            <p>An OpenEnv-compatible interactive environment where AI agents iteratively refactor Python code to improve efficiency (Time & Memory) and reduce Carbon Footprint (gCO₂eq).</p>
            <h3>API Endpoints:</h3>
            <ul>
                <li><code>POST /reset</code></li>
                <li><code>POST /step</code></li>
                <li><code>GET /state</code></li>
                <li><code>GET /tasks</code></li>
                <li><code>POST /grader</code></li>
                <li><code>POST /baseline</code></li>
            </ul>
        </div>
    """
    
    if os.path.exists("baseline_results.json"):
        try:
            with open("baseline_results.json", "r") as f:
                data = json.load(f)
            
            html_content += "<h2>Latest Baseline Results</h2><table><tr><th>Task</th><th>Difficulty</th><th>Score</th><th class='eco'>Reward</th></tr>"
            for tid, tdata in data.get("tasks", {}).items():
                score = round(tdata.get('final_score', 0), 3)
                reward = round(tdata.get('reward', 0), 3)
                html_content += f"<tr><td>{tid}</td><td>{tdata.get('difficulty')}</td><td>{score}</td><td class='eco'>{reward}</td></tr>"
            html_content += "</table>"
            
            avg = data.get('average_score', 0)
            html_content += f"<p><strong>Average Score:</strong> {avg}</p>"
        except Exception:
            pass
            
    html_content += "</body></html>"
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
