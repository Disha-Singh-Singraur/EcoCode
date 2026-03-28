"""Sandboxed code execution engine.

Provides safe, restricted execution of user-submitted Python code:
  - Syntax validation via ast.parse()
  - Strict import blacklist
  - Builtin restrictions (no open, exec, eval, etc.)
  - Timeout enforcement
  - Stdout capture for output comparison
"""

import ast
import sys
import threading
import time
import tracemalloc
from io import StringIO
from typing import Optional

# Modules that are NEVER allowed
IMPORT_BLACKLIST = frozenset({
    "os", "sys", "subprocess", "shutil", "socket", "ctypes",
    "importlib", "pathlib", "io", "tempfile", "signal",
    "threading", "multiprocessing", "pickle", "shelve",
    "http", "urllib", "ftplib", "smtplib", "webbrowser",
    "code", "codeop", "compileall",
})

# Builtins that are removed inside the sandbox
BLOCKED_BUILTINS = frozenset({
    "open", "exec", "eval", "compile", "__import__",
    "getattr", "setattr", "delattr", "globals", "locals",
    "breakpoint", "exit", "quit", "input",
})

DEFAULT_TIMEOUT = 5  # seconds


class ExecutionResult:
    """Result of a sandboxed code execution."""

    def __init__(
        self,
        success: bool,
        output: str = "",
        error: Optional[str] = None,
    ):
        self.success = success
        self.output = output
        self.error = error

    def __repr__(self) -> str:
        return (
            f"ExecutionResult(success={self.success}, "
            f"output={self.output!r}, error={self.error!r})"
        )


# ── Validation helpers ─────────────────────────────────────────────────

def validate_syntax(code: str) -> Optional[str]:
    """Return None if valid Python, otherwise a syntax error string."""
    try:
        ast.parse(code)
        return None
    except SyntaxError as exc:
        return f"SyntaxError: {exc.msg} (line {exc.lineno})"


def _collect_imports(tree: ast.AST) -> list[str]:
    """Walk the AST and collect all imported module names."""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module.split(".")[0])
    return names


def validate_imports(code: str) -> Optional[str]:
    """Return None if no banned imports, otherwise an error string."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None  # syntax errors are caught separately

    for mod_name in _collect_imports(tree):
        if mod_name in IMPORT_BLACKLIST:
            return f"Blocked import: '{mod_name}' is not allowed"
    return None


def validate_code(code: str) -> Optional[str]:
    """Run all validations. Returns None on success, error string on failure."""
    err = validate_syntax(code)
    if err:
        return err
    err = validate_imports(code)
    if err:
        return err
    return None


# ── Sandboxed execution ────────────────────────────────────────────────

def _build_safe_builtins() -> dict:
    """Create a restricted builtins dict."""
    import builtins as _builtins

    safe = {k: v for k, v in vars(_builtins).items() if k not in BLOCKED_BUILTINS}
    # Replace blocked names with a function that raises
    for name in BLOCKED_BUILTINS:
        def _blocked(*_args, _name=name, **_kwargs):
            raise PermissionError(f"'{_name}' is not allowed in sandboxed code")
        safe[name] = _blocked
    return safe


def execute_code(
    code: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> ExecutionResult:
    """Execute code in a restricted sandbox with timeout."""

    # 1. Validate first
    err = validate_code(code)
    if err:
        return ExecutionResult(success=False, error=err)

    # 2. Prepare sandbox globals
    safe_builtins = _build_safe_builtins()
    sandbox_globals = {"__builtins__": safe_builtins}

    # 3. Execute with stdout capture and timeout
    captured_stdout = StringIO()
    result_container: dict = {"success": True, "error": None}

    def _run():
        old_stdout = sys.stdout
        try:
            sys.stdout = captured_stdout
            exec(compile(code, "<sandbox>", "exec"), sandbox_globals)  # noqa: S102
        except Exception as exc:
            result_container["success"] = False
            result_container["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            sys.stdout = old_stdout

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        return ExecutionResult(
            success=False,
            error=f"Execution timed out after {timeout}s",
        )

    return ExecutionResult(
        success=result_container["success"],
        output=captured_stdout.getvalue(),
        error=result_container["error"],
    )


def run_test_case(
    function_code: str,
    test_input: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> ExecutionResult:
    """Execute function code + a test-case call and capture output."""
    full_code = function_code.rstrip("\n") + "\n" + test_input + "\n"
    return execute_code(full_code, timeout=timeout)


class BenchmarkResult:
    def __init__(self, time_avg: Optional[float] = None, memory_peak: Optional[float] = None):
        self.time_avg = time_avg
        self.memory_peak = memory_peak


def run_benchmark(
    function_code: str,
    test_input: str,
    iterations: int = 3,
    timeout: int = 2,
) -> BenchmarkResult:
    """Execute code multiple times to measure average time and peak memory."""
    err = validate_code(function_code)
    if err:
        return BenchmarkResult()

    full_code = function_code.rstrip("\n") + "\n" + test_input + "\n"
    
    import subprocess
    import json
    import os

    runner_path = os.path.join(os.path.dirname(__file__), "runner.py")
    
    try:
        proc = subprocess.run(
            [sys.executable, runner_path, str(iterations), full_code],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            # Parse the last line in case stdout got dirtied
            data = json.loads(proc.stdout.strip().split("\n")[-1])
            if "error" not in data:
                return BenchmarkResult(time_avg=data.get("time"), memory_peak=data.get("memory"))
    except Exception:
        pass

    return BenchmarkResult()
