"""
Inference Script for EcoCode
===================================
MANDATORY
- Before submitting, ensure the following variables are defined in your environment configuration:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.
    
- The inference script must be named `inference.py` and placed in the root directory of the project
- Participants must use OpenAI Client for all LLM calls using above variables

STDOUT FORMAT
- The script emits exactly three line types to stdout per task:

    [START] task=<task_name> env=ecocode model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
"""

import os
import json
import textwrap
from typing import List, Optional

from openai import OpenAI
from env.environment import EcoCodeEnv
from models.schemas import Action
from tasks.definitions import list_task_ids

# ── Environment Variables ──────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")

# ── Configuration ──────────────────────────────────────────────────
BENCHMARK = "ecocode"
MAX_STEPS = 3
TEMPERATURE = 0.0  # Deterministic for baseline
MAX_TOKENS = 1024
SUCCESS_SCORE_THRESHOLD = 0.5  # score in [0, 1]

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


# ── Structured Logging Helpers ─────────────────────────────────────
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# ── Prompt Builders ────────────────────────────────────────────────
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


def parse_model_code(content: str) -> str:
    """Extract code from model response, stripping markdown fences."""
    content = content.strip()
    if content.startswith("```python"):
        content = content[len("```python"):].strip()
    if content.startswith("```"):
        content = content[3:].strip()
    if content.endswith("```"):
        content = content[:-3].strip()
    return content


# ── Main ───────────────────────────────────────────────────────────
def main() -> None:
    if not HF_TOKEN:
        print("Error: HF_TOKEN environment variable not set.", flush=True)
        return

    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    env = EcoCodeEnv()

    all_results = {}

    for task_id in list_task_ids():
        # ── [START] ────────────────────────────────────────────────
        log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

        obs = env.reset(task_id=task_id)
        user_prompt = build_user_prompt(obs)

        done = False
        steps_taken = 0
        final_score = 0.01
        correctness = 0.0
        rewards: List[float] = []
        success = False
        last_error: Optional[str] = None

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            steps_taken = step
            last_error = None

            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                )
                response_text = completion.choices[0].message.content or ""
                rewritten = parse_model_code(response_text)

                action = Action(rewritten_code=rewritten)
                obs, reward, done, info = env.step(action)

                gr = info.get("grader_result", {})
                final_score = gr.get("final_score", 0.0)
                correctness = gr.get("correctness_score", 0.0)
                reward_value = reward.score

                rewards.append(reward_value)

                # ── [STEP] ─────────────────────────────────────────
                action_str = f"submit_code('{task_id}_step{step}')"
                log_step(
                    step=step,
                    action=action_str,
                    reward=reward_value,
                    done=done,
                    error=None,
                )

                # If incorrect, add feedback for retry
                if correctness < 1.0:
                    user_prompt += (
                        f"\n\n--- Attempt {step} Failed ---\n"
                        f"Your code:\n```python\n{rewritten}\n```\n"
                        f"Feedback: {reward.feedback}\n"
                        f"Please fix and optimize further. Return ONLY code."
                    )
                elif reward_value < 0.01:
                    user_prompt += (
                        f"\n\n--- Attempt {step} No Improvement ---\n"
                        f"Feedback: {reward.feedback}\n"
                        f"Please optimize the logic further."
                    )
                else:
                    done = True  # Good result, stop

            except Exception as exc:
                last_error = str(exc)
                rewards.append(0.01)
                # ── [STEP] on error ────────────────────────────────
                log_step(
                    step=step,
                    action=f"submit_code('{task_id}_step{step}')",
                    reward=0.01,
                    done=False,
                    error=last_error,
                )
                break

        # ── [END] ──────────────────────────────────────────────────
        score = min(max(final_score, 0.01), 0.99)  # clamp to strictly open (0,1), safe at 2dp
        success = score >= SUCCESS_SCORE_THRESHOLD
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

        all_results[task_id] = {
            "task_id": task_id,
            "final_score": final_score,
            "correctness": correctness,
            "success": success,
            "steps": steps_taken,
        }

    # ── Save results to file ───────────────────────────────────────
    total_tasks = len(all_results)
    total_score = sum(r["final_score"] for r in all_results.values())
    avg_score = total_score / total_tasks if total_tasks else 0.0
    correct_count = sum(1 for r in all_results.values() if r.get("correctness", 0) >= 1.0)

    with open("baseline_results.json", "w") as f:
        json.dump({
            "model": MODEL_NAME,
            "average_score": avg_score,
            "success_rate": correct_count / total_tasks if total_tasks else 0.0,
            "tasks": all_results
        }, f, indent=2)


if __name__ == "__main__":
    main()
