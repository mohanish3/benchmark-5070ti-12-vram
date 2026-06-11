"""
Speed benchmark: wraps llama-bench, parses PP/TG throughput.
Usage: python bench_speed.py --model path/to/model.gguf --ngl 99 --ctx 131072 [--threads 8] [--output results.json]
Writes JSON: {model, pp_tps, tg_tps, pp_ms, tg_ms, ngl, ctx, timestamp}
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
# llama-bench lives in the CUDA b9509 build (SM120 build only compiled llama-server)
CUDA_BENCH = ROOT / "tools" / "llama-cpp-cuda-b9509" / "llama-bench.exe"
SM120_BENCH = ROOT / "tools" / "llama.cpp-sm120-src" / "build-sm120" / "bin" / "Release" / "llama-bench.exe"

def find_llama_bench() -> Path:
    for candidate in (CUDA_BENCH, SM120_BENCH):
        if candidate.exists():
            return candidate
    import shutil
    p = shutil.which("llama-bench")
    if p:
        return Path(p)
    raise FileNotFoundError("llama-bench.exe not found")

def run_bench(model: Path, ngl: int, ctx: int, threads: int, prompt_tokens: int = 512, gen_tokens: int = 512, reps: int = 1) -> dict:
    bench = find_llama_bench()
    # llama-bench does not have -c; context = prompt + gen
    # Use -pg for combined pp+tg test, or separate -p/-n passes
    # Note: -fa uses on/off/auto, not 0/1
    cmd = [
        str(bench),
        "-m", str(model),
        "-ngl", str(ngl),
        "-p", f"0,{prompt_tokens}",  # "0" = no-warmup entry, then real run
        "-n", f"0,{gen_tokens}",
        "-t", str(threads),
        "-fa", "on",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "-o", "json",
        "-r", str(reps),
    ]
    print(f"[speed] Running: {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        print(f"[speed] llama-bench stderr: {result.stderr[-2000:]}", file=sys.stderr)
        raise RuntimeError(f"llama-bench failed: exit {result.returncode}")

    # Parse JSON output from llama-bench
    # llama-bench -o json outputs a JSON array (multi-line) to stdout
    # stderr contains loader messages - these are already captured separately
    raw = result.stdout.strip()

    entries = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            entries = parsed
        elif isinstance(parsed, dict):
            entries = [parsed]
    except json.JSONDecodeError:
        # Fallback: try to find the JSON array within mixed output
        m = re.search(r"(\[[\s\S]*\])", raw)
        if m:
            try:
                entries = json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

    if not entries:
        # Fallback: parse table output
        return _parse_table_output(result.stdout, model, ngl, ctx)

    pp_tps = None
    tg_tps = None
    pp_ms = None
    tg_ms = None

    for entry in entries:
        # llama-bench JSON: n_prompt>0 n_gen=0 → PP test; n_prompt=0 n_gen>0 → TG test
        n_prompt = entry.get("n_prompt", 0)
        n_gen = entry.get("n_gen", 0)
        avg_ts = entry.get("avg_ts")
        avg_ms = entry.get("avg_t")  # average time in ms per token (may not exist)

        if n_prompt > 0 and n_gen == 0 and avg_ts:
            pp_tps = float(avg_ts)
            if avg_ms:
                pp_ms = float(avg_ms)
        elif n_gen > 0 and n_prompt == 0 and avg_ts:
            tg_tps = float(avg_ts)
            if avg_ms:
                tg_ms = float(avg_ms)

    return {
        "model": str(model.name),
        "pp_tps": pp_tps,
        "tg_tps": tg_tps,
        "pp_ms": pp_ms,
        "tg_ms": tg_ms,
        "ngl": ngl,
        "ctx": ctx,
        "prompt_tokens": prompt_tokens,
        "gen_tokens": gen_tokens,
        "reps": reps,
        "raw": raw[:4000],
        "timestamp": datetime.now().isoformat(),
    }

def _parse_table_output(stdout: str, model: Path, ngl: int, ctx: int) -> dict:
    """Fallback parser for llama-bench table output."""
    pp_tps = None
    tg_tps = None
    # Example line: | pp512 | ... | 1234.56 t/s |
    pp_match = re.search(r"pp\d+.*?(\d+\.?\d*)\s+t/s", stdout)
    tg_match = re.search(r"tg\d+.*?(\d+\.?\d*)\s+t/s", stdout)
    if pp_match:
        pp_tps = float(pp_match.group(1))
    if tg_match:
        tg_tps = float(tg_match.group(1))
    return {
        "model": str(model.name),
        "pp_tps": pp_tps,
        "tg_tps": tg_tps,
        "pp_ms": None,
        "tg_ms": None,
        "ngl": ngl,
        "ctx": ctx,
        "raw": stdout[:4000],
        "timestamp": datetime.now().isoformat(),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--ngl", type=int, default=99)
    parser.add_argument("--ctx", type=int, default=131072)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    result = run_bench(args.model, args.ngl, args.ctx, args.threads, reps=args.reps)

    print(f"[speed] PP: {result['pp_tps']:.1f} t/s  TG: {result['tg_tps']:.1f} t/s" if result['pp_tps'] else "[speed] parse failed, check raw output")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2))
        print(f"[speed] Results saved to {args.output}")
    else:
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
