"""
Agentic tool-calling benchmark: 25 BFCL-style tests against llama-server OpenAI API.
Usage: python bench_toolcall.py --base-url http://127.0.0.1:8080/v1 --model <alias> [--output results.json]
Scores: tool_accuracy (correct tool selected), param_accuracy, no_tool_accuracy, overall
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from openai import OpenAI

# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

TOOLS_ALL = {
    "get_weather": {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "units": {"type": "string", "enum": ["celsius", "fahrenheit"], "description": "Temperature units"},
                },
                "required": ["city"],
            },
        },
    },
    "calculate": {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a mathematical expression",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression to evaluate"},
                },
                "required": ["expression"],
            },
        },
    },
    "search_web": {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Maximum results to return", "default": 10},
                },
                "required": ["query"],
            },
        },
    },
    "get_stock_price": {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Get current stock price for a ticker symbol",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol (e.g. AAPL)"},
                },
                "required": ["symbol"],
            },
        },
    },
    "translate": {
        "type": "function",
        "function": {
            "name": "translate",
            "description": "Translate text to another language",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to translate"},
                    "target_language": {"type": "string", "description": "Target language code (e.g. 'fr', 'es', 'ja')"},
                },
                "required": ["text", "target_language"],
            },
        },
    },
    "convert_units": {
        "type": "function",
        "function": {
            "name": "convert_units",
            "description": "Convert a value from one unit to another",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "from_unit": {"type": "string"},
                    "to_unit": {"type": "string"},
                },
                "required": ["value", "from_unit", "to_unit"],
            },
        },
    },
    "get_current_time": {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get current time in a given timezone",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "IANA timezone (e.g. 'Asia/Tokyo')"},
                },
                "required": ["timezone"],
            },
        },
    },
    "set_reminder": {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Set a reminder with a message at a given time",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "time": {"type": "string", "description": "Time string (e.g. '20:00', '8pm')"},
                },
                "required": ["message", "time"],
            },
        },
    },
    "send_email": {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    "create_calendar_event": {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Create a new calendar event",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "datetime": {"type": "string", "description": "Date and time string"},
                    "attendees": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "datetime"],
            },
        },
    },
    "read_file": {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
        },
    },
    "random_number": {
        "type": "function",
        "function": {
            "name": "random_number",
            "description": "Generate a random integer between min and max (inclusive)",
            "parameters": {
                "type": "object",
                "properties": {
                    "min": {"type": "integer"},
                    "max": {"type": "integer"},
                },
                "required": ["min", "max"],
            },
        },
    },
    "get_definition": {
        "type": "function",
        "function": {
            "name": "get_definition",
            "description": "Get the dictionary definition of a word",
            "parameters": {
                "type": "object",
                "properties": {
                    "word": {"type": "string"},
                },
                "required": ["word"],
            },
        },
    },
    "convert_currency": {
        "type": "function",
        "function": {
            "name": "convert_currency",
            "description": "Convert amount from one currency to another",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "from_currency": {"type": "string", "description": "3-letter ISO currency code"},
                    "to_currency": {"type": "string", "description": "3-letter ISO currency code"},
                },
                "required": ["amount", "from_currency", "to_currency"],
            },
        },
    },
    "geocode": {
        "type": "function",
        "function": {
            "name": "geocode",
            "description": "Get coordinates (lat/lon) of a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                },
                "required": ["location"],
            },
        },
    },
    "set_language": {
        "type": "function",
        "function": {
            "name": "set_language",
            "description": "Set the application interface language",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {"type": "string", "enum": ["en", "es", "fr", "de", "ja", "zh"]},
                },
                "required": ["language"],
            },
        },
    },
}

def tools(*names):
    return [TOOLS_ALL[n] for n in names if n in TOOLS_ALL]


TESTS = [
    # --- Group 1: Single tool, clear intent ---
    {
        "id": "T01", "desc": "weather lookup",
        "user": "What's the weather like in Tokyo right now?",
        "tools": tools("get_weather", "search_web", "get_current_time"),
        "expect_tool": "get_weather",
        "expect_params": {"city": lambda v: "tokyo" in v.lower()},
        "no_tool": False,
    },
    {
        "id": "T02", "desc": "arithmetic calculation",
        "user": "What is 17 multiplied by 23?",
        "tools": tools("calculate", "search_web"),
        "expect_tool": "calculate",
        "expect_params": {"expression": lambda v: re.search(r"17.*23|23.*17", v)},
        "no_tool": False,
    },
    {
        "id": "T03", "desc": "web search",
        "user": "Find recent research papers on large language models published in 2024",
        "tools": tools("search_web", "get_definition"),
        "expect_tool": "search_web",
        "expect_params": {"query": lambda v: len(v) > 5},
        "no_tool": False,
    },
    {
        "id": "T04", "desc": "stock price",
        "user": "What is the current stock price of Tesla?",
        "tools": tools("get_stock_price", "search_web", "calculate"),
        "expect_tool": "get_stock_price",
        "expect_params": {"symbol": lambda v: "tsla" in v.lower()},
        "no_tool": False,
    },
    {
        "id": "T05", "desc": "translation",
        "user": "Translate 'good morning' to French",
        "tools": tools("translate", "search_web", "get_definition"),
        "expect_tool": "translate",
        "expect_params": {
            "text": lambda v: "good morning" in v.lower(),
            "target_language": lambda v: "fr" in v.lower() or "french" in v.lower(),
        },
        "no_tool": False,
    },
    {
        "id": "T06", "desc": "unit conversion",
        "user": "Convert 100 kilometers to miles",
        "tools": tools("convert_units", "calculate", "search_web"),
        "expect_tool": "convert_units",
        "expect_params": {
            "value": lambda v: float(v) == 100.0,
            "from_unit": lambda v: "km" in v.lower() or "kilo" in v.lower(),
        },
        "no_tool": False,
    },
    {
        "id": "T07", "desc": "timezone time",
        "user": "What time is it in Tokyo right now?",
        "tools": tools("get_current_time", "get_weather", "search_web"),
        "expect_tool": "get_current_time",
        "expect_params": {"timezone": lambda v: "tokyo" in v.lower() or "asia/tokyo" in v.lower() or "japan" in v.lower()},
        "no_tool": False,
    },
    {
        "id": "T08", "desc": "set reminder",
        "user": "Set a reminder to take my medicine at 8pm tonight",
        "tools": tools("set_reminder", "create_calendar_event", "send_email"),
        "expect_tool": "set_reminder",
        "expect_params": {"message": lambda v: len(v) > 3},
        "no_tool": False,
    },
    {
        "id": "T09", "desc": "send email",
        "user": "Send an email to alice@example.com with subject 'Project Update' saying the deadline has moved to Friday",
        "tools": tools("send_email", "create_calendar_event", "search_web"),
        "expect_tool": "send_email",
        "expect_params": {
            "to": lambda v: "alice@example.com" in v.lower(),
            "subject": lambda v: len(v) > 3,
        },
        "no_tool": False,
    },
    {
        "id": "T10", "desc": "create calendar event",
        "user": "Schedule a dentist appointment for next Monday at 2pm",
        "tools": tools("create_calendar_event", "set_reminder", "send_email"),
        "expect_tool": "create_calendar_event",
        "expect_params": {"title": lambda v: len(v) > 3},
        "no_tool": False,
    },
    {
        "id": "T11", "desc": "read file",
        "user": "Read the file at /var/log/app.log",
        "tools": tools("read_file", "search_web"),
        "expect_tool": "read_file",
        "expect_params": {"path": lambda v: "app.log" in v},
        "no_tool": False,
    },
    {
        "id": "T12", "desc": "random number",
        "user": "Give me a random number between 1 and 100",
        "tools": tools("random_number", "calculate"),
        "expect_tool": "random_number",
        "expect_params": {
            "min": lambda v: int(v) == 1,
            "max": lambda v: int(v) == 100,
        },
        "no_tool": False,
    },
    {
        "id": "T13", "desc": "word definition",
        "user": "What does 'ephemeral' mean?",
        "tools": tools("get_definition", "search_web"),
        "expect_tool": "get_definition",
        "expect_params": {"word": lambda v: "ephemeral" in v.lower()},
        "no_tool": False,
    },
    {
        "id": "T14", "desc": "currency conversion",
        "user": "How much is 500 US dollars in euros?",
        "tools": tools("convert_currency", "convert_units", "calculate"),
        "expect_tool": "convert_currency",
        "expect_params": {
            "amount": lambda v: float(v) == 500.0,
            "from_currency": lambda v: "usd" in v.lower() or v.upper() == "USD",
        },
        "no_tool": False,
    },
    {
        "id": "T15", "desc": "geocode",
        "user": "What are the GPS coordinates of the Eiffel Tower?",
        "tools": tools("geocode", "search_web", "get_weather"),
        "expect_tool": "geocode",
        "expect_params": {"location": lambda v: "eiffel" in v.lower() or "paris" in v.lower()},
        "no_tool": False,
    },
    # --- Group 2: Multi-param correctness ---
    {
        "id": "T16", "desc": "percent calculation",
        "user": "What is 15 percent of 840?",
        "tools": tools("calculate", "search_web", "convert_units"),
        "expect_tool": "calculate",
        "expect_params": {"expression": lambda v: ("15" in v and "840" in v) or "0.15" in v},
        "no_tool": False,
    },
    {
        "id": "T17", "desc": "weather units",
        "user": "What is the weather in Berlin in Celsius?",
        "tools": tools("get_weather", "get_current_time"),
        "expect_tool": "get_weather",
        "expect_params": {
            "city": lambda v: "berlin" in v.lower(),
            "units": lambda v: "celsius" in v.lower(),
        },
        "no_tool": False,
    },
    {
        "id": "T18", "desc": "translate Japanese",
        "user": "How do you say 'goodbye' in Japanese?",
        "tools": tools("translate", "search_web", "get_definition"),
        "expect_tool": "translate",
        "expect_params": {
            "text": lambda v: "goodbye" in v.lower(),
            "target_language": lambda v: "ja" in v.lower() or "japanese" in v.lower(),
        },
        "no_tool": False,
    },
    {
        "id": "T19", "desc": "temperature conversion",
        "user": "What is 37 degrees Celsius in Fahrenheit?",
        "tools": tools("convert_units", "calculate", "search_web"),
        "expect_tool": "convert_units",
        "expect_params": {
            "value": lambda v: float(v) == 37.0,
            "from_unit": lambda v: "celsius" in v.lower() or "c" == v.lower(),
        },
        "no_tool": False,
    },
    {
        "id": "T20", "desc": "Sydney time",
        "user": "Is it currently night time in Sydney, Australia?",
        "tools": tools("get_current_time", "get_weather"),
        "expect_tool": "get_current_time",
        "expect_params": {"timezone": lambda v: "sydney" in v.lower() or "australia" in v.lower() or "pacific" in v.lower()},
        "no_tool": False,
    },
    # --- Group 3: No tool needed ---
    {
        "id": "T21", "desc": "no-tool: basic math",
        "user": "What is 2 plus 2?",
        "tools": tools("get_weather", "search_web", "calculate"),
        "expect_tool": None,
        "expect_params": {},
        "no_tool": True,
    },
    {
        "id": "T22", "desc": "no-tool: factual",
        "user": "Who wrote the play Hamlet?",
        "tools": tools("search_web", "get_definition"),
        "expect_tool": None,
        "expect_params": {},
        "no_tool": True,
    },
    {
        "id": "T23", "desc": "no-tool: list",
        "user": "List the planets in our solar system in order from the sun",
        "tools": tools("search_web", "geocode"),
        "expect_tool": None,
        "expect_params": {},
        "no_tool": True,
    },
    # --- Group 4: Edge cases ---
    {
        "id": "T24", "desc": "optional param",
        "user": "Search for Python tutorials and show me the top 5 results",
        "tools": tools("search_web", "get_definition"),
        "expect_tool": "search_web",
        "expect_params": {
            "query": lambda v: "python" in v.lower(),
            "max_results": lambda v: int(v) == 5,
        },
        "no_tool": False,
    },
    {
        "id": "T25", "desc": "enum param",
        "user": "Switch the interface to Spanish",
        "tools": tools("set_language", "translate"),
        "expect_tool": "set_language",
        "expect_params": {"language": lambda v: v.lower() in ("es", "spanish")},
        "no_tool": False,
    },
    # --- Group 5: Multi-tool calls ---
    {
        "id": "T26", "desc": "multi-tool: weather and time",
        "user": "Tell me the weather in Tokyo and the current time there.",
        "tools": tools("get_weather", "get_current_time", "search_web"),
        "expect_tools": ["get_weather", "get_current_time"],
        "expect_params_by_tool": {
            "get_weather": {"city": lambda v: "tokyo" in v.lower()},
            "get_current_time": {"timezone": lambda v: "tokyo" in v.lower() or "asia/tokyo" in v.lower() or "japan" in v.lower()},
        },
        "no_tool": False,
    },
    {
        "id": "T27", "desc": "multi-tool: stock and currency",
        "user": "Get Apple's stock price and convert 100 USD to EUR.",
        "tools": tools("get_stock_price", "convert_currency", "calculate", "search_web"),
        "expect_tools": ["get_stock_price", "convert_currency"],
        "expect_params_by_tool": {
            "get_stock_price": {"symbol": lambda v: "aapl" in v.lower() or "apple" in v.lower()},
            "convert_currency": {
                "amount": lambda v: float(v) == 100.0,
                "from_currency": lambda v: "usd" in v.lower() or v.upper() == "USD",
                "to_currency": lambda v: "eur" in v.lower() or v.upper() == "EUR",
            },
        },
        "no_tool": False,
    },
    {
        "id": "T28", "desc": "multi-tool: email and calendar",
        "user": "Email bob@example.com about the budget review and schedule a budget review meeting for Friday at 10am.",
        "tools": tools("send_email", "create_calendar_event", "set_reminder"),
        "expect_tools": ["send_email", "create_calendar_event"],
        "expect_params_by_tool": {
            "send_email": {
                "to": lambda v: "bob@example.com" in v.lower(),
                "subject": lambda v: "budget" in v.lower() or "review" in v.lower(),
            },
            "create_calendar_event": {"title": lambda v: "budget" in v.lower() or "review" in v.lower()},
        },
        "no_tool": False,
    },
    {
        "id": "T29", "desc": "multi-tool: geocode and weather",
        "user": "Find the coordinates of the Eiffel Tower and get the weather in Paris.",
        "tools": tools("geocode", "get_weather", "search_web"),
        "expect_tools": ["geocode", "get_weather"],
        "expect_params_by_tool": {
            "geocode": {"location": lambda v: "eiffel" in v.lower() or "paris" in v.lower()},
            "get_weather": {"city": lambda v: "paris" in v.lower()},
        },
        "no_tool": False,
    },
    {
        "id": "T30", "desc": "multi-tool: reminder and unit conversion",
        "user": "Convert 5 miles to kilometers and remind me at 6pm to log the result.",
        "tools": tools("convert_units", "set_reminder", "calculate"),
        "expect_tools": ["convert_units", "set_reminder"],
        "expect_params_by_tool": {
            "convert_units": {
                "value": lambda v: float(v) == 5.0,
                "from_unit": lambda v: "mile" in v.lower() or v.lower() == "mi",
                "to_unit": lambda v: "km" in v.lower() or "kilo" in v.lower(),
            },
            "set_reminder": {"time": lambda v: "6" in v.lower() or "18" in v.lower()},
        },
        "no_tool": False,
    },
]


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_tool_call(test: dict, response) -> dict:
    msg = response.choices[0].message
    tool_calls = msg.tool_calls or []
    called_tool = tool_calls[0].function.name if tool_calls else None
    called_tools = [tc.function.name for tc in tool_calls]
    expected_tools = test.get("expect_tools")

    result = {
        "id": test["id"],
        "desc": test["desc"],
        "called_tool": called_tool,
        "called_tools": called_tools,
        "expected_tool": test.get("expect_tool"),
        "expected_tools": expected_tools,
        "tool_correct": False,
        "params_correct": False,
        "params_detail": {},
        "score": 0.0,
        "raw_content": msg.content or "",
    }

    # No-tool tests
    if test["no_tool"]:
        result["tool_correct"] = called_tool is None
        result["params_correct"] = True
        result["score"] = 1.0 if called_tool is None else 0.0
        return result

    if expected_tools:
        expected_set = set(expected_tools)
        called_set = set(called_tools)
        result["tool_correct"] = expected_set.issubset(called_set)
        if not result["tool_correct"]:
            result["score"] = 0.0
            return result

        args_by_tool = {}
        for tc in tool_calls:
            try:
                args_by_tool[tc.function.name] = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, AttributeError):
                args_by_tool[tc.function.name] = {}

        all_pass = True
        param_results = {}
        for tool_name, params in test.get("expect_params_by_tool", {}).items():
            tool_args = args_by_tool.get(tool_name, {})
            tool_param_results = {}
            for param, checker in params.items():
                val = tool_args.get(param)
                try:
                    ok = checker(val) if val is not None else False
                    ok = bool(ok)
                except Exception:
                    ok = False
                tool_param_results[param] = {"value": val, "pass": ok}
                if not ok:
                    all_pass = False
            param_results[tool_name] = tool_param_results

        result["params_detail"] = param_results
        result["params_correct"] = all_pass
        result["score"] = 1.0 if all_pass else 0.5
        return result

    # Tool should be called
    if called_tool != test["expect_tool"]:
        result["tool_correct"] = False
        result["score"] = 0.0
        return result

    result["tool_correct"] = True

    # Check params
    try:
        args = json.loads(tool_calls[0].function.arguments)
    except (json.JSONDecodeError, AttributeError):
        args = {}

    param_results = {}
    all_pass = True
    for param, checker in test["expect_params"].items():
        val = args.get(param)
        try:
            ok = checker(val) if val is not None else False
            ok = bool(ok)
        except Exception:
            ok = False
        param_results[param] = {"value": val, "pass": ok}
        if not ok:
            all_pass = False

    result["params_detail"] = param_results
    result["params_correct"] = all_pass
    result["score"] = 1.0 if all_pass else 0.5  # partial credit: right tool, wrong params

    return result


# Default 15-test balanced subset (fast); full 25 if n_tests=25
_FAST_IDS = {"T01","T02","T03","T04","T05","T06","T07","T08","T16","T17","T18","T21","T22","T23","T25"}

def run_toolcall_bench(base_url: str, model: str, timeout: int = 60, n_tests: int = 15) -> dict:
    client = OpenAI(base_url=base_url, api_key="not-needed")
    run_ids = _FAST_IDS if n_tests <= 15 else {t["id"] for t in TESTS}
    active = [t for t in TESTS if t["id"] in run_ids]

    results = []
    for test in active:
        print(f"  [{test['id']}] {test['desc']}...", end="", flush=True)
        t0 = time.time()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Use the provided tools when appropriate."},
                    {"role": "user", "content": test["user"]},
                ],
                tools=test["tools"],
                tool_choice="auto",
                max_tokens=512,
                temperature=0.0,
                timeout=timeout,
            )
            elapsed = time.time() - t0
            r = evaluate_tool_call(test, response)
            r["latency_s"] = round(elapsed, 2)
            icon = "✓" if r["score"] == 1.0 else ("~" if r["score"] > 0 else "✗")
            print(f" {icon} ({elapsed:.1f}s)")
        except Exception as e:
            elapsed = time.time() - t0
            r = {
                "id": test["id"], "desc": test["desc"],
                "called_tool": None, "expected_tool": test.get("expect_tool"),
                "tool_correct": False, "params_correct": False,
                "params_detail": {}, "score": 0.0,
                "error": str(e)[:200],
                "latency_s": round(elapsed, 2),
            }
            print(f" ERROR: {str(e)[:60]}")
        results.append(r)

    test_by_id = {t["id"]: t for t in active}
    no_tool_tests = [r for r in results if test_by_id.get(r["id"], {}).get("no_tool")]
    tool_tests = [r for r in results if not test_by_id.get(r["id"], {}).get("no_tool")]

    tool_acc = sum(1 for r in tool_tests if r["tool_correct"]) / max(len(tool_tests), 1)
    param_acc = sum(1 for r in tool_tests if r["params_correct"]) / max(len(tool_tests), 1)
    no_tool_acc = sum(1 for r in no_tool_tests if r["tool_correct"]) / max(len(no_tool_tests), 1)
    overall = sum(r["score"] for r in results) / max(len(results), 1)

    return {
        "tool_accuracy": round(tool_acc, 4),
        "param_accuracy": round(param_acc, 4),
        "no_tool_accuracy": round(no_tool_acc, 4),
        "overall_score": round(overall, 4),
        "n_tests": len(results),
        "n_tool_tests": len(tool_tests),
        "n_no_tool_tests": len(no_tool_tests),
        "details": results,
        "timestamp": datetime.now().isoformat(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--n-tests", type=int, default=15)
    args = parser.parse_args()

    print(f"[toolcall] Benchmarking tool calling: {args.model} @ {args.base_url} ({args.n_tests} tests)")
    result = run_toolcall_bench(args.base_url, args.model, args.timeout, args.n_tests)

    print(f"\n[toolcall] Tool acc: {result['tool_accuracy']:.1%}  Param acc: {result['param_accuracy']:.1%}  No-tool acc: {result['no_tool_accuracy']:.1%}  Overall: {result['overall_score']:.1%}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2))
        print(f"[toolcall] Saved to {args.output}")
    else:
        print(json.dumps({k: v for k, v in result.items() if k != "details"}, indent=2))

if __name__ == "__main__":
    main()
