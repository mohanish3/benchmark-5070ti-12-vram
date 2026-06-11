# Expanded Benchmark Results

Expanded run: speed 3 reps, toolcall 30 tests including 5 multi-tool cases, coding 20 HumanEval problems, reasoning 50 GSM8K problems.

| Model | PP t/s | TG t/s | Speed reps | Tool overall | Multi-tool | Coding | Reasoning |
|---|---:|---:|---:|---:|---:|---:|---:|
| `gemma4-12b-q4km` | 2252.9 | 51.5 | 3 | 88.3% | 80.0% (4/5) | 30.0% (6/20) | 98.0% (49/50) |
| `qwen35-9b-glm51-q4km` | 2980.8 | 80.2 | 3 | 90.0% | 100.0% (5/5) | 75.0% (15/20) | 90.0% (45/50) |
| `omnicoder-9b-q4km` | 3208.8 | 78.5 | 3 | 93.3% | 100.0% (5/5) | 95.0% (19/20) | 56.0% (28/50) |
| `qwen35-9b-opus-distill-q4km` | 2987.3 | 79.9 | 3 | 93.3% | 100.0% (5/5) | 80.0% (16/20) | 92.0% (46/50) |
| `lfm25-8b-q6km` | 7668.2 | 265.3 | 3 | 83.3% | 80.0% (4/5) | 55.0% (11/20) | 88.0% (44/50) |
| `qwopus35-9b-coder-mtp-q4km` | 2958.0 | 78.6 | 3 | 91.7% | 90.0% (4/5) | 75.0% (15/20) | 92.0% (46/50) |
