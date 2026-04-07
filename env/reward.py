"""Trajectory-based reward function.

Provides meaningful per-step reward signals to guide the agent.
All scores are strictly within (0, 1) per validator requirement.
"""

from models.schemas import Reward, RewardBreakdown, GraderResult

# Score bands — all strictly within (0, 1)
_INVALID_SCORE   = 0.05   # invalid / unsafe code
_INCORRECT_SCORE = 0.10   # correct syntax but wrong output
_NO_IMPROVE_SCORE = 0.15  # correct but no optimization gain
_PARTIAL_MIN     = 0.20   # minimum for partial improvement
_PARTIAL_MAX     = 0.49   # maximum for partial improvement (safe at 2dp)
_GOOD_MIN        = 0.51   # minimum for significant improvement (safe at 2dp)
_GOOD_MAX        = 0.99   # maximum ("0.99" with :.2f, never reaches 1.0)


def _clamp(score: float, lo: float = 0.01, hi: float = 0.99) -> float:
    return max(lo, min(hi, score))


def compute_reward(
    grader_result: GraderResult,
    previous_optimization_score: float,
) -> Reward:
    """Compute a step reward from the grader result.

    Reward ranges (all strictly within (0, 1)):
      Invalid code:            0.05
      Incorrect output:        0.10
      No improvement:          0.15
      Partial improvement:     0.20 – 0.50
      Significant improvement: 0.50 – 0.999

    Args:
        grader_result: result from the Grader
        previous_optimization_score: optimization score from the prior step

    Returns:
        Reward with score and breakdown
    """
    # ── Invalid code ───────────────────────────────────────────────────
    if grader_result.penalty >= 0.5:
        return Reward(
            score=_INVALID_SCORE,
            breakdown=RewardBreakdown(
                correctness=0.001,
                optimization=0.001,
                penalty=_INVALID_SCORE,
                reason="Invalid or unsafe code submitted",
            ),
            feedback="Your code is invalid or contains unsafe constructs. "
                     "Please fix syntax errors and remove blocked operations.",
        )

    # ── Incorrect output ───────────────────────────────────────────────
    if grader_result.correctness_score < 0.99:
        return Reward(
            score=_INCORRECT_SCORE,
            breakdown=RewardBreakdown(
                correctness=grader_result.correctness_score,
                optimization=0.001,
                penalty=_INCORRECT_SCORE,
                reason="Incorrect output — test cases failed",
            ),
            feedback="Your code produces incorrect output. "
                     "Ensure all test cases pass before optimizing.",
        )

    # ── Correct code, check improvement ────────────────────────────────
    improvement = grader_result.optimization_score - previous_optimization_score

    if improvement > 0.1:
        # Significant improvement
        raw = _GOOD_MIN + min(_GOOD_MAX - _GOOD_MIN, improvement * 2.0 * (_GOOD_MAX - _GOOD_MIN))
        score = _clamp(raw, _GOOD_MIN, _GOOD_MAX)
        return Reward(
            score=round(score, 4),
            breakdown=RewardBreakdown(
                correctness=0.999,
                optimization=grader_result.optimization_score,
                penalty=0.001,
                reason=f"Significant improvement (+{improvement:.3f})",
            ),
            feedback="Great optimization! Your code is more efficient.",
        )
    elif improvement > 0.0:
        # Partial improvement
        raw = _PARTIAL_MIN + min(_PARTIAL_MAX - _PARTIAL_MIN, improvement * 3.0 * (_PARTIAL_MAX - _PARTIAL_MIN))
        score = _clamp(raw, _PARTIAL_MIN, _PARTIAL_MAX)
        return Reward(
            score=round(score, 4),
            breakdown=RewardBreakdown(
                correctness=0.999,
                optimization=grader_result.optimization_score,
                penalty=0.001,
                reason=f"Partial improvement (+{improvement:.3f})",
            ),
            feedback="Some improvement detected. Keep optimizing!",
        )
    else:
        # No improvement
        return Reward(
            score=_NO_IMPROVE_SCORE,
            breakdown=RewardBreakdown(
                correctness=0.999,
                optimization=grader_result.optimization_score,
                penalty=_NO_IMPROVE_SCORE,
                reason="No optimization improvement detected",
            ),
            feedback="Your code is correct but no optimization improvement "
                     "was detected. Try using builtins, comprehensions, or "
                     "reducing loops.",
        )
