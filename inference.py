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
"""

import os
import json
import re
import textwrap
from typing import List, Optional, Dict

from openai import OpenAI
from env.environment import EcoCodeEnv
from models.schemas import Action
from tasks.definitions import list_task_ids

# ── Environment Variables ──────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

# ── Configuration ──────────────────────────────────────────────────
MAX_STEPS = 3
TEMPERATURE = 0.0  # Deterministic for baseline
MAX_TOKENS = 1024

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


def main() -> None:
    if not API_KEY:
        print("Error: HF_TOKEN or API_KEY environment variable not set.")
        return

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env = EcoCodeEnv()
    
    results = {}
    correct_count = 0
    total_tasks = 0

    print("=" * 60)
    print("EcoCode Inference Execution")
    print(f"Model: {MODEL_NAME}")
    print(f"Endpoint: {API_BASE_URL}")
    print("=" * 60)

    for task_id in list_task_ids():
        total_tasks += 1
        obs = env.reset(task_id=task_id)
        
        print(f"\n[Task] {task_id} ({obs.difficulty})")
        user_prompt = build_user_prompt(obs)
        
        done = False
        step_count = 0
        final_score = 0.0
        correctness = 0.0
        optimization = 0.0
        reward_value = 0.0

        while not done and step_count < MAX_STEPS:
            step_count += 1
            print(f"  Step {step_count}...")
            
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
                optimization = gr.get("optimization_score", 0.0)
                reward_value = reward.score
                
                if correctness < 1.0:
                    print(f"    Failed correctness. Feedback: {reward.feedback}")
                    user_prompt += (
                        f"\n\n--- Attempt {step_count} Failed ---\n"
                        f"Your code:\n```python\n{rewritten}\n```\n"
                        f"Feedback: {reward.feedback}\n"
                        f"Please fix and optimize further. Return ONLY code."
                    )
                elif reward_value < 0.01:
                    print(f"    No improvement. Feedback: {reward.feedback}")
                    user_prompt += (
                        f"\n\n--- Attempt {step_count} No Improvement ---\n"
                        f"Feedback: {reward.feedback}\n"
                        f"Please optimize the logic further."
                    )
                else:
                    print(f"    Success! Score: {final_score:.3f}")
                    break
            except Exception as exc:
                print(f"    Error: {exc}")
                break

        if correctness >= 1.0:
            correct_count += 1

        results[task_id] = {
            "task_id": task_id,
            "final_score": final_score,
            "correctness": correctness,
            "optimization": optimization,
        }

    # ── Summary ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    total_score = sum(r["final_score"] for r in results.values())
    avg_score = total_score / total_tasks if total_tasks else 0.0
    success_rate = correct_count / total_tasks if total_tasks else 0.0
    
    print(f"Average Score: {avg_score:.3f}")
    print(f"Success Rate:  {success_rate:.0%} ({correct_count}/{total_tasks})")
    print("=" * 60)

    # Save to baseline_results.json for reproduction check
    with open("baseline_results.json", "w") as f:
        json.dump({
            "model": MODEL_NAME,
            "average_score": avg_score,
            "success_rate": success_rate,
            "tasks": results
        }, f, indent=2)


if __name__ == "__main__":
    main()
