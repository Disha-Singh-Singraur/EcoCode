"""End-to-end test for the EcoCode environment."""

from env.environment import EcoCodeEnv
from models.schemas import Action
from grader.grader import Grader
from tasks.definitions import list_task_ids

def test_full_pipeline():
    env = EcoCodeEnv()

    # Test 1: Reset loop_sum
    obs = env.reset("loop_sum")
    print(f"[PASS] Reset: difficulty={obs.difficulty}, steps={obs.step_count}, tests={len(obs.test_cases)}")

    # Test 2: Submit optimized code
    optimized = "def compute_sum(numbers):\n    return sum(numbers)\n"
    action = Action(rewritten_code=optimized)
    obs2, reward, done, info = env.step(action)
    print(f"[PASS] Step: reward={reward.score}, done={done}")
    print(f"  Breakdown: corr={reward.breakdown.correctness}, opt={reward.breakdown.optimization}, pen={reward.breakdown.penalty}")
    gr = info.get("grader_result", {})
    print(f"  Grader: correctness={gr.get('correctness_score')}, optimization={gr.get('optimization_score')}, final={gr.get('final_score')}")
    if "termination_reason" in info:
        print(f"  Terminated: {info['termination_reason']}")

    # Test 3: State
    state = env.state()
    print(f"[PASS] State: task={state.task_id}, steps={state.step_count}, done={state.done}")

    # Test 4: Grader standalone
    grader = Grader()
    from tasks.definitions import TASKS
    task = TASKS["loop_sum"]
    result = grader.grade(task["dirty_code"], optimized, task["test_cases"])
    print(f"[PASS] Grader: correctness={result.correctness_score}, opt={result.optimization_score}, final={result.final_score}")
    print(f"  Details: {result.details}")

    # Test 5: All tasks can reset
    for tid in list_task_ids():
        obs = env.reset(tid)
        print(f"[PASS] Task '{tid}' resets OK: difficulty={obs.difficulty}")

    # Test 6: Invalid code penalty
    env.reset("loop_sum")
    bad = Action(rewritten_code="import os\nos.system('rm -rf /')\n")
    obs_bad, rew_bad, done_bad, info_bad = env.step(bad)
    print(f"[PASS] Invalid code: reward={rew_bad.score}, state_unchanged={info_bad.get('state_unchanged')}")

    # Test 7: Incorrect output penalty
    env.reset("loop_sum")
    wrong = Action(rewritten_code="def compute_sum(numbers):\n    return 999\n")
    obs_wrong, rew_wrong, done_wrong, info_wrong = env.step(wrong)
    print(f"[PASS] Incorrect output: reward={rew_wrong.score}")

    print("\n=== ALL TESTS PASSED ===")


if __name__ == "__main__":
    test_full_pipeline()
