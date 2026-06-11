"""
Reasoning benchmark: GSM8K subset (50 problems) with chain-of-thought.
Downloads from HuggingFace datasets. Evaluates answer extraction accuracy.
Usage: python bench_reasoning.py --base-url http://127.0.0.1:8080/v1 --model <alias> [--output results.json] [--limit 50]
"""
import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from openai import OpenAI

SYSTEM_PROMPT = """You are a math problem solver. Work through the problem step by step.
At the end, write your final numerical answer on a new line starting with exactly: ANSWER: <number>
No units, no explanation after the number."""


def load_gsm8k(limit: int = 50) -> list:
    """Load GSM8K test set from HuggingFace datasets."""
    try:
        from datasets import load_dataset
        ds = load_dataset("gsm8k", "main", split="test")
        samples = list(ds.select(range(min(limit, len(ds)))))
        return [{"question": s["question"], "answer": s["answer"]} for s in samples]
    except Exception as e:
        print(f"[reasoning] WARNING: Failed to load GSM8K from HF: {e}")
        print("[reasoning] Using embedded fallback set (20 problems)")
        return FALLBACK_PROBLEMS[:limit]


def extract_answer(text: str) -> str | None:
    """Extract final numeric answer from model response."""
    # Primary: look for "ANSWER: <num>"
    m = re.search(r"ANSWER:\s*([+-]?\d+(?:,\d{3})*(?:\.\d+)?)", text, re.IGNORECASE)
    if m:
        return m.group(1).replace(",", "").strip()
    # Secondary: last number in response
    nums = re.findall(r"([+-]?\d+(?:,\d{3})*(?:\.\d+)?)", text)
    if nums:
        return nums[-1].replace(",", "").strip()
    return None


def extract_gt_answer(answer_field: str) -> str:
    """Extract numeric answer from GSM8K answer field (#### <num>)."""
    m = re.search(r"####\s*([+-]?\d+(?:,\d{3})*(?:\.\d+)?)", answer_field)
    if m:
        return m.group(1).replace(",", "").strip()
    # fallback: last number
    nums = re.findall(r"([+-]?\d+(?:,\d{3})*(?:\.\d+)?)", answer_field)
    if nums:
        return nums[-1].replace(",", "").strip()
    return answer_field.strip()


def answers_match(pred: str | None, gt: str) -> bool:
    if pred is None:
        return False
    try:
        return abs(float(pred) - float(gt)) < 1e-3
    except ValueError:
        return pred.strip().lower() == gt.strip().lower()


def run_reasoning_bench(base_url: str, model: str, limit: int = 50, timeout: int = 180) -> dict:
    client = OpenAI(base_url=base_url, api_key="not-needed")
    problems = load_gsm8k(limit)
    results = []
    correct = 0

    for i, problem in enumerate(problems):
        q = problem["question"]
        gt_raw = problem["answer"]
        gt = extract_gt_answer(gt_raw)

        print(f"  [Q{i+1:02d}/{len(problems)}] {q[:60]}...", end="", flush=True)
        t0 = time.time()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": q},
                ],
                max_tokens=2048,
                temperature=0.0,
                timeout=timeout,
            )
            raw = response.choices[0].message.content or ""
            elapsed = time.time() - t0
            pred = extract_answer(raw)
            match = answers_match(pred, gt)
            if match:
                correct += 1

            icon = "✓" if match else "✗"
            print(f" {icon} pred={pred} gt={gt} ({elapsed:.1f}s)")

            results.append({
                "idx": i,
                "question": q[:200],
                "gt": gt,
                "pred": pred,
                "correct": match,
                "latency_s": round(elapsed, 2),
                "response_len": len(raw),
            })
        except Exception as e:
            elapsed = time.time() - t0
            print(f" ERROR: {str(e)[:60]}")
            results.append({
                "idx": i,
                "question": q[:200],
                "gt": gt,
                "pred": None,
                "correct": False,
                "latency_s": round(elapsed, 2),
                "error": str(e)[:200],
            })

    acc = correct / max(len(results), 1)
    return {
        "accuracy": round(acc, 4),
        "n_correct": correct,
        "n_total": len(results),
        "details": results,
        "timestamp": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Fallback: 20 embedded GSM8K-style problems if dataset unavailable
# ---------------------------------------------------------------------------

FALLBACK_PROBLEMS = [
    {"question": "Janet's ducks lay 16 eggs per day. She eats 3 for breakfast and bakes muffins with 4933 each morning. She sells the rest for $2 per egg. How much does she make per day?", "answer": "18 #### 18"},
    {"question": "A robe takes 2 bolts of blue fiber and half that much white fiber. How many bolts does it take in total?", "answer": "3 #### 3"},
    {"question": "Josh decides to try flipping a house. He buys a house for $80,000 and does $50,000 in repairs. He sells it for 1.5 times what he paid combined. How much profit does he make?", "answer": "45000 #### 45000"},
    {"question": "There are 15 trees in the grove. Grove workers will plant trees today. After planting, there will be 21 trees. How many trees did they plant?", "answer": "6 #### 6"},
    {"question": "Leah had 32 chocolates and her sister had 42. If they ate 35, how many are left?", "answer": "39 #### 39"},
    {"question": "Jason had 20 lollipops. He gave some to Denny, now has 12. How many did he give?", "answer": "8 #### 8"},
    {"question": "Shawn has 5 toys. For Christmas, he got 2 from mom and 2 from dad. How many does he have now?", "answer": "9 #### 9"},
    {"question": "There were 9 computers in the server room. Each day 5 more are installed. After 4 days, how many computers?", "answer": "29 #### 29"},
    {"question": "Michael had 58 golf balls. On Tuesday, he lost 23. On Wednesday, he lost 2. How many are left?", "answer": "33 #### 33"},
    {"question": "Olivia has $23. She bought 5 bagels at $3 each. How much does she have left?", "answer": "8 #### 8"},
    {"question": "A store had 3 boxes of apples with 15 apples each. They sold 12 apples. How many are left?", "answer": "33 #### 33"},
    {"question": "Maria has 3 bags with 6 cookies each, plus 2 bags with 9 cookies each. How many cookies total?", "answer": "36 #### 36"},
    {"question": "Tom has 12 toys. He gives away a third of them. How many does he have?", "answer": "8 #### 8"},
    {"question": "A train travels 60 mph. How far does it go in 2.5 hours?", "answer": "150 #### 150"},
    {"question": "A rectangle is 8 cm wide and 5 cm tall. What is its area?", "answer": "40 #### 40"},
    {"question": "There are 24 students and each table seats 6. How many tables are needed?", "answer": "4 #### 4"},
    {"question": "A book has 300 pages. Sam reads 25 pages per day. How many days to finish?", "answer": "12 #### 12"},
    {"question": "A store sells apples for $0.50 each. If you buy 8, how much do you pay?", "answer": "4 #### 4"},
    {"question": "Mark earns $12 per hour. How much does he earn in a 40-hour week?", "answer": "480 #### 480"},
    {"question": "A class of 30 students. 40% are boys. How many girls?", "answer": "18 #### 18"},
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--limit", type=int, default=15)  # 15 keeps runtime ~3 min for 9B, ~7 min for 35B
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    print(f"[reasoning] Benchmarking GSM8K ({args.limit} problems): {args.model}")
    result = run_reasoning_bench(args.base_url, args.model, args.limit, args.timeout)

    print(f"\n[reasoning] Accuracy: {result['accuracy']:.1%}  ({result['n_correct']}/{result['n_total']})")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2))
        print(f"[reasoning] Saved to {args.output}")
    else:
        print(json.dumps({k: v for k, v in result.items() if k != "details"}, indent=2))

if __name__ == "__main__":
    main()
