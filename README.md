---
title: EcoCode
emoji: 🌱
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
---
# 🌱 EcoCode: Green Code Optimization Environment

An OpenEnv-compatible interactive environment where an AI agent receives inefficient ("dirty") Python code and iteratively refactors it to improve efficiency (time and memory) while preserving exact output correctness.

EcoCode is not just a coding tool — it is an evaluation environment for training and benchmarking AI agents to write efficient, energy-aware code.

---

## 🎯 Motivation

Inefficient code wastes compute resources and energy. EcoCode gamifies code optimization — an AI agent learns to write cleaner, faster, more Pythonic code through multi-step interaction with deterministic feedback. Every optimization saves energy. **Green code is better code.**

This environment can be used to train next-generation coding agents that optimize software for performance and sustainability at scale.

---

## 🏗️ Project Structure

```
EcoCode/
├── env/
│   ├── environment.py       # OpenEnv interface (reset, step, state)
│   └── reward.py            # Trajectory-based reward function
├── models/
│   └── schemas.py           # Pydantic models (Observation, Action, Reward, etc.)
├── tasks/
│   ├── definitions.py       # Task definitions (easy → hard)
│   └── task_registry.py     # Task discovery registry
├── grader/
│   └── grader.py            # Deterministic grader (0.0–1.0)
├── utils/
│   ├── sandbox.py           # Sandboxed code execution
│   └── code_analysis.py     # AST-based proxy metrics
├── scripts/
│   └── baseline.py          # Hybrid baseline agent (API + fallback)
├── server.py                # FastAPI server
├── openenv.yaml             # OpenEnv metadata
├── Dockerfile               # Docker deployment
├── requirements.txt         # Python dependencies
└── README.md
```

---

## 🧩 How It Works

*EcoCode uses deterministic AST-based grading as the primary signal, with optional runtime benchmarking for analysis and future extensions.*
*Carbon estimates are derived as a proxy from execution time and memory usage to simulate environmental impact of optimizations.*

EcoCode follows the **Observation → Action → Reward** loop:

### Observation
The agent receives the current state of the code along with test cases:

| Field | Type | Description |
|-------|------|-------------|
| `current_code` | string | Current version of the code |
| `original_code` | string | Original inefficient code |
| `test_cases` | list | `{input, expected_output}` pairs |
| `difficulty` | string | `easy`, `medium`, or `hard` |
| `step_count` | int | Current step in the episode |

### Action
The agent submits optimized code:

| Field | Type | Description |
|-------|------|-------------|
| `rewritten_code` | string | Agent's improved version of the code |

### Reward
The environment evaluates the submission and returns a reward signal:

| Condition | Reward |
|-----------|--------|
| Correct + significantly improved | +0.5 to +1.0 |
| Correct + partial improvement | +0.2 to +0.5 |
| Correct but no improvement | −0.05 |
| Incorrect output | −1.0 |
| Invalid / unsafe code | −0.5 |

The agent can iterate for up to **5 steps** per episode. Episodes end early if a near-optimal score (≥ 0.95) is reached or no further AST improvements are detected. Episodes terminate immediately on invalid or unsafe code submissions.

---

## 🧪 Tasks

| ID | Difficulty | Description |
|----|-----------|-------------|
| `loop_sum` | Easy | Replace loop-based sum with `sum()` builtin |
| `nested_search` | Medium | Replace nested O(n²) search with set operations |
| `string_builder` | Medium | Replace string concatenation with `str.join()` |
| `dictionary_frequency` | Medium | Replace nested-loop frequency counting with dict |
| `generator_vs_list` | Medium | Use generator expression instead of list comprehension |
| `combined_opts` | Hard | Multiple combined optimizations |
| `fibonacci_memoization` | Hard | Use memoization for exponential recursion |
| `loop_invariant_motion` | Hard | Move constant computation outside loops |
| `math_simplification` | Medium | Replace loop with O(1) Gaussian formula |
| `any_builtin` | Easy | Use `any()` builtin instead of search loop |
| `all_builtin` | Easy | Use `all()` builtin instead of search loop |
| `enumerate_builtin` | Easy | Use `enumerate()` instead of `range(len())` |
| `zip_builtin` | Medium | Use `zip()` for parallel list iteration |
| `max_builtin` | Easy | Use `max()` instead of tracking highest value |
| `filter_builtin` | Medium | Use `filter()` or comprehension for conditional append |

---

## 🔍 Example Optimization

### Before (Dirty Code)
```python
def compute_sum(numbers):
    total = 0
    temp = 0
    for i in range(len(numbers)):
        temp = numbers[i]
        total = total + temp
    result = total
    return result
```

### After (Optimized)
```python
def compute_sum(numbers):
    return sum(numbers)
```

### Result
- ✅ **Correctness**: Passed all 4 test cases
- 📈 **Optimization**: Significant improvement detected (removed loops, used builtin)
- ⏱️ **Time**: 0.05s → 0.01s
- 💾 **Memory**: 2.0MB → 0.5MB
- 🌱 **Carbon**: 0.025g → 0.005g
- 🏆 **Score**: 0.812

---

## 🎯 Grading System

Deterministic grader returning structured `GraderResult`:

| Component | Range | Description |
|-----------|-------|-------------|
| `correctness_score` | 0 or 1 | Binary — all tests must pass |
| `optimization_score` | 0.0–1.0 | AST-based improvement metrics |
| `penalty` | 0.0–0.5 | No improvement or invalid code |
| `final_score` | 0.0–1.0 | Combined weighted score |

**Proxy metrics** (no runtime benchmarking): loop reduction, nesting depth, builtin usage, comprehensions, string methods, redundant variable removal, `range(len(...))` elimination.

---

## 📊 Baseline Results (Deterministic Agent)

```
Task                    Difficulty  Score      Correct
───────────────────────────────────────────────────────
loop_sum                easy        0.813      ✅
nested_search           medium      0.813      ✅
string_builder          medium      0.757      ✅
dictionary_frequency    medium      0.818      ✅
generator_vs_list       medium      0.436      ✅
combined_opts           hard        0.798      ✅
fibonacci_memoization   hard        0.300      ✅
loop_invariant_motion   hard        0.775      ✅
math_simplification     medium      0.725      ✅
any_builtin             easy        0.815      ✅
all_builtin             easy        0.815      ✅
enumerate_builtin       easy        0.815      ✅
zip_builtin             medium      0.815      ✅
max_builtin             easy        0.815      ✅
filter_builtin          medium      0.815      ✅
───────────────────────────────────────────────────────
Average Score:       0.741
Success Rate:        100% (15/15)
```

Results are fully reproducible — the deterministic fallback agent uses rule-based optimal solutions with no randomness. Hard tasks intentionally score lower to challenge frontier models.

---

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reset` | POST | Reset with `task_id`, returns `Observation` |
| `/step` | POST | Submit `rewritten_code`, returns `Observation` + `Reward` + `done` |
| `/state` | GET | Current environment state |
| `/tasks` | GET | Task metadata with sample observations |
| `/grader` | POST | Grade submission with full breakdown |
| `/baseline` | POST | Run baseline evaluation |

### Quick API Examples

```bash
# List tasks
curl http://localhost:7860/tasks

# Reset environment
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "loop_sum"}'

# Submit optimized code
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"rewritten_code": "def compute_sum(numbers):\n    return sum(numbers)\n"}'

# Grade a submission directly
curl -X POST http://localhost:7860/grader \
  -H "Content-Type: application/json" \
  -d '{"task_id": "loop_sum", "rewritten_code": "def compute_sum(numbers):\n    return sum(numbers)\n"}'
```

---

## 🚀 Setup & Running

### Local Development
```bash
pip install -r requirements.txt
python server.py
# → http://localhost:7860
```

### Run Baseline
```bash
# Deterministic fallback (no API key needed)
python -m scripts.baseline

# With OpenAI API (deterministic, temperature=0)
export OPENAI_API_KEY="sk-..."
python -m scripts.baseline
```

### Docker
```bash
docker build -t ecocode .
docker run -p 7860:7860 ecocode
```

Compatible with **Hugging Face Spaces** Docker runtime.

---

## 🔒 Security

- **Import blacklist**: `os`, `sys`, `subprocess`, `shutil`, `socket`, `ctypes`, and 14+ more
- **Blocked builtins**: `open`, `exec`, `eval`, `compile`, `__import__`, etc.
- **Execution timeout**: 5 seconds per run
- **No file I/O** allowed inside sandbox

---

## 🔁 Reproducibility

- All grading is **deterministic** (AST-based, no runtime benchmarking)
- Baseline uses `temperature=0` with fixed prompts (API mode)
- Fallback mode uses hardcoded optimal solutions
- **No randomness** in any component
