"""
Aggregate benchmark results and generate a markdown + JSON report.
Usage: python report.py [--results-dir results/] [--output benchmark_report.md]
"""
import argparse
import json
from datetime import datetime
from pathlib import Path


def load_results(results_dir: Path) -> dict:
    """Load all model result JSONs from results dir."""
    models = {}
    for model_dir in sorted(results_dir.iterdir()):
        if not model_dir.is_dir():
            continue
        model_id = model_dir.name
        data = {}
        for bench in ["speed", "toolcall", "coding", "reasoning"]:
            f = model_dir / f"{bench}.json"
            if f.exists():
                try:
                    data[bench] = json.loads(f.read_text())
                except Exception:
                    pass
        if data:
            models[model_id] = data
    return models


def format_val(v, fmt="{:.1f}") -> str:
    if v is None:
        return "—"
    try:
        return fmt.format(float(v))
    except (TypeError, ValueError):
        return str(v)


def generate_report(models: dict) -> str:
    lines = []
    lines.append(f"# Model Benchmark Report")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Summary table
    lines.append("## Summary\n")
    header = "| Model | PP tok/s | TG tok/s | Tool acc | Param acc | Code pass@1 | GSM8K acc | NGL |"
    sep    = "|-------|----------|----------|----------|-----------|-------------|-----------|-----|"
    lines.append(header)
    lines.append(sep)

    for model_id, data in models.items():
        speed = data.get("speed", {})
        tool = data.get("toolcall", {})
        code = data.get("coding", {})
        reason = data.get("reasoning", {})

        pp = format_val(speed.get("pp_tps"), "{:.0f}")
        tg = format_val(speed.get("tg_tps"), "{:.0f}")
        tool_acc = format_val(tool.get("tool_accuracy"), "{:.1%}") if tool.get("tool_accuracy") is not None else "—"
        param_acc = format_val(tool.get("param_accuracy"), "{:.1%}") if tool.get("param_accuracy") is not None else "—"
        code_p1 = format_val(code.get("pass_at_1"), "{:.1%}") if code.get("pass_at_1") is not None else "—"
        gsm = format_val(reason.get("accuracy"), "{:.1%}") if reason.get("accuracy") is not None else "—"
        ngl = speed.get("ngl", "—")

        lines.append(f"| {model_id} | {pp} | {tg} | {tool_acc} | {param_acc} | {code_p1} | {gsm} | {ngl} |")

    lines.append("")

    # Speed details
    lines.append("## Speed (PP = prefill, TG = generation @ 128k ctx, 512 tok)\n")
    lines.append("| Model | PP tok/s | TG tok/s | NGL | Notes |")
    lines.append("|-------|----------|----------|-----|-------|")
    for model_id, data in models.items():
        s = data.get("speed", {})
        if not s:
            continue
        pp = format_val(s.get("pp_tps"), "{:.1f}")
        tg = format_val(s.get("tg_tps"), "{:.1f}")
        ngl = s.get("ngl", "—")
        note = "CPU offload" if s.get("ngl", 99) < 99 else "Full GPU"
        lines.append(f"| {model_id} | {pp} | {tg} | {ngl} | {note} |")
    lines.append("")

    # Tool calling details
    lines.append("## Agentic Tool Calling (25 tests)\n")
    lines.append("| Model | Tool acc | Param acc | No-tool acc | Overall |")
    lines.append("|-------|----------|-----------|-------------|---------|")
    for model_id, data in models.items():
        t = data.get("toolcall", {})
        if not t:
            continue
        ta = f"{t.get('tool_accuracy', 0):.1%}"
        pa = f"{t.get('param_accuracy', 0):.1%}"
        na = f"{t.get('no_tool_accuracy', 0):.1%}"
        ov = f"{t.get('overall_score', 0):.1%}"
        lines.append(f"| {model_id} | {ta} | {pa} | {na} | {ov} |")
    lines.append("")

    # Coding details
    lines.append("## Coding (HumanEval subset, 20 problems)\n")
    lines.append("| Model | pass@1 | Passed/Total |")
    lines.append("|-------|--------|--------------|")
    for model_id, data in models.items():
        c = data.get("coding", {})
        if not c:
            continue
        p1 = f"{c.get('pass_at_1', 0):.1%}"
        pt = f"{c.get('n_passed', 0)}/{c.get('n_total', 0)}"
        lines.append(f"| {model_id} | {p1} | {pt} |")
    lines.append("")

    # Reasoning details
    lines.append("## Reasoning (GSM8K, 50 problems)\n")
    lines.append("| Model | Accuracy | Correct/Total |")
    lines.append("|-------|----------|---------------|")
    for model_id, data in models.items():
        r = data.get("reasoning", {})
        if not r:
            continue
        acc = f"{r.get('accuracy', 0):.1%}"
        ct = f"{r.get('n_correct', 0)}/{r.get('n_total', 0)}"
        lines.append(f"| {model_id} | {acc} | {ct} |")
    lines.append("")

    lines.append("---")
    lines.append("*Benchmarks run with llama.cpp SM120 build, RTX 5070 Ti Laptop GPU (12GB)*")

    return "\n".join(lines)


def generate_json_summary(models: dict) -> dict:
    summary = {"generated": datetime.now().isoformat(), "models": {}}
    for model_id, data in models.items():
        speed = data.get("speed", {})
        tool = data.get("toolcall", {})
        code = data.get("coding", {})
        reason = data.get("reasoning", {})
        summary["models"][model_id] = {
            "speed": {
                "pp_tps": speed.get("pp_tps"),
                "tg_tps": speed.get("tg_tps"),
                "ngl": speed.get("ngl"),
            },
            "toolcall": {
                "tool_accuracy": tool.get("tool_accuracy"),
                "param_accuracy": tool.get("param_accuracy"),
                "no_tool_accuracy": tool.get("no_tool_accuracy"),
                "overall_score": tool.get("overall_score"),
            },
            "coding": {
                "pass_at_1": code.get("pass_at_1"),
                "n_passed": code.get("n_passed"),
                "n_total": code.get("n_total"),
            },
            "reasoning": {
                "accuracy": reason.get("accuracy"),
                "n_correct": reason.get("n_correct"),
                "n_total": reason.get("n_total"),
            },
        }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, default=Path(__file__).parent / "results")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "benchmark_report.md")
    args = parser.parse_args()

    if not args.results_dir.exists():
        print(f"[report] Results dir not found: {args.results_dir}")
        return

    models = load_results(args.results_dir)
    if not models:
        print("[report] No results found")
        return

    print(f"[report] Found {len(models)} models: {', '.join(models.keys())}")

    md = generate_report(models)
    args.output.write_text(md, encoding="utf-8")
    print(f"[report] Markdown report: {args.output}")

    json_out = args.output.with_suffix(".json")
    json_out.write_text(json.dumps(generate_json_summary(models), indent=2), encoding="utf-8")
    print(f"[report] JSON summary: {json_out}")

    print("\n" + md)

if __name__ == "__main__":
    main()
