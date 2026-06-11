"""
Coding benchmark: 20 HumanEval problems with subprocess execution.
Usage: python bench_coding.py --base-url http://127.0.0.1:8080/v1 --model <alias> [--output results.json]
Score: pass@1 (fraction of problems where generated code passes all test cases)
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import textwrap
import time
from datetime import datetime
from pathlib import Path
from openai import OpenAI

# ---------------------------------------------------------------------------
# HumanEval problem subset (20 problems, self-contained Python only)
# ---------------------------------------------------------------------------

PROBLEMS = [
    {
        "id": "HE/0", "name": "has_close_elements",
        "prompt": "from typing import List\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    \"\"\"Check if any two numbers in the list are closer than threshold.\n    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n    False\n    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)\n    True\n    \"\"\"\n",
        "tests": [
            "assert has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) == True",
            "assert has_close_elements([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05) == False",
            "assert has_close_elements([1.0, 2.0, 5.9, 4.0, 5.0], 0.95) == True",
            "assert has_close_elements([1.0, 2.0, 5.9, 4.0, 5.0], 0.8) == False",
            "assert has_close_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.0], 0.1) == True",
        ],
    },
    {
        "id": "HE/3", "name": "below_zero",
        "prompt": "from typing import List\n\ndef below_zero(operations: List[int]) -> bool:\n    \"\"\"Check if balance goes below zero at any point.\n    >>> below_zero([1, 2, 3])\n    False\n    >>> below_zero([1, 2, -4, 5])\n    True\n    \"\"\"\n",
        "tests": [
            "assert below_zero([]) == False",
            "assert below_zero([1, 2, -3, 1, 2, -3]) == False",
            "assert below_zero([1, 2, -4, 5, 6]) == True",
            "assert below_zero([1, -1, 2, -2, 5, -5, 4, -4]) == False",
            "assert below_zero([1, -1, 2, -2, 5, -5, 4, -5]) == True",
        ],
    },
    {
        "id": "HE/6", "name": "parse_nested_parens",
        "prompt": "from typing import List\n\ndef parse_nested_parens(paren_string: str) -> List[int]:\n    \"\"\"Return max nesting depth for each group of parens (groups separated by spaces).\n    >>> parse_nested_parens('(()()) ((())) () ((())(()))')\n    [2, 3, 1, 3]\n    \"\"\"\n",
        "tests": [
            "assert parse_nested_parens('(()()) ((())) () ((())(()))') == [2, 3, 1, 3]",
            "assert parse_nested_parens('() (()) ((())) (((())))') == [1, 2, 3, 4]",
            "assert parse_nested_parens('(()(())((())))') == [4]",
        ],
    },
    {
        "id": "HE/9", "name": "rolling_max",
        "prompt": "from typing import List\n\ndef rolling_max(numbers: List[int]) -> List[int]:\n    \"\"\"Return list of running maximum values.\n    >>> rolling_max([1, 2, 3, 2, 3, 4, 2])\n    [1, 2, 3, 3, 3, 4, 4]\n    \"\"\"\n",
        "tests": [
            "assert rolling_max([]) == []",
            "assert rolling_max([1, 2, 3, 2, 3, 4, 2]) == [1, 2, 3, 3, 3, 4, 4]",
            "assert rolling_max([4, 3, 2, 1]) == [4, 4, 4, 4]",
            "assert rolling_max([3, 2, 3, 100, 3]) == [3, 3, 3, 100, 100]",
        ],
    },
    {
        "id": "HE/14", "name": "all_prefixes",
        "prompt": "from typing import List\n\ndef all_prefixes(string: str) -> List[str]:\n    \"\"\"Return list of all prefixes of the input string from shortest to longest.\n    >>> all_prefixes('abc')\n    ['a', 'ab', 'abc']\n    \"\"\"\n",
        "tests": [
            "assert all_prefixes('') == []",
            "assert all_prefixes('asdfgh') == ['a', 'as', 'asd', 'asdf', 'asdfg', 'asdfgh']",
            "assert all_prefixes('WWW') == ['W', 'WW', 'WWW']",
        ],
    },
    {
        "id": "HE/17", "name": "parse_music",
        "prompt": "from typing import List\n\ndef parse_music(music_string: str) -> List[int]:\n    \"\"\"Parse music notes: 'o' = 4 beats, 'o|' = 2 beats, '.|' = 1 beat.\n    >>> parse_music('o o| .| o| o| .| .| .| .| o o')\n    [4, 2, 1, 2, 2, 1, 1, 1, 1, 4, 4]\n    \"\"\"\n",
        "tests": [
            "assert parse_music('') == []",
            "assert parse_music('o o| .| o| o| .| .| .| .| o o') == [4, 2, 1, 2, 2, 1, 1, 1, 1, 4, 4]",
            "assert parse_music('o| o| .| .| o o|') == [2, 2, 1, 1, 4, 2]",
        ],
    },
    {
        "id": "HE/20", "name": "find_closest_elements",
        "prompt": "from typing import List, Tuple\n\ndef find_closest_elements(numbers: List[float]) -> Tuple[float, float]:\n    \"\"\"Return the two closest values from the sorted list (smaller first).\n    >>> find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.2])\n    (2.0, 2.2)\n    \"\"\"\n",
        "tests": [
            "assert find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.2]) == (2.0, 2.2)",
            "assert find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.0]) == (2.0, 2.0)",
            "assert find_closest_elements([1.0, 5.0, 3.0, 10.0]) == (1.0, 3.0)",
            "assert find_closest_elements([1.0, 2.0]) == (1.0, 2.0)",
        ],
    },
    {
        "id": "HE/23", "name": "strlen",
        "prompt": "def strlen(string: str) -> int:\n    \"\"\"Return the length of the string.\n    >>> strlen('')\n    0\n    >>> strlen('abc')\n    3\n    \"\"\"\n",
        "tests": [
            "assert strlen('') == 0",
            "assert strlen('x') == 1",
            "assert strlen('asdfgh') == 6",
            "assert strlen('hello world') == 11",
        ],
    },
    {
        "id": "HE/24", "name": "largest_divisor",
        "prompt": "def largest_divisor(n: int) -> int:\n    \"\"\"Return the largest divisor of n that is smaller than n.\n    >>> largest_divisor(15)\n    5\n    \"\"\"\n",
        "tests": [
            "assert largest_divisor(3) == 1",
            "assert largest_divisor(7) == 1",
            "assert largest_divisor(10) == 5",
            "assert largest_divisor(100) == 50",
            "assert largest_divisor(49) == 7",
        ],
    },
    {
        "id": "HE/26", "name": "remove_duplicates",
        "prompt": "from typing import List\n\ndef remove_duplicates(numbers: List[int]) -> List[int]:\n    \"\"\"Remove elements that appear more than once, keeping order.\n    >>> remove_duplicates([1, 2, 3, 2, 4])\n    [1, 3, 4]\n    \"\"\"\n",
        "tests": [
            "assert remove_duplicates([]) == []",
            "assert remove_duplicates([1, 2, 3, 2, 4]) == [1, 3, 4]",
            "assert remove_duplicates([1, 2, 3, 4]) == [1, 2, 3, 4]",
            "assert remove_duplicates([1, 1, 1, 1, 1]) == []",
        ],
    },
    {
        "id": "HE/28", "name": "concatenate",
        "prompt": "from typing import List\n\ndef concatenate(strings: List[str]) -> str:\n    \"\"\"Concatenate all strings in the list.\n    >>> concatenate(['a', 'b', 'c'])\n    'abc'\n    \"\"\"\n",
        "tests": [
            "assert concatenate([]) == ''",
            "assert concatenate(['a', 'b', 'c']) == 'abc'",
            "assert concatenate(['x', 'y', 'z']) == 'xyz'",
        ],
    },
    {
        "id": "HE/32", "name": "poly_zero",
        "prompt": "import math\n\ndef poly(xs: list, x: float):\n    return sum([coeff * math.pow(x, i) for i, coeff in enumerate(xs)])\n\ndef find_zero(xs: list):\n    \"\"\"Find a zero of a polynomial with an even number of coefficients.\n    The largest coefficient is non-zero. Guaranteed to have a zero.\n    >>> round(find_zero([1, 2]), 3)\n    -0.5\n    \"\"\"\n",
        "tests": [
            "import math\nassert math.isclose(poly([1, 2], find_zero([1, 2])), 0, abs_tol=1e-3)",
            "import math\nassert math.isclose(poly([-6, 11, -6, 1], find_zero([-6, 11, -6, 1])), 0, abs_tol=1e-3)",
        ],
    },
    {
        "id": "HE/33", "name": "sort_third",
        "prompt": "from typing import List\n\ndef sort_third(l: List[int]) -> List[int]:\n    \"\"\"Return list where values at indices divisible by 3 are sorted, others unchanged.\n    >>> sort_third([1, 2, 3])\n    [1, 2, 3]\n    >>> sort_third([5, 6, 3, 4, 8, 9, 2])\n    [2, 6, 3, 4, 8, 9, 5]\n    \"\"\"\n",
        "tests": [
            "assert sort_third([1, 2, 3]) == [1, 2, 3]",
            "assert sort_third([5, 6, 3, 4, 8, 9, 2]) == [2, 6, 3, 4, 8, 9, 5]",
            "assert sort_third([2, 6, 4, 3, 4, 3, 9, 3, 10]) == [2, 6, 4, 3, 4, 3, 9, 3, 10]",
        ],
    },
    {
        "id": "HE/36", "name": "fizz_buzz",
        "prompt": "def fizz_buzz(n: int) -> int:\n    \"\"\"Return count of 7s in integers from 1 to n divisible by 11 or 13.\n    >>> fizz_buzz(50)\n    0\n    >>> fizz_buzz(78)\n    2\n    >>> fizz_buzz(79)\n    3\n    \"\"\"\n",
        "tests": [
            "assert fizz_buzz(50) == 0",
            "assert fizz_buzz(78) == 2",
            "assert fizz_buzz(79) == 3",
            "assert fizz_buzz(100) == 3",
            "assert fizz_buzz(200) == 6",
        ],
    },
    {
        "id": "HE/41", "name": "car_race_collision",
        "prompt": "def car_race_collision(n: int) -> int:\n    \"\"\"Return number of collisions when n cars going left meet n cars going right.\n    >>> car_race_collision(2)\n    4\n    \"\"\"\n",
        "tests": [
            "assert car_race_collision(2) == 4",
            "assert car_race_collision(3) == 9",
            "assert car_race_collision(4) == 16",
            "assert car_race_collision(8) == 64",
        ],
    },
    {
        "id": "HE/44", "name": "change_base",
        "prompt": "def change_base(x: int, base: int) -> str:\n    \"\"\"Convert x to given base (base < 10), return as string.\n    >>> change_base(8, 3)\n    '22'\n    >>> change_base(8, 2)\n    '1000'\n    >>> change_base(7, 2)\n    '111'\n    \"\"\"\n",
        "tests": [
            "assert change_base(8, 3) == '22'",
            "assert change_base(9, 3) == '100'",
            "assert change_base(234, 2) == '11101010'",
            "assert change_base(16, 2) == '10000'",
            "assert change_base(8, 2) == '1000'",
        ],
    },
    {
        "id": "HE/50", "name": "encode_shift",
        "prompt": "def encode_shift(s: str) -> str:\n    \"\"\"Shift each letter in s by 5 in alphabet, wrap around.\"\"\"\n    return ''.join([chr(((ord(ch) + 5 - ord('a')) % 26) + ord('a')) if ch.isalpha() and ch.islower() else ch for ch in s])\n\ndef decode_shift(s: str) -> str:\n    \"\"\"Decode a string encoded with encode_shift.\n    >>> decode_shift(encode_shift('hello'))\n    'hello'\n    \"\"\"\n",
        "tests": [
            "assert decode_shift(encode_shift('hello')) == 'hello'",
            "assert decode_shift(encode_shift('abc')) == 'abc'",
            "assert decode_shift(encode_shift('xyz')) == 'xyz'",
            "assert decode_shift(encode_shift('test string')) == 'test string'",
        ],
    },
    {
        "id": "HE/51", "name": "remove_vowels",
        "prompt": "def remove_vowels(text: str) -> str:\n    \"\"\"Remove all vowels from text.\n    >>> remove_vowels('')\n    ''\n    >>> remove_vowels('abcdef')\n    'bcdf'\n    >>> remove_vowels('hello world')\n    'hll wrld'\n    \"\"\"\n",
        "tests": [
            "assert remove_vowels('') == ''",
            "assert remove_vowels('abcdef') == 'bcdf'",
            "assert remove_vowels('hello world') == 'hll wrld'",
            "assert remove_vowels('aeiou') == ''",
        ],
    },
    {
        "id": "HE/58", "name": "common",
        "prompt": "from typing import List\n\ndef common(l1: List[int], l2: List[int]) -> List[int]:\n    \"\"\"Return unique common elements of two lists, sorted.\n    >>> common([1, 4, 3, 34, 653, 2, 5], [5, 7, 1, 5, 9, 653, 121])\n    [1, 5, 653]\n    \"\"\"\n",
        "tests": [
            "assert common([1, 4, 3, 34, 653, 2, 5], [5, 7, 1, 5, 9, 653, 121]) == [1, 5, 653]",
            "assert common([5, 3, 2, 8], [3, 2]) == [2, 3]",
            "assert common([], [1, 2, 3]) == []",
            "assert common([1, 2, 3], []) == []",
        ],
    },
    {
        "id": "HE/62", "name": "derivative",
        "prompt": "from typing import List\n\ndef derivative(xs: List[int]) -> List[int]:\n    \"\"\"Return derivative of polynomial represented as list of coefficients.\n    xs[0] + xs[1]*x + xs[2]*x^2 + ...\n    >>> derivative([3, 1, 2, 4, 5])\n    [1, 4, 12, 20]\n    >>> derivative([1, 2, 3])\n    [2, 6]\n    \"\"\"\n",
        "tests": [
            "assert derivative([3, 1, 2, 4, 5]) == [1, 4, 12, 20]",
            "assert derivative([1, 2, 3]) == [2, 6]",
            "assert derivative([3, 2, 1]) == [2, 2]",
            "assert derivative([3]) == []",
        ],
    },
]


# ---------------------------------------------------------------------------
# Code extraction and execution
# ---------------------------------------------------------------------------

def extract_code(response: str, problem_name: str) -> str:
    """Extract Python function from model response."""
    # Try ```python ... ``` block first
    match = re.search(r"```(?:python)?\n(.*?)```", response, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Try to find function def
    lines = response.split("\n")
    code_lines = []
    in_func = False
    for line in lines:
        if f"def {problem_name}" in line or (code_lines and (line.startswith(" ") or line.startswith("\t") or line.strip() == "")):
            in_func = True
        if in_func:
            code_lines.append(line)
    if code_lines:
        return "\n".join(code_lines).strip()
    return response.strip()


def run_tests(code: str, problem: dict) -> tuple[bool, str]:
    """Execute code + tests in subprocess. Returns (passed, error_msg)."""
    test_code = "\n".join(problem["tests"])
    # Body-only response (no def line) → indent so it sits inside the function header from prompt
    if not re.search(r"^\s*def\s", code, re.MULTILINE):
        code = textwrap.indent(textwrap.dedent(code), "    ")
    full_code = f"{problem['prompt']}\n{code}\n\n{test_code}\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(full_code)
        tmppath = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmppath],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return True, ""
        return False, (result.stderr or result.stdout)[:500]
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, str(e)
    finally:
        Path(tmppath).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert Python programmer. Complete the given Python function.
Return ONLY the function body (the implementation), starting with the first line of indented code.
Do not repeat the function signature. Do not include docstrings. Do not include tests.
Use only Python standard library. Keep the implementation correct and concise."""


# Fast 10-problem subset (balanced difficulty)
_FAST_PROBLEMS = {"HE/0","HE/9","HE/14","HE/24","HE/26","HE/33","HE/36","HE/44","HE/51","HE/62"}

def run_coding_bench(base_url: str, model: str, timeout: int = 120, fast: bool = True) -> dict:
    client = OpenAI(base_url=base_url, api_key="not-needed")
    active = [p for p in PROBLEMS if not fast or p["id"] in _FAST_PROBLEMS]
    results = []

    for problem in active:
        print(f"  [{problem['id']}] {problem['name']}...", end="", flush=True)
        t0 = time.time()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Complete this function:\n\n{problem['prompt']}\n\nReturn only the implementation body."},
                ],
                max_tokens=2048,
                temperature=0.0,
                timeout=timeout,
            )
            raw = response.choices[0].message.content or ""
            elapsed = time.time() - t0

            code = extract_code(raw, problem["name"])
            passed, err = run_tests(code, problem)

            icon = "✓" if passed else "✗"
            print(f" {icon} ({elapsed:.1f}s)")

            results.append({
                "id": problem["id"],
                "name": problem["name"],
                "passed": passed,
                "error": err if not passed else "",
                "latency_s": round(elapsed, 2),
                "generated_code": code[:500],
            })
        except Exception as e:
            elapsed = time.time() - t0
            print(f" ERROR: {str(e)[:60]}")
            results.append({
                "id": problem["id"],
                "name": problem["name"],
                "passed": False,
                "error": str(e)[:200],
                "latency_s": round(elapsed, 2),
                "generated_code": "",
            })

    n_passed = sum(1 for r in results if r["passed"])
    pass_at_1 = n_passed / max(len(results), 1)

    return {
        "pass_at_1": round(pass_at_1, 4),
        "n_passed": n_passed,
        "n_total": len(results),
        "details": results,
        "timestamp": datetime.now().isoformat(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--full", action="store_true", help="Run all 20 embedded HumanEval problems instead of the fast 10-problem subset")
    args = parser.parse_args()

    n = len(PROBLEMS) if args.full else len(_FAST_PROBLEMS)
    print(f"[coding] Benchmarking: {args.model} @ {args.base_url} ({n} problems)")
    result = run_coding_bench(args.base_url, args.model, args.timeout, fast=not args.full)

    print(f"\n[coding] pass@1: {result['pass_at_1']:.1%}  ({result['n_passed']}/{result['n_total']})")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2))
        print(f"[coding] Saved to {args.output}")
    else:
        print(json.dumps({k: v for k, v in result.items() if k != "details"}, indent=2))

if __name__ == "__main__":
    main()
