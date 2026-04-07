"""Deterministic grader for the EcoCode environment.

Produces a structured GraderResult with:
  - correctness_score (binary gate)
  - optimization_score (AST-based)
  - penalty
  - final_score (combined, strictly in (0, 1))
  - details (human-readable)
"""

from models.schemas import GraderResult
from utils.sandbox import run_test_case, run_benchmark
from utils.code_analysis import analyze_code, compute_improvement_score

# Validator requires scores strictly within (0, 1) — not 0.0 and not 1.0
# Use 0.01/0.99 so they format correctly as "0.01"/"0.99" with :.2f
_SCORE_MIN = 0.01
_SCORE_MAX = 0.99


def _clamp(score: float) -> float:
    """Clamp score to open interval (0, 1) as required by the validator."""
    return max(_SCORE_MIN, min(_SCORE_MAX, score))


class Grader:
    """Deterministic grader — no randomness."""

    def grade(
        self,
        original_code: str,
        rewritten_code: str,
        test_cases: list[dict],
    ) -> GraderResult:
        """Grade rewritten code against original.

        Args:
            original_code: the original dirty code
            rewritten_code: the agent's optimized submission
            test_cases: list of {input, expected_output}

        Returns:
            GraderResult with full breakdown
        """
        details_parts: list[str] = []

        # ── 1. Syntax / safety check ───────────────────────────────────
        from utils.sandbox import validate_code
        err = validate_code(rewritten_code)
        if err:
            return GraderResult(
                correctness_score=_SCORE_MIN,
                optimization_score=_SCORE_MIN,
                penalty=0.5,
                final_score=_SCORE_MIN,
                details=f"Invalid code: {err}",
            )

        # ── 2. Correctness gate ────────────────────────────────────────
        all_passed = True
        passed_count = 0
        for tc in test_cases:
            result = run_test_case(rewritten_code, tc["input"])
            expected = tc["expected_output"].rstrip("\n")
            actual = result.output.rstrip("\n") if result.success else ""

            if not result.success or actual != expected:
                all_passed = False
                details_parts.append(
                    f"FAIL: input={tc['input']!r} "
                    f"expected={expected!r} got={actual!r}"
                )
            else:
                passed_count += 1

        total_tests = len(test_cases)
        if not all_passed:
            details_parts.insert(
                0, f"Correctness: {passed_count}/{total_tests} tests passed"
            )
            partial = _clamp(passed_count / total_tests * 0.4) if total_tests else _SCORE_MIN
            return GraderResult(
                correctness_score=_clamp(passed_count / total_tests) if total_tests else _SCORE_MIN,
                optimization_score=_SCORE_MIN,
                penalty=0.01,
                final_score=partial,
                details="\n".join(details_parts),
            )

        correctness_score = _SCORE_MAX
        details_parts.append(f"Correctness: {total_tests}/{total_tests} tests passed")

        # ── 3. Optimization scoring ────────────────────────────────────
        original_metrics = analyze_code(original_code)
        new_metrics = analyze_code(rewritten_code)
        optimization_score = compute_improvement_score(original_metrics, new_metrics)

        details_parts.append(f"Optimization score: {optimization_score:.3f}")

        # ── 4. No-improvement penalty ──────────────────────────────────
        penalty = 0.01
        if optimization_score < 0.01:
            penalty = 0.1
            details_parts.append("Penalty: no measurable optimization improvement")

        # ── 5. Combine ─────────────────────────────────────────────────
        # Weighted: 40% correctness gate + 60% optimization, minus penalty
        # Clamped to strictly open interval (0, 1) per validator requirement
        raw_score = correctness_score * 0.4 + optimization_score * 0.6 - penalty
        final_score = _clamp(raw_score)
        details_parts.append(f"Final score: {final_score:.3f}")

        # ── 6. Benchmarking (Safe & Optional) ──────────────────────────────
        time_orig = None
        time_opt = None
        time_percent = None
        mem_orig = None
        mem_opt = None
        mem_percent = None
        carbon_orig = None
        carbon_opt = None
        carbon_grams = None
        carbon_percent = None

        if test_cases and final_score >= 0.01:  # Only benchmark if no fatal error
            tc_input = test_cases[0]["input"]  # Use first test case for benchmark
            try:
                if original_code.strip() == rewritten_code.strip():
                    bench_orig = run_benchmark(original_code, tc_input)
                    bench_opt = bench_orig
                else:
                    bench_orig = run_benchmark(original_code, tc_input)
                    bench_opt = run_benchmark(rewritten_code, tc_input)
                
                if bench_orig.time_avg is not None and bench_opt.time_avg is not None:
                    time_orig = bench_orig.time_avg
                    time_opt = bench_opt.time_avg
                    if time_orig > 0:
                        improvement = (time_orig - time_opt) / time_orig
                        threshold = 0.10  # 10% tolerance to absorb OS variance
                        if abs(improvement) < threshold:
                            time_percent = None  # No meaningful improvement
                        else:
                            time_percent = improvement * 100.0
                        
                if bench_orig.memory_peak is not None and bench_opt.memory_peak is not None:
                    mem_orig = bench_orig.memory_peak / 1048576.0  # MB
                    mem_opt = bench_opt.memory_peak / 1048576.0  # MB
                    if mem_orig > 0:
                        mem_improvement = (mem_orig - mem_opt) / mem_orig
                        threshold = 0.10  # 10% tolerance to absorb OS variance
                        if abs(mem_improvement) < threshold:
                            mem_percent = None  # No meaningful improvement
                        else:
                            mem_percent = mem_improvement * 100.0

                # Carbon Calculation
                if time_orig is not None and mem_orig is not None:
                    POWER_USAGE_CONSTANT = 0.5
                    MEMORY_POWER_CONSTANT = 0.0001
                    carbon_orig = (time_orig * POWER_USAGE_CONSTANT) + (mem_orig * MEMORY_POWER_CONSTANT)
                    carbon_opt = (time_opt * POWER_USAGE_CONSTANT) + (mem_opt * MEMORY_POWER_CONSTANT)
                    carbon_grams = carbon_orig - carbon_opt
                    # If carbon_grams is essentially zero, set to None
                    if abs(carbon_grams) < 1e-9:
                        carbon_grams = None
                    if carbon_orig > 0:
                        carbon_improvement = (carbon_grams or 0.01) / carbon_orig
                        threshold = 0.10  # 10% tolerance to absorb OS variance
                        if abs(carbon_improvement) < threshold:
                            carbon_percent = None  # No meaningful improvement
                        else:
                            carbon_percent = carbon_improvement * 100.0
            except Exception:
                pass  # Silently skip benchmarking if it fails

        return GraderResult(
            correctness_score=correctness_score,
            optimization_score=optimization_score,
            penalty=penalty,
            final_score=final_score,
            details="\n".join(details_parts),
            time_original=time_orig,
            time_optimized=time_opt,
            time_improvement_percent=time_percent,
            memory_original=mem_orig,
            memory_optimized=mem_opt,
            memory_reduction_percent=mem_percent,
            carbon_original=carbon_orig,
            carbon_optimized=carbon_opt,
            carbon_saved_grams=carbon_grams,
            carbon_saved_percent=carbon_percent,
        )
