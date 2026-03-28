"""Subprocess runner for isolated benchmarking."""

import sys
import time
import tracemalloc
import json
from io import StringIO
import builtins

# Blocked builtins from sandbox.py
BLOCKED_BUILTINS = frozenset({
    "open", "exec", "eval", "compile", "__import__",
    "getattr", "setattr", "delattr", "globals", "locals",
    "breakpoint", "exit", "quit", "input",
})

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
        
    iterations = int(sys.argv[1])
    code = sys.argv[2]
    
    # 1. Build safe builtins inside the subprocess
    safe_builtins = {k: v for k, v in vars(builtins).items() if k not in BLOCKED_BUILTINS}
    for name in BLOCKED_BUILTINS:
        def _blocked(*_args, _name=name, **_kwargs):
            raise PermissionError(f"'{_name}' is not allowed in sandboxed code")
        safe_builtins[name] = _blocked
        
    sandbox_globals = {"__builtins__": safe_builtins}
    
    try:
        compiled = compile(code, "<sandbox>", "exec")
        
        # 2. Silently capture stdout during execution
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        # --- Time Benchmark ---
        def measure_time(compiled_code, globals_dict):
            import time
            runs = 50
            start = time.perf_counter()
            for _ in range(runs):
                exec(compiled_code, globals_dict)
            end = time.perf_counter()
            return (end - start) / runs
            
        time_avg = measure_time(compiled, sandbox_globals)
        
        # --- Memory Benchmark ---
        tracemalloc.start()
        exec(compiled, sandbox_globals)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # 3. Restore stdout to print JSON result back to main process
        sys.stdout = old_stdout
        print(json.dumps({"time": time_avg, "memory": peak}))
        
    except Exception as e:
        sys.stdout = sys.__stdout__
        print(json.dumps({"error": str(e)}))

if __name__ == "__main__":
    main()
