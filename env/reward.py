"""Trajectory-based reward function.

Provides meaningful per-step reward signals to guide the agent.
"""

from models.schemas import Reward, RewardBreakdown, GraderResult


def compute_reward(
    grader_result: GraderResult,
    previous_optimization_score: float,
) -> Reward:
    """Compute a step reward from the grader result.

    Reward ranges:
      Correct + improved:      +0.5 to +1.0
      Partial improvement:     +0.2 to +0.5
      No improvement:          -0.05
      Incorrect output:        -1.0
      Invalid code:            -0.5

    Args:
        grader_result: result from the Grader
        previous_optimization_score: optimization score from the prior step

    Returns:
        Reward with score and breakdown
    """
    # ── Invalid code ───────────────────────────────────────────────────
    if grader_result.penalty >= 0.5:
        return Reward(
            score=-0.5,
            breakdown=RewardBreakdown(
                correctness=0.0,
                optimization=0.0,
                penalty=-0.5,
                reason="Invalid or unsafe code submitted",
            ),
            feedback="Your code is invalid or contains unsafe constructs. "
                     "Please fix syntax errors and remove blocked operations.",
        )

    # ── Incorrect output ───────────────────────────────────────────────
    if grader_result.correctness_score < 1.0:
        return Reward(
            score=-1.0,
            breakdown=RewardBreakdown(
                correctness=0.0,
                optimization=0.0,
                penalty=-1.0,
                reason="Incorrect output — test cases failed",
            ),
            feedback="Your code produces incorrect output. "
                     "Ensure all test cases pass before optimizing.",
        )

    # ── Correct code, check improvement ────────────────────────────────
    improvement = grader_result.optimization_score - previous_optimization_score

    if improvement > 0.1:
        # Significant improvement
        score = 0.5 + min(0.5, improvement * 2.0)
        return Reward(
            score=round(score, 4),
            breakdown=RewardBreakdown(
                correctness=1.0,
                optimization=grader_result.optimization_score,
                penalty=0.0,
                reason=f"Significant improvement (+{improvement:.3f})",
            ),
            feedback="Great optimization! Your code is more efficient.",
        )
    elif improvement > 0.0:
        # Partial improvement
        score = 0.2 + min(0.3, improvement * 3.0)
        return Reward(
            score=round(score, 4),
            breakdown=RewardBreakdown(
                correctness=1.0,
                optimization=grader_result.optimization_score,
                penalty=0.0,
                reason=f"Partial improvement (+{improvement:.3f})",
            ),
            feedback="Some improvement detected. Keep optimizing!",
        )
    else:
        # No improvement
        return Reward(
            score=-0.05,
            breakdown=RewardBreakdown(
                correctness=1.0,
                optimization=grader_result.optimization_score,
                penalty=-0.05,
                reason="No optimization improvement detected",
            ),
            feedback="Your code is correct but no optimization improvement "
                     "was detected. Try using builtins, comprehensions, or "
                     "reducing loops.",
        )
