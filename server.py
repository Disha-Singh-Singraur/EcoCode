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
    """Premium EcoCode dashboard."""
    return HTMLResponse(content="""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EcoCode — Green Code Optimization</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:linear-gradient(135deg,#f0fdf4 0%,#dcfce7 30%,#ecfdf5 60%,#f0f9ff 100%);min-height:100vh;color:#1e293b}
.container{max-width:960px;margin:0 auto;padding:40px 24px}

/* Hero */
.hero{text-align:center;margin-bottom:48px;animation:fadeUp .6s ease-out}
.hero-icon{font-size:64px;margin-bottom:12px}
.hero h1{font-size:2.5rem;font-weight:800;background:linear-gradient(135deg,#166534,#15803d,#059669);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}
.hero p{font-size:1.1rem;color:#475569;max-width:600px;margin:0 auto;line-height:1.7}
.badge{display:inline-block;background:#dcfce7;color:#166534;padding:4px 14px;border-radius:20px;font-size:.8rem;font-weight:600;margin-top:12px;border:1px solid #bbf7d0}

/* Stats row */
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:36px;animation:fadeUp .8s ease-out}
.stat-card{background:rgba(255,255,255,.75);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.8);border-radius:16px;padding:24px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.04);transition:transform .2s,box-shadow .2s}
.stat-card:hover{transform:translateY(-4px);box-shadow:0 8px 30px rgba(0,0,0,.08)}
.stat-num{font-size:2rem;font-weight:800;color:#166534}
.stat-label{font-size:.85rem;color:#64748b;margin-top:4px;font-weight:500}

/* Cards */
.card{background:rgba(255,255,255,.7);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.8);border-radius:16px;padding:28px;margin-bottom:24px;box-shadow:0 4px 20px rgba(0,0,0,.04);animation:fadeUp 1s ease-out}
.card h2{font-size:1.3rem;font-weight:700;color:#166534;margin-bottom:16px;display:flex;align-items:center;gap:8px}

/* Table */
table{width:100%;border-collapse:separate;border-spacing:0}
th{background:#f0fdf4;color:#166534;font-weight:600;font-size:.8rem;text-transform:uppercase;letter-spacing:.5px;padding:12px 16px;text-align:left}
th:first-child{border-radius:10px 0 0 10px}
th:last-child{border-radius:0 10px 10px 0}
td{padding:12px 16px;border-bottom:1px solid #f1f5f9;font-size:.9rem}
tr:last-child td{border-bottom:none}
tr:hover td{background:#f0fdf4}
.diff-easy{color:#059669;font-weight:600}
.diff-medium{color:#d97706;font-weight:600}
.diff-hard{color:#dc2626;font-weight:600}

/* Endpoints */
.endpoints{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.ep{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px;display:flex;align-items:center;gap:10px;transition:all .2s}
.ep:hover{background:#f0fdf4;border-color:#bbf7d0;transform:translateX(4px)}
.ep-method{font-size:.7rem;font-weight:700;padding:3px 8px;border-radius:6px;min-width:44px;text-align:center}
.ep-get{background:#dcfce7;color:#166534}
.ep-post{background:#dbeafe;color:#1e40af}
.ep-path{font-family:'SF Mono',Monaco,monospace;font-size:.85rem;color:#334155}

/* Footer */
.footer{text-align:center;margin-top:40px;color:#94a3b8;font-size:.8rem}
.footer a{color:#166534;text-decoration:none}

/* Loading */
#tasks-loading{text-align:center;padding:20px;color:#94a3b8}
.spinner{display:inline-block;width:20px;height:20px;border:2px solid #e2e8f0;border-top-color:#166534;border-radius:50%;animation:spin .6s linear infinite;margin-right:8px;vertical-align:middle}

@keyframes fadeUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
@keyframes spin{to{transform:rotate(360deg)}}
@media(max-width:640px){.stats{grid-template-columns:1fr}.endpoints{grid-template-columns:1fr}.hero h1{font-size:1.8rem}}
</style>
</head>
<body>
<div class="container">
  <div class="hero">
    <div class="hero-icon">🌱</div>
    <h1>EcoCode</h1>
    <p>An OpenEnv-compatible environment where AI agents iteratively refactor Python code to improve efficiency and reduce carbon footprint.</p>
    <span class="badge">✅ Online — OpenEnv v1.0</span>
  </div>

  <div class="stats">
    <div class="stat-card"><div class="stat-num" id="task-count">—</div><div class="stat-label">Optimization Tasks</div></div>
    <div class="stat-card"><div class="stat-num">3</div><div class="stat-label">Difficulty Levels</div></div>
    <div class="stat-card"><div class="stat-num" id="carbon-stat">🌱</div><div class="stat-label">CO₂ Tracking</div></div>
  </div>

  <div class="card">
    <h2>📋 Available Tasks</h2>
    <div id="tasks-loading"><span class="spinner"></span>Loading tasks...</div>
    <table id="tasks-table" style="display:none">
      <thead><tr><th>Task</th><th>Difficulty</th><th>Description</th></tr></thead>
      <tbody id="tasks-body"></tbody>
    </table>
  </div>

  <div class="card">
    <h2>🔌 API Endpoints</h2>
    <div class="endpoints">
      <div class="ep"><span class="ep-method ep-post">POST</span><span class="ep-path">/reset</span></div>
      <div class="ep"><span class="ep-method ep-post">POST</span><span class="ep-path">/step</span></div>
      <div class="ep"><span class="ep-method ep-get">GET</span><span class="ep-path">/state</span></div>
      <div class="ep"><span class="ep-method ep-get">GET</span><span class="ep-path">/tasks</span></div>
      <div class="ep"><span class="ep-method ep-post">POST</span><span class="ep-path">/grader</span></div>
      <div class="ep"><span class="ep-method ep-post">POST</span><span class="ep-path">/baseline</span></div>
    </div>
  </div>

  <div class="card">
    <h2>🌍 How It Works</h2>
    <p style="color:#475569;line-height:1.8;font-size:.95rem">
      <strong>1.</strong> Agent receives inefficient Python code via <code>/reset</code><br>
      <strong>2.</strong> Agent submits optimized code via <code>/step</code><br>
      <strong>3.</strong> Environment grades correctness + optimization + carbon savings<br>
      <strong>4.</strong> Agent iterates using feedback until optimal score is reached
    </p>
  </div>

  <div class="footer">
    <p>Built for the <strong>Meta OpenEnv Hackathon</strong> · <a href="/docs">API Docs ↗</a></p>
  </div>
</div>

<script>
fetch('/tasks').then(r=>r.json()).then(tasks=>{
  document.getElementById('task-count').textContent=tasks.length;
  const tbody=document.getElementById('tasks-body');
  tasks.forEach(t=>{
    const dc=t.difficulty==='easy'?'diff-easy':t.difficulty==='medium'?'diff-medium':'diff-hard';
    const cap=t.difficulty.charAt(0).toUpperCase()+t.difficulty.slice(1);
    tbody.innerHTML+=`<tr><td style="font-weight:600">${t.id}</td><td><span class="${dc}">${cap}</span></td><td style="color:#64748b;font-size:.85rem">${t.description.substring(0,80)}...</td></tr>`;
  });
  document.getElementById('tasks-loading').style.display='none';
  document.getElementById('tasks-table').style.display='table';
}).catch(()=>{document.getElementById('tasks-loading').textContent='Could not load tasks';});
</script>
</body>
</html>""")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
