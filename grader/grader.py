"""Deterministic grader for the EcoCode environment.

Produces a structured GraderResult with:
  - correctness_score (binary gate)
  - optimization_score (AST-based)
  - penalty
  - final_score (combined, 0.0–1.0)
  - details (human-readable)
"""

from models.schemas import GraderResult
from utils.sandbox import run_test_case, run_benchmark
from utils.code_analysis import analyze_code, compute_improvement_score


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
                correctness_score=0.0,
                optimization_score=0.0,
                penalty=0.5,
                final_score=0.0,
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
            return GraderResult(
                correctness_score=0.0,
                optimization_score=0.0,
                penalty=0.0,
                final_score=0.0,
                details="\n".join(details_parts),
            )

        correctness_score = 1.0
        details_parts.append(f"Correctness: {total_tests}/{total_tests} tests passed")

        # ── 3. Optimization scoring ────────────────────────────────────
        original_metrics = analyze_code(original_code)
        new_metrics = analyze_code(rewritten_code)
        optimization_score = compute_improvement_score(original_metrics, new_metrics)

        details_parts.append(f"Optimization score: {optimization_score:.3f}")

        # ── 4. No-improvement penalty ──────────────────────────────────
        penalty = 0.0
        if optimization_score < 0.01:
            penalty = 0.1
            details_parts.append("Penalty: no measurable optimization improvement")

        # ── 5. Combine ─────────────────────────────────────────────────
        # Weighted: 40% correctness gate + 60% optimization, minus penalty
        final_score = max(
            0.0,
            min(1.0, correctness_score * 0.4 + optimization_score * 0.6 - penalty),
        )
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

        if test_cases and final_score >= 0.0:  # Only benchmark if no fatal error
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
                        threshold = 0.10  # 10% tolerance to absorb OS variance  # 2% tolerance
                        if abs(improvement) < threshold:
                            improvement = 0.0
                        time_percent = improvement * 100.0
                        
                if bench_orig.memory_peak is not None and bench_opt.memory_peak is not None:
                    mem_orig = bench_orig.memory_peak / 1048576.0  # MB
                    mem_opt = bench_opt.memory_peak / 1048576.0  # MB
                    if mem_orig > 0:
                        mem_improvement = (mem_orig - mem_opt) / mem_orig
                        threshold = 0.10  # 10% tolerance to absorb OS variance
                        if abs(mem_improvement) < threshold:
                            mem_improvement = 0.0
                        mem_percent = mem_improvement * 100.0

                # Carbon Calculation
                if time_orig is not None and mem_orig is not None:
                    POWER_USAGE_CONSTANT = 0.5
                    MEMORY_POWER_CONSTANT = 0.0001
                    carbon_orig = (time_orig * POWER_USAGE_CONSTANT) + (mem_orig * MEMORY_POWER_CONSTANT)
                    carbon_opt = (time_opt * POWER_USAGE_CONSTANT) + (mem_opt * MEMORY_POWER_CONSTANT)
                    carbon_grams = carbon_orig - carbon_opt
                    if carbon_orig > 0:
                        carbon_improvement = carbon_grams / carbon_orig
                        threshold = 0.10  # 10% tolerance to absorb OS variance
                        if abs(carbon_improvement) < threshold:
                            carbon_improvement = 0.0
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
