"""Baseline inference script for the EcoCode environment.

Supports TWO modes:
  Mode A — OpenAI API (if OPENAI_API_KEY is set): temperature=0, fixed prompts
  Mode B — Deterministic fallback (no API key): rule-based optimal solutions

Usage:
    # Mode A (API):
    export OPENAI_API_KEY="sk-..."
    python -m scripts.baseline

    # Mode B (fallback):
    python -m scripts.baseline
"""

import json
import os
import sys

from env.environment import EcoCodeEnv
from models.schemas import Action
from tasks.definitions import list_task_ids

# ═══════════════════════════════════════════════════════════════════════
# DETERMINISTIC FALLBACK SOLUTIONS (Mode B)
# ═══════════════════════════════════════════════════════════════════════

FALLBACK_SOLUTIONS = {
    "loop_sum": (
        "def compute_sum(numbers):\n"
        "    return sum(numbers)\n"
    ),
    "nested_search": (
        "def find_common(list_a, list_b):\n"
        "    return sorted(set(list_a) & set(list_b))\n"
    ),
    "string_builder": (
        "def format_words(words):\n"
        "    return ', '.join(word.capitalize() for word in words)\n"
    ),
    "combined_opts": (
        "def analyze_numbers(numbers):\n"
        "    unique = list(set(numbers))\n"
        "    count = len(unique)\n"
        "    avg = sum(unique) / count if count else 0\n"
        "    return str(count) + ':' + str(avg) + ':' + str(sorted(unique))\n"
    ),
    "dictionary_frequency": (
        "def count_freq(items):\n"
        "    freq = {}\n"
        "    for item in items:\n"
        "        freq[item] = freq.get(item, 0) + 1\n"
        "    return ', '.join(str(k) + ':' + str(v) for k, v in freq.items())\n"
    ),
    "generator_vs_list": (
        "def process_data(limit):\n"
        "    data = (x * 2 for x in range(limit))\n"
        "    return sum(data)\n"
    ),
    "fibonacci_memoization": (
        "def fibonacci(n, cache={}):\n"
        "    if n in cache:\n"
        "        return cache[n]\n"
        "    if n <= 1:\n"
        "        return n\n"
        "    cache[n] = fibonacci(n - 1) + fibonacci(n - 2)\n"
        "    return cache[n]\n"
    ),
    "loop_invariant_motion": (
        "def process_transactions(transactions, settings_str):\n"
        "    parts = settings_str.split(':')\n"
        "    multiplier = int(parts[1])\n"
        "    base_fee = float(parts[2])\n"
        "    return [t * multiplier + base_fee for t in transactions]\n"
    ),
    "math_simplification": (
        "def sum_to_n(n):\n"
        "    return n * (n + 1) // 2\n"
    ),
    "any_builtin": (
        "def contains_positive(numbers):\n"
        "    return any(n > 0 for n in numbers)\n"
    ),
    "all_builtin": (
        "def is_all_positive(numbers):\n"
        "    return all(n > 0 for n in numbers)\n"
    ),
    "enumerate_builtin": (
        "def format_indexed(items):\n"
        "    return [str(i) + '-' + str(val) for i, val in enumerate(items)]\n"
    ),
    "zip_builtin": (
        "def combine_lists(list_a, list_b):\n"
        "    return [a + b for a, b in zip(list_a, list_b)]\n"
    ),
    "max_builtin": (
        "def find_highest(numbers):\n"
        "    if not numbers:\n"
        "        return None\n"
        "    return max(numbers)\n"
    ),
    "filter_builtin": (
        "def get_evens(numbers):\n"
        "    return [n for n in numbers if n % 2 == 0]\n"
    ),
}

# ═══════════════════════════════════════════════════════════════════════
# OPENAI API AGENT (Mode A)
# ═══════════════════════════════════════════════════════════════════════

MODEL = "gpt-4o-mini"
TEMPERATURE = 0  # Deterministic

SYSTEM_PROMPT = (
    "You are an expert Python developer specializing in code optimization. "
    "You will receive inefficient Python code and must rewrite it to be more "
    "efficient while preserving the exact same output.\n\n"
    "Rules:\n"
    "1. The rewritten code MUST produce identical output for all inputs.\n"
    "2. Use Python builtins (sum, sorted, len, etc.) where appropriate.\n"
    "3. Replace manual loops with list comprehensions or generator expressions.\n"
    "4. Remove redundant variables and unnecessary operations.\n"
    "5. Use set operations for membership testing instead of nested loops.\n"
    "6. Use str.join() instead of string concatenation in loops.\n\n"
    "Return ONLY the rewritten Python code, no explanations or markdown."
)


def build_user_prompt(observation) -> str:
    """Build a fixed-format user prompt from an observation."""
    test_info = "\n".join(
        f"  - Input: {tc.input} -> Expected: {tc.expected_output}"
        for tc in observation.test_cases
    )
    return (
        f"Optimize the following Python code:\n\n"
        f"```python\n{observation.current_code}```\n\n"
        f"Test cases:\n{test_info}\n\n"
        f"Difficulty: {observation.difficulty}\n"
        f"Return ONLY the optimized Python code."
    )


def call_openai(prompt: str) -> str:
    """Call OpenAI API with deterministic settings."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=MODEL,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1024,
    )
    content = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    if content.startswith("```python"):
        content = content[len("```python"):].strip()
    if content.startswith("```"):
        content = content[3:].strip()
    if content.endswith("```"):
        content = content[:-3].strip()

    return content


# ═══════════════════════════════════════════════════════════════════════
# BASELINE RUNNER
# ═══════════════════════════════════════════════════════════════════════

def run_baseline_evaluation() -> dict:
    """Run the baseline agent across all tasks.

    Automatically selects Mode A (API) or Mode B (fallback).
    """
    use_api = bool(os.environ.get("OPENAI_API_KEY"))
    mode = "OpenAI API (Mode A)" if use_api else "Deterministic Fallback (Mode B)"

    print("=" * 60)
    print("EcoCode Baseline Evaluation")
    print(f"Mode: {mode}")
    print("=" * 60)

    env = EcoCodeEnv()
    results = {}
    correct_count = 0
    total_tasks = 0

    for task_id in list_task_ids():
        total_tasks += 1
        obs = env.reset(task_id=task_id)

        correctness = 0.0
        final_score = 0.0
        optimization = 0.0
        reward_score = 0.0

        if use_api:
            user_prompt = build_user_prompt(obs)
            max_steps = 3
            step_count = 0
            done = False
            
            while not done and step_count < max_steps:
                step_count += 1
                rewritten = call_openai(user_prompt)
                action = Action(rewritten_code=rewritten)
                obs2, reward, done, info = env.step(action)
                
                gr = info.get("grader_result", {})
                final_score = gr.get("final_score", 0.0)
                correctness = gr.get("correctness_score", 0.0)
                optimization = gr.get("optimization_score", 0.0)
                reward_score = reward.score
                
                if correctness < 1.0 or reward_score < 0.0:
                    details = gr.get("details", "")
                    user_prompt += (
                        f"\n\n--- Attempt {step_count} Failed ---\n"
                        f"Your code:\n```python\n{rewritten}\n```\n"
                        f"Feedback: {reward.feedback}\n"
                        f"Grader Details:\n{details}\n"
                        f"Please fix the mistakes and optimize further. Return ONLY the optimized Python code."
                    )
                else:
                    break
        else:
            rewritten = FALLBACK_SOLUTIONS.get(task_id, obs.current_code)
            action = Action(rewritten_code=rewritten)
            obs2, reward, done, info = env.step(action)

            gr = info.get("grader_result", {})
            final_score = gr.get("final_score", 0.0)
            correctness = gr.get("correctness_score", 0.0)
            optimization = gr.get("optimization_score", 0.0)
            reward_score = reward.score

        if correctness >= 1.0:
            correct_count += 1

        results[task_id] = {
            "task_id": task_id,
            "difficulty": obs.difficulty,
            "final_score": final_score,
            "correctness": correctness,
            "optimization": optimization,
            "reward": reward_score,
        }

    # ── Print results ──────────────────────────────────────────────────
    print()
    print("-" * 60)
    print(f"{'Task':<20} {'Difficulty':<10} {'Score':<10} {'Correct':<10}")
    print("-" * 60)

    total_score = 0.0
    for tid, res in results.items():
        score = res["final_score"]
        total_score += score
        correct = "Yes" if res["correctness"] >= 1.0 else "No"
        print(f"{tid:<20} {res['difficulty']:<10} {score:<10.3f} {correct:<10}")

    avg_score = total_score / total_tasks if total_tasks else 0.0
    success_rate = correct_count / total_tasks if total_tasks else 0.0

    print("-" * 60)
    print(f"{'Average Score:':<20} {avg_score:.3f}")
    print(f"{'Success Rate:':<20} {success_rate:.0%} ({correct_count}/{total_tasks})")
    print("=" * 60)

    return {
        "mode": mode,
        "tasks": results,
        "average_score": round(avg_score, 4),
        "success_rate": round(success_rate, 4),
        "correct_count": correct_count,
        "total_tasks": total_tasks,
    }


if __name__ == "__main__":
    results = run_baseline_evaluation()

    # Save results to JSON
    output_path = "baseline_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
