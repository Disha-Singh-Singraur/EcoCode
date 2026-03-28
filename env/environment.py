"""EcoCode OpenEnv-compatible environment.

Provides:
  - reset(task_id?) → Observation
  - step(action) → (Observation, Reward, done, info)
  - state() → EnvironmentState
"""

from typing import Any, Dict, Optional, Tuple

from models.schemas import (
    Action,
    EnvironmentState,
    GraderResult,
    Observation,
    Reward,
    TestCase,
)
from tasks.definitions import TASKS, get_task, list_task_ids
from grader.grader import Grader
from env.reward import compute_reward
from utils.code_analysis import analyze_code, metrics_are_equal

MAX_STEPS = 5
OPTIMAL_THRESHOLD = 0.95


class EcoCodeEnv:
    """OpenEnv-compatible environment for code optimisation."""

    def __init__(self) -> None:
        self._grader = Grader()
        self._task: Optional[dict] = None
        self._current_code: str = ""
        self._original_code: str = ""
        self._test_cases: list[dict] = []
        self._difficulty: str = ""
        self._task_id: str = ""
        self._step_count: int = 0
        self._done: bool = True
        self._history: list[Dict[str, Any]] = []
        self._prev_optimization_score: float = 0.0
        self._prev_metrics: Optional[Dict[str, Any]] = None

    # ── OpenEnv interface ──────────────────────────────────────────────

    def reset(self, task_id: Optional[str] = None) -> Observation:
        """Reset environment with a task. Defaults to first task."""
        if task_id is None:
            task_id = list_task_ids()[0]

        task = get_task(task_id)
        self._task = task
        self._task_id = task_id
        self._current_code = task["dirty_code"]
        self._original_code = task["dirty_code"]
        self._test_cases = task["test_cases"]
        self._difficulty = task["difficulty"]
        self._step_count = 0
        self._done = False
        self._history = []
        self._prev_optimization_score = 0.0
        self._prev_metrics = analyze_code(self._original_code)

        return self._make_observation()

    def step(
        self, action: Action
    ) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
        """Apply an action and return (observation, reward, done, info)."""
        if self._done:
            raise RuntimeError("Episode is done. Call reset() first.")

        self._step_count += 1
        info: Dict[str, Any] = {"step": self._step_count}

        # Grade the submission
        grader_result = self._grader.grade(
            original_code=self._original_code,
            rewritten_code=action.rewritten_code,
            test_cases=self._test_cases,
        )
        info["grader_result"] = grader_result.model_dump()

        # Compute reward
        reward = compute_reward(grader_result, self._prev_optimization_score)

        # Update state only if code is valid and correct
        if (
            grader_result.correctness_score >= 1.0
            and grader_result.penalty < 0.5
        ):
            self._current_code = action.rewritten_code
            new_metrics = analyze_code(action.rewritten_code)

            # ── Optimal solution detection ─────────────────────────────
            # Early termination if score ≥ 0.95
            if grader_result.final_score >= OPTIMAL_THRESHOLD:
                self._done = True
                info["termination_reason"] = "optimal_score_reached"

            # Early termination if AST metrics plateaued
            elif self._prev_metrics and metrics_are_equal(
                self._prev_metrics, new_metrics
            ):
                # Only terminate for plateau if we've had at least 2 steps
                if self._step_count >= 2:
                    self._done = True
                    info["termination_reason"] = "no_further_ast_improvements"

            self._prev_optimization_score = grader_result.optimization_score
            self._prev_metrics = new_metrics
        else:
            info["state_unchanged"] = True
            if grader_result.penalty >= 0.5:
                self._done = True
                info["termination_reason"] = "fatal_error"

        # Max steps check
        if self._step_count >= MAX_STEPS:
            self._done = True
            info["termination_reason"] = info.get(
                "termination_reason", "max_steps_reached"
            )

        # Record history
        self._history.append({
            "step": self._step_count,
            "reward": reward.score,
            "grader_final_score": grader_result.final_score,
            "done": self._done,
        })

        return self._make_observation(), reward, self._done, info

    def state(self) -> EnvironmentState:
        """Return current environment state."""
        return EnvironmentState(
            task_id=self._task_id,
            current_code=self._current_code,
            original_code=self._original_code,
            step_count=self._step_count,
            max_steps=MAX_STEPS,
            done=self._done,
            history=self._history,
        )

    # ── Helpers ────────────────────────────────────────────────────────

    def _make_observation(self) -> Observation:
        return Observation(
            current_code=self._current_code,
            original_code=self._original_code,
            test_cases=[
                TestCase(input=tc["input"], expected_output=tc["expected_output"])
                for tc in self._test_cases
            ],
            difficulty=self._difficulty,
            step_count=self._step_count,
        )
