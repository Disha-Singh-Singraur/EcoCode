"""AST-based proxy analysis for code quality metrics.

Fully deterministic — no runtime benchmarking. Analyses the code's
abstract syntax tree to estimate optimization quality.
"""

import ast
from typing import Any, Dict

# Scores must be strictly within (0, 1) per validator
_SCORE_MIN = 0.001
_SCORE_MAX = 0.999


# Builtins / methods that indicate good Python style
EFFICIENT_BUILTINS = frozenset({
    "sum", "map", "filter", "sorted", "enumerate",
    "zip", "any", "all", "min", "max", "len",
})

EFFICIENT_STR_METHODS = frozenset({
    "join", "capitalize", "title", "upper", "lower",
    "strip", "replace", "split",
})


def analyze_code(code: str) -> Dict[str, Any]:
    """Analyse Python source and return deterministic proxy metrics.

    Returns a dict with:
        - loop_count: number of for/while loops
        - max_nesting_depth: deepest loop nesting
        - list_comprehension_count: number of list/set/dict comprehensions
        - generator_expression_count: number of genexprs
        - builtin_usage_count: uses of efficient builtins
        - str_method_count: uses of efficient string methods
        - redundant_variable_count: estimated unused/trivial assignments
        - total_lines: non-blank source lines
        - has_index_loop: True if `range(len(...))` pattern detected
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return _empty_analysis()

    metrics: Dict[str, Any] = {
        "loop_count": 0,
        "max_nesting_depth": 0,
        "list_comprehension_count": 0,
        "generator_expression_count": 0,
        "builtin_usage_count": 0,
        "str_method_count": 0,
        "redundant_variable_count": 0,
        "total_lines": _count_lines(code),
        "has_index_loop": False,
    }

    _walk(tree, metrics, depth=0)
    metrics["redundant_variable_count"] = _count_redundant_vars(tree)
    return metrics


def _empty_analysis() -> Dict[str, Any]:
    return {
        "loop_count": 0,
        "max_nesting_depth": 0,
        "list_comprehension_count": 0,
        "generator_expression_count": 0,
        "builtin_usage_count": 0,
        "str_method_count": 0,
        "redundant_variable_count": 0,
        "total_lines": 0,
        "has_index_loop": False,
    }


def _count_lines(code: str) -> int:
    return sum(1 for line in code.splitlines() if line.strip())


def _walk(node: ast.AST, metrics: Dict[str, Any], depth: int) -> None:
    """Recursive AST walk tracking nesting depth."""
    if isinstance(node, (ast.For, ast.While)):
        metrics["loop_count"] += 1
        new_depth = depth + 1
        metrics["max_nesting_depth"] = max(metrics["max_nesting_depth"], new_depth)

        # Detect range(len(...)) pattern
        if isinstance(node, ast.For) and _is_range_len(node.iter):
            metrics["has_index_loop"] = True

        for child in ast.iter_child_nodes(node):
            _walk(child, metrics, new_depth)
        return

    if isinstance(node, ast.ListComp):
        metrics["list_comprehension_count"] += 1
    elif isinstance(node, (ast.SetComp, ast.DictComp)):
        metrics["list_comprehension_count"] += 1
    elif isinstance(node, ast.GeneratorExp):
        metrics["generator_expression_count"] += 1

    # Detect efficient builtin calls
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in EFFICIENT_BUILTINS:
            metrics["builtin_usage_count"] += 1
        # Detect str method calls like ",".join(...)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in EFFICIENT_STR_METHODS:
                metrics["str_method_count"] += 1

    for child in ast.iter_child_nodes(node):
        _walk(child, metrics, depth)


def _is_range_len(node: ast.AST) -> bool:
    """Detect `range(len(...))` pattern."""
    if not isinstance(node, ast.Call):
        return False
    if not (isinstance(node.func, ast.Name) and node.func.id == "range"):
        return False
    if len(node.args) != 1:
        return False
    arg = node.args[0]
    return (
        isinstance(arg, ast.Call)
        and isinstance(arg.func, ast.Name)
        and arg.func.id == "len"
    )


def _count_redundant_vars(tree: ast.AST) -> int:
    """Heuristic: count variables assigned but only read once or never."""
    assignments: Dict[str, int] = {}
    reads: Dict[str, int] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = assignments.get(target.id, 0) + 1
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            reads[node.id] = reads.get(node.id, 0) + 1

    # A variable is "redundant" if it is assigned but read ≤ 1 time
    # and is not the function name or 'return' target
    redundant = 0
    for var, assign_count in assignments.items():
        read_count = reads.get(var, 0)
        if assign_count >= 1 and read_count <= 1:
            redundant += 1
    return redundant


def compute_improvement_score(
    original_metrics: Dict[str, Any],
    new_metrics: Dict[str, Any],
) -> float:
    """Compute a 0.0–1.0 score comparing new code against original.

    Higher = better optimization. Fully deterministic.
    """
    score = 0.0
    max_possible = 0.0

    # 1. Reduced loop count (weight 0.20)
    max_possible += 0.20
    orig_loops = original_metrics["loop_count"]
    new_loops = new_metrics["loop_count"]
    if orig_loops > 0 and new_loops < orig_loops:
        score += 0.20 * (1.0 - new_loops / orig_loops)

    # 2. Reduced nesting depth (weight 0.15)
    max_possible += 0.15
    orig_depth = original_metrics["max_nesting_depth"]
    new_depth = new_metrics["max_nesting_depth"]
    if orig_depth > 0 and new_depth < orig_depth:
        score += 0.15 * (1.0 - new_depth / orig_depth)

    # 3. Use of comprehensions (weight 0.15)
    max_possible += 0.15
    if new_metrics["list_comprehension_count"] > original_metrics["list_comprehension_count"]:
        score += 0.15
    if new_metrics["generator_expression_count"] > original_metrics["generator_expression_count"]:
        score += 0.05
        max_possible += 0.05

    # 4. Use of efficient builtins (weight 0.20)
    max_possible += 0.20
    if new_metrics["builtin_usage_count"] > original_metrics["builtin_usage_count"]:
        gained = new_metrics["builtin_usage_count"] - original_metrics["builtin_usage_count"]
        score += min(0.20, 0.05 * gained)

    # 5. Use of efficient string methods (weight 0.10)
    max_possible += 0.10
    if new_metrics["str_method_count"] > original_metrics["str_method_count"]:
        score += 0.10

    # 6. Removed index-based loops (weight 0.10)
    max_possible += 0.10
    if original_metrics["has_index_loop"] and not new_metrics["has_index_loop"]:
        score += 0.10

    # 7. Reduced redundant variables (weight 0.10)
    max_possible += 0.10
    orig_red = original_metrics["redundant_variable_count"]
    new_red = new_metrics["redundant_variable_count"]
    if orig_red > 0 and new_red < orig_red:
        score += 0.10 * (1.0 - new_red / orig_red)

    # Normalize to strictly (0, 1) per validator requirement
    if max_possible > 0:
        raw = min(1.0, score / max_possible * 1.25)  # slight scale factor
        return max(_SCORE_MIN, min(_SCORE_MAX, raw))
    return _SCORE_MIN


def metrics_are_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Check if two metric dicts are identical (for plateau detection)."""
    keys = [
        "loop_count", "max_nesting_depth", "list_comprehension_count",
        "generator_expression_count", "builtin_usage_count",
        "str_method_count", "redundant_variable_count", "has_index_loop",
    ]
    return all(a.get(k) == b.get(k) for k in keys)
