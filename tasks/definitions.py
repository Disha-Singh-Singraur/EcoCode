"""Task definitions for the EcoCode environment.

Each task contains:
  - id: unique identifier
  - description: what to optimize
  - difficulty: easy/medium/hard
  - dirty_code: the inefficient code to optimize
  - test_cases: list of (input, expected_output) pairs
  - expected_patterns: AST patterns to look for in optimized code
"""

TASKS = {
    # ──────────────────────────────────────────────────────────────────────
    # EASY: Loop-based sum → builtin sum()
    # ──────────────────────────────────────────────────────────────────────
    "loop_sum": {
        "id": "loop_sum",
        "description": (
            "Optimize a function that computes the sum of a list using a "
            "manual for-loop and redundant variables. Replace with Python "
            "builtins and remove unnecessary code."
        ),
        "difficulty": "easy",
        "dirty_code": (
            "def compute_sum(numbers):\n"
            "    total = 0\n"
            "    temp = 0\n"
            "    for i in range(len(numbers)):\n"
            "        temp = numbers[i]\n"
            "        total = total + temp\n"
            "    result = total\n"
            "    return result\n"
        ),
        "test_cases": [
            {"input": "print(compute_sum(list(range(10000))))", "expected_output": "49995000"},
            {"input": "print(compute_sum([]))", "expected_output": "0"},
            {"input": "print(compute_sum([10, -5, 3]))", "expected_output": "8"},
            {"input": "print(compute_sum([100]))", "expected_output": "100"},
        ],
        "expected_patterns": ["use_builtin_sum", "remove_redundant_vars", "remove_index_loop"],
    },

    # ──────────────────────────────────────────────────────────────────────
    # MEDIUM: Nested loop search → set lookup
    # ──────────────────────────────────────────────────────────────────────
    "nested_search": {
        "id": "nested_search",
        "description": (
            "Optimize a function that finds common elements between two "
            "lists using nested loops (O(n²)). Use set intersection for "
            "O(n) complexity."
        ),
        "difficulty": "medium",
        "dirty_code": (
            "def find_common(list_a, list_b):\n"
            "    common = []\n"
            "    for i in range(len(list_a)):\n"
            "        for j in range(len(list_b)):\n"
            "            if list_a[i] == list_b[j]:\n"
            "                found = True\n"
            "                if list_a[i] not in common:\n"
            "                    common.append(list_a[i])\n"
            "    result = common\n"
            "    return result\n"
        ),
        "test_cases": [
            {
                "input": "print(len(find_common(list(range(2000)), list(range(1000, 3000)))))",
                "expected_output": "1000",
            },
            {
                "input": "print(sorted(find_common([], [1, 2, 3])))",
                "expected_output": "[]",
            },
            {
                "input": "print(sorted(find_common([1, 2], [3, 4])))",
                "expected_output": "[]",
            },
            {
                "input": "print(sorted(find_common([5, 5, 6], [5, 6, 6])))",
                "expected_output": "[5, 6]",
            },
        ],
        "expected_patterns": ["use_set_operations", "remove_nested_loops", "remove_redundant_vars"],
    },

    # ──────────────────────────────────────────────────────────────────────
    # MEDIUM: String concatenation → join()
    # ──────────────────────────────────────────────────────────────────────
    "string_builder": {
        "id": "string_builder",
        "description": (
            "Optimize a function that builds a formatted string using "
            "repeated string concatenation in a loop. Use str.join() and "
            "list comprehension for efficient string building."
        ),
        "difficulty": "medium",
        "dirty_code": (
            "def format_words(words):\n"
            "    result = ''\n"
            "    for i in range(len(words)):\n"
            "        word = words[i]\n"
            "        upper_word = ''\n"
            "        for j in range(len(word)):\n"
            "            if j == 0:\n"
            "                upper_word = upper_word + word[j].upper()\n"
            "            else:\n"
            "                upper_word = upper_word + word[j].lower()\n"
            "        if i < len(words) - 1:\n"
            "            result = result + upper_word + ', '\n"
            "        else:\n"
            "            result = result + upper_word\n"
            "    return result\n"
        ),
        "test_cases": [
            {
                "input": "print(len(format_words(['a'] * 5000)))",
                "expected_output": "14998",
            },
            {
                "input": "print(format_words(['TEST']))",
                "expected_output": "Test",
            },
            {
                "input": "print(format_words([]))",
                "expected_output": "",
            },
            {
                "input": "print(format_words(['a', 'b', 'c']))",
                "expected_output": "A, B, C",
            },
        ],
        "expected_patterns": ["use_str_join", "use_str_methods", "use_list_comprehension"],
    },

    # ──────────────────────────────────────────────────────────────────────
    # HARD: Multiple combined inefficiencies
    # ──────────────────────────────────────────────────────────────────────
    "combined_opts": {
        "id": "combined_opts",
        "description": (
            "Optimize a function with multiple inefficiencies: O(n²) "
            "duplicate checking, manual counting, redundant variables, and "
            "non-Pythonic constructs. Apply combined optimizations."
        ),
        "difficulty": "hard",
        "dirty_code": (
            "def analyze_numbers(numbers):\n"
            "    unique = []\n"
            "    for i in range(len(numbers)):\n"
            "        is_dup = False\n"
            "        for j in range(len(unique)):\n"
            "            if numbers[i] == unique[j]:\n"
            "                is_dup = True\n"
            "        if is_dup == False:\n"
            "            unique.append(numbers[i])\n"
            "    \n"
            "    total = 0\n"
            "    count = 0\n"
            "    for i in range(len(unique)):\n"
            "        total = total + unique[i]\n"
            "        count = count + 1\n"
            "    \n"
            "    if count == 0:\n"
            "        avg = 0\n"
            "    else:\n"
            "        avg = total / count\n"
            "    \n"
            "    sorted_unique = []\n"
            "    temp_list = []\n"
            "    for i in range(len(unique)):\n"
            "        temp_list.append(unique[i])\n"
            "    for i in range(len(temp_list)):\n"
            "        for j in range(i + 1, len(temp_list)):\n"
            "            if temp_list[i] > temp_list[j]:\n"
            "                tmp = temp_list[i]\n"
            "                temp_list[i] = temp_list[j]\n"
            "                temp_list[j] = tmp\n"
            "    sorted_unique = temp_list\n"
            "    \n"
            "    result = str(len(unique)) + ':' + str(avg) + ':' + str(sorted_unique)\n"
            "    return result\n"
        ),
        "test_cases": [
            {
                "input": "print(analyze_numbers([3, 1, 2, 3, 1]))",
                "expected_output": "3:2.0:[1, 2, 3]",
            },
            {
                "input": "print(analyze_numbers([]))",
                "expected_output": "0:0:[]",
            },
            {
                "input": "print(analyze_numbers([5]))",
                "expected_output": "1:5.0:[5]",
            },
            {
                "input": "print(analyze_numbers([4, 4, 4, 4]))",
                "expected_output": "1:4.0:[4]",
            },
        ],
        "expected_patterns": [
            "use_set_for_dedup",
            "use_builtin_sum",
            "use_builtin_len",
            "use_builtin_sorted",
            "remove_nested_loops",
            "remove_redundant_vars",
            "use_fstring_or_join",
        ],
    },

    # ──────────────────────────────────────────────────────────────────────
    # MEDIUM: Dictionary frequency counting
    # ──────────────────────────────────────────────────────────────────────
    "dictionary_frequency": {
        "id": "dictionary_frequency",
        "description": (
            "Optimize a function that counts the frequency of elements in "
            "a list using nested loops and manual comparison. Replace with "
            "dictionary-based counting for O(n) complexity."
        ),
        "difficulty": "medium",
        "dirty_code": (
            "def count_freq(items):\n"
            "    unique_items = []\n"
            "    for i in range(len(items)):\n"
            "        found = False\n"
            "        for j in range(len(unique_items)):\n"
            "            if items[i] == unique_items[j]:\n"
            "                found = True\n"
            "        if found == False:\n"
            "            unique_items.append(items[i])\n"
            "    \n"
            "    result = []\n"
            "    for i in range(len(unique_items)):\n"
            "        count = 0\n"
            "        for j in range(len(items)):\n"
            "            if items[j] == unique_items[i]:\n"
            "                count = count + 1\n"
            "        pair = str(unique_items[i]) + ':' + str(count)\n"
            "        result.append(pair)\n"
            "    \n"
            "    output = ''\n"
            "    for i in range(len(result)):\n"
            "        if i < len(result) - 1:\n"
            "            output = output + result[i] + ', '\n"
            "        else:\n"
            "            output = output + result[i]\n"
            "    return output\n"
        ),
        "test_cases": [
            {
                "input": "print(count_freq(['a', 'b', 'a', 'c', 'b', 'a']))",
                "expected_output": "a:3, b:2, c:1",
            },
            {
                "input": "print(count_freq([]))",
                "expected_output": "",
            },
            {
                "input": "print(count_freq(['x']))",
                "expected_output": "x:1",
            },
            {
                "input": "print(count_freq([1, 2, 2, 3, 3, 3]))",
                "expected_output": "1:1, 2:2, 3:3",
            },
        ],
        "expected_patterns": [
            "use_dict_counting",
            "remove_nested_loops",
            "use_str_join",
            "remove_redundant_vars",
        ],
    },

    # ──────────────────────────────────────────────────────────────────────
    # MEDIUM: List comprehension -> Generator expression
    # ──────────────────────────────────────────────────────────────────────
    "generator_vs_list": {
        "id": "generator_vs_list",
        "description": (
            "Optimize a function that builds a large list in memory using "
            "a list comprehension. Replace it with a generator expression "
            "to save memory."
        ),
        "difficulty": "medium",
        "dirty_code": (
            "def process_data(limit):\n"
            "    data = [x * 2 for x in range(limit)]\n"
            "    return sum(data)\n"
        ),
        "test_cases": [
            {"input": "print(process_data(10))", "expected_output": "90"},
            {"input": "print(process_data(100))", "expected_output": "9900"},
            {"input": "print(process_data(0))", "expected_output": "0"},
            {"input": "print(process_data(1000))", "expected_output": "999000"},
        ],
        "expected_patterns": ["use_generator_expression"],
    },

    # ──────────────────────────────────────────────────────────────────────
    # HARD: Recursive Fibonacci -> Memoization
    # ──────────────────────────────────────────────────────────────────────
    "fibonacci_memoization": {
        "id": "fibonacci_memoization",
        "description": (
            "Optimize a function that computes the nth Fibonacci number "
            "using naive recursion (exponential time). Use memoization "
            "(dict or functools.lru_cache) to achieve linear time."
        ),
        "difficulty": "hard",
        "dirty_code": (
            "def fibonacci(n):\n"
            "    if n <= 1:\n"
            "        return n\n"
            "    return fibonacci(n - 1) + fibonacci(n - 2)\n"
        ),
        "test_cases": [
            {"input": "print(fibonacci(30))", "expected_output": "832040"},
            {"input": "print(fibonacci(10))", "expected_output": "55"},
            {"input": "print(fibonacci(0))", "expected_output": "0"},
            {"input": "print(fibonacci(1))", "expected_output": "1"},
        ],
        "expected_patterns": ["use_memoization", "use_lru_cache"],
    },

    # ──────────────────────────────────────────────────────────────────────
    # HARD: Loop Invariant Code Motion
    # ──────────────────────────────────────────────────────────────────────
    "loop_invariant_motion": {
        "id": "loop_invariant_motion",
        "description": (
            "Optimize code where constant computation is unnecessarily "
            "repeated inside loops. Move the invariant computation outside "
            "the loop."
        ),
        "difficulty": "hard",
        "dirty_code": (
            "def process_transactions(transactions, settings_str):\n"
            "    results = []\n"
            "    for t in transactions:\n"
            "        # Expensive parsing inside loop\n"
            "        multiplier = int(settings_str.split(':')[1])\n"
            "        base_fee = float(settings_str.split(':')[2])\n"
            "        results.append(t * multiplier + base_fee)\n"
            "    return results\n"
        ),
        "test_cases": [
            {
                "input": "print(process_transactions([10, 20, 30], 'config:2:1.5'))",
                "expected_output": "[21.5, 41.5, 61.5]"
            },
            {
                "input": "print(process_transactions([], 'config:5:0.0'))",
                "expected_output": "[]"
            },
            {
                "input": "print(process_transactions([100], 'cfg:10:5.0'))",
                "expected_output": "[1005.0]"
            },
        ],
        "expected_patterns": ["remove_redundant_vars"],
    },

    # ──────────────────────────────────────────────────────────────────────
    # MEDIUM: O(N) Loop Sum -> O(1) Gaussian Sum
    # ──────────────────────────────────────────────────────────────────────
    "math_simplification": {
        "id": "math_simplification",
        "description": (
            "Optimize a function that computes the sum of integers from 1 to N "
            "using an O(N) for-loop. Replace with the O(1) Gaussian sum formula."
        ),
        "difficulty": "medium",
        "dirty_code": (
            "def sum_to_n(n):\n"
            "    total = 0\n"
            "    for i in range(1, n + 1):\n"
            "        total = total + i\n"
            "    return total\n"
        ),
        "test_cases": [
            {"input": "print(sum_to_n(100000))", "expected_output": "5000050000"},
            {"input": "print(sum_to_n(10))", "expected_output": "55"},
            {"input": "print(sum_to_n(0))", "expected_output": "0"},
            {"input": "print(sum_to_n(1))", "expected_output": "1"},
        ],
        "expected_patterns": ["remove_redundant_vars", "remove_nested_loops"],
    },

    # ──────────────────────────────────────────────────────────────────────
    # EASY: For Loop Search -> any() builtin
    # ──────────────────────────────────────────────────────────────────────
    "any_builtin": {
        "id": "any_builtin",
        "description": "Optimize a loop that checks if any element in a list meets a condition. Use the any() builtin.",
        "difficulty": "easy",
        "dirty_code": (
            "def contains_positive(numbers):\n"
            "    found = False\n"
            "    for i in range(len(numbers)):\n"
            "        if numbers[i] > 0:\n"
            "            found = True\n"
            "            break\n"
            "    return found\n"
        ),
        "test_cases": [
            {"input": "print(contains_positive([-10, -5, 0, 1]))", "expected_output": "True"},
            {"input": "print(contains_positive([-1, -2, -3]))", "expected_output": "False"},
            {"input": "print(contains_positive([]))", "expected_output": "False"},
            {"input": "print(contains_positive(list(range(-5000, 5001))))", "expected_output": "True"},
        ],
        "expected_patterns": ["use_builtin_any", "remove_index_loop"],
    },

    # ──────────────────────────────────────────────────────────────────────
    # EASY: For Loop Search -> all() builtin
    # ──────────────────────────────────────────────────────────────────────
    "all_builtin": {
        "id": "all_builtin",
        "description": "Optimize a loop that checks if all elements in a list meet a condition. Use the all() builtin.",
        "difficulty": "easy",
        "dirty_code": (
            "def is_all_positive(numbers):\n"
            "    result = True\n"
            "    for i in range(len(numbers)):\n"
            "        if numbers[i] <= 0:\n"
            "            result = False\n"
            "            break\n"
            "    return result\n"
        ),
        "test_cases": [
            {"input": "print(is_all_positive([1, 2, 3, 4]))", "expected_output": "True"},
            {"input": "print(is_all_positive([10, -5, 3]))", "expected_output": "False"},
            {"input": "print(is_all_positive([]))", "expected_output": "True"},
            {"input": "print(is_all_positive(list(range(1, 100000))))", "expected_output": "True"},
        ],
        "expected_patterns": ["use_builtin_all", "remove_index_loop"],
    },

    # ──────────────────────────────────────────────────────────────────────
    # EASY: range(len()) -> enumerate()
    # ──────────────────────────────────────────────────────────────────────
    "enumerate_builtin": {
        "id": "enumerate_builtin",
        "description": "Optimize a list mapping function currently using range(len()). Use the enumerate() builtin.",
        "difficulty": "easy",
        "dirty_code": (
            "def format_indexed(items):\n"
            "    result = []\n"
            "    for i in range(len(items)):\n"
            "        val = str(i) + '-' + str(items[i])\n"
            "        result.append(val)\n"
            "    return result\n"
        ),
        "test_cases": [
            {"input": "print(format_indexed(['a', 'b', 'c']))", "expected_output": "['0-a', '1-b', '2-c']"},
            {"input": "print(format_indexed([]))", "expected_output": "[]"},
            {"input": "print(len(format_indexed(list(range(20000)))))", "expected_output": "20000"},
            {"input": "print(format_indexed(['x']))", "expected_output": "['0-x']"},
        ],
        "expected_patterns": ["use_builtin_enumerate", "remove_index_loop"],
    },

    # ──────────────────────────────────────────────────────────────────────
    # MEDIUM: Multi-list index loop -> zip()
    # ──────────────────────────────────────────────────────────────────────
    "zip_builtin": {
        "id": "zip_builtin",
        "description": "Optimize an operation combining two lists piece-by-piece using double indexing. Use the zip() builtin.",
        "difficulty": "medium",
        "dirty_code": (
            "def combine_lists(list_a, list_b):\n"
            "    result = []\n"
            "    for i in range(len(list_a)):\n"
            "        result.append(list_a[i] + list_b[i])\n"
            "    return result\n"
        ),
        "test_cases": [
            {"input": "print(combine_lists([1, 2], [3, 4]))", "expected_output": "[4, 6]"},
            {"input": "print(combine_lists([], []))", "expected_output": "[]"},
            {"input": "print(len(combine_lists(list(range(20000)), list(range(20000)))))", "expected_output": "20000"},
            {"input": "print(combine_lists(['a', 'b'], ['x', 'y']))", "expected_output": "['ax', 'by']"},
        ],
        "expected_patterns": ["use_builtin_zip", "remove_index_loop"],
    },

    # ──────────────────────────────────────────────────────────────────────
    # EASY: For Loop Max Tracking -> max() builtin
    # ──────────────────────────────────────────────────────────────────────
    "max_builtin": {
        "id": "max_builtin",
        "description": "Optimize a manual tracking sequence finding the highest number in a list. Use the max() builtin.",
        "difficulty": "easy",
        "dirty_code": (
            "def find_highest(numbers):\n"
            "    if len(numbers) == 0:\n"
            "        return None\n"
            "    highest = numbers[0]\n"
            "    for i in range(1, len(numbers)):\n"
            "        if numbers[i] > highest:\n"
            "            highest = numbers[i]\n"
            "    return highest\n"
        ),
        "test_cases": [
            {"input": "print(find_highest([10, -5, 30, 2]))", "expected_output": "30"},
            {"input": "print(find_highest([5]))", "expected_output": "5"},
            {"input": "print(find_highest([]))", "expected_output": "None"},
            {"input": "print(find_highest(list(range(100000))))", "expected_output": "99999"},
        ],
        "expected_patterns": ["use_builtin_max"],
    },

    # ──────────────────────────────────────────────────────────────────────
    # MEDIUM: For Loop filtering -> list comprehension
    # ──────────────────────────────────────────────────────────────────────
    "filter_builtin": {
        "id": "filter_builtin",
        "description": "Optimize a for loop that appends only even numbers to a new list. Use filter() or a list comprehension.",
        "difficulty": "medium",
        "dirty_code": (
            "def get_evens(numbers):\n"
            "    evens = []\n"
            "    for i in range(len(numbers)):\n"
            "        if numbers[i] % 2 == 0:\n"
            "            evens.append(numbers[i])\n"
            "    return evens\n"
        ),
        "test_cases": [
            {"input": "print(get_evens([1, 2, 3, 4, 5]))", "expected_output": "[2, 4]"},
            {"input": "print(get_evens([1, 3, 5]))", "expected_output": "[]"},
            {"input": "print(get_evens([]))", "expected_output": "[]"},
            {"input": "print(len(get_evens(list(range(50000)))))", "expected_output": "25000"},
        ],
        "expected_patterns": ["use_list_comprehension", "remove_index_loop"],
    }
}


def get_task(task_id: str) -> dict:
    """Get a task definition by ID."""
    if task_id not in TASKS:
        raise ValueError(f"Unknown task: {task_id}. Available: {list(TASKS.keys())}")
    return TASKS[task_id]


def list_task_ids() -> list:
    """Return all available task IDs."""
    return list(TASKS.keys())
