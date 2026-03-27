"""Pydantic models for the EcoCode environment."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TestCase(BaseModel):
    """A single test case with input and expected output."""
    input: str = Field(..., description="Input to pass to the function")
    expected_output: str = Field(..., description="Expected stdout output")


class Observation(BaseModel):
    """Observation returned by the environment."""
    current_code: str = Field(..., description="Current version of the code")
    original_code: str = Field(..., description="Original dirty code")
    test_cases: List[TestCase] = Field(..., description="Test cases for validation")
    difficulty: str = Field(..., description="Task difficulty: easy, medium, hard")
    step_count: int = Field(0, description="Current step number in the episode")


class Action(BaseModel):
    """Action submitted by the agent."""
    rewritten_code: str = Field(..., description="Agent's optimized version of the code")


class RewardBreakdown(BaseModel):
    """Detailed breakdown of reward components."""
    correctness: float = Field(..., description="1.0 if all tests pass, 0.0 otherwise")
    optimization: float = Field(..., description="Optimization improvement score")
    penalty: float = Field(0.0, description="Penalty applied")
    reason: str = Field("", description="Human-readable explanation")


class Reward(BaseModel):
    """Reward signal returned per step."""
    score: float = Field(..., description="Final reward value for this step")
    breakdown: RewardBreakdown = Field(..., description="Detailed score breakdown")
    feedback: str = Field("", description="Feedback message for the agent")


class GraderResult(BaseModel):
    """Structured result from the deterministic grader."""
    correctness_score: float = Field(..., description="0.0 or 1.0 binary gate")
    optimization_score: float = Field(..., description="0.0-1.0 AST improvement score")
    penalty: float = Field(0.0, description="Penalty for no improvement or invalid code")
    final_score: float = Field(..., description="Combined score clamped to 0.0-1.0")
    details: str = Field("", description="Human-readable grading explanation")
    
    # Optional performance benchmarking
    time_original: Optional[float] = Field(None, description="Execution time of original code")
    time_optimized: Optional[float] = Field(None, description="Execution time of optimized code")
    time_improvement_percent: Optional[float] = Field(None, description="Percentage of execution time saved")
    memory_original: Optional[float] = Field(None, description="Peak memory usage of original code")
    memory_optimized: Optional[float] = Field(None, description="Peak memory usage of optimized code")
    memory_reduction_percent: Optional[float] = Field(None, description="Percentage of peak memory saved")

    # Optional carbon footprint estimation
    carbon_original: Optional[float] = Field(None, description="Estimated gCO2eq for original code")
    carbon_optimized: Optional[float] = Field(None, description="Estimated gCO2eq for optimized code")
    carbon_saved_grams: Optional[float] = Field(None, description="Estimated gCO2eq saved")
    carbon_saved_percent: Optional[float] = Field(None, description="Percentage of carbon footprint saved")


class TaskInfo(BaseModel):
    """Task metadata returned by /tasks endpoint."""
    id: str = Field(..., description="Unique task identifier")
    description: str = Field(..., description="What the task requires")
    difficulty: str = Field(..., description="easy, medium, or hard")
    sample_observation: Optional[Observation] = Field(
        None, description="Example observation for this task"
    )
    action_schema: Dict[str, Any] = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "rewritten_code": {
                    "type": "string",
                    "description": "Optimized version of the code",
                }
            },
            "required": ["rewritten_code"],
        },
        description="JSON schema for the Action model",
    )


class EnvironmentState(BaseModel):
    """Full internal state snapshot."""
    task_id: str = Field(..., description="Current task identifier")
    current_code: str = Field(..., description="Current code version")
    original_code: str = Field(..., description="Original dirty code")
    step_count: int = Field(0, description="Steps taken so far")
    max_steps: int = Field(5, description="Maximum allowed steps")
    done: bool = Field(False, description="Whether the episode has ended")
    history: List[Dict[str, Any]] = Field(
        default_factory=list, description="History of actions and rewards"
    )
