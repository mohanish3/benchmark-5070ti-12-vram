# Expanded Benchmark Results

Expanded run: speed 3 reps, toolcall 30 tests including 5 multi-tool cases, coding 20 HumanEval problems, reasoning 50 GSM8K problems.

Speed test now enforces 128k context for newly generated rows (`fit_min_ctx = 131072`). Retained legacy rows have `fit_min_ctx = null` in the JSON summary.

| Model | PP t/s | TG t/s | Speed reps | Tool overall | Multi-tool | Coding | Reasoning |
|---|---:|---:|---:|---:|---:|---:|---:|
| `gemma4-12b-q4km` | 2474.5 | 52.1 | 3 | 88.3% | 80.0% (4/5) | 30.0% (6/20) | 98.0% (49/50) |
| `qwen35-9b-glm51-q4km` | 2980.8 | 80.2 | 3 | 90.0% | 100.0% (5/5) | 75.0% (15/20) | 90.0% (45/50) |
| `qwen35-9b-glm51-distill-q5km` | 2862.7 | 69.2 | 3 | 96.7% | 100.0% (5/5) | 85.0% (17/20) | 92.0% (46/50) |
| `omnicoder-9b-q4km` | 3089.2 | 77.8 | 3 | 93.3% | 100.0% (5/5) | 95.0% (19/20) | 56.0% (28/50) |
| `omnicoder-9b-q5km` | 3165.4 | 70.5 | 3 | 98.3% | 100.0% (5/5) | 85.0% (17/20) | 66.0% (33/50) |
| `qwen35-9b-opus-distill-q4km` | 3082.1 | 79.9 | 3 | 93.3% | 100.0% (5/5) | 80.0% (16/20) | 92.0% (46/50) |
| `qwen35-9b-opus-distill-q5km` | 3178.4 | 70.4 | 3 | 96.7% | 100.0% (5/5) | 65.0% (13/20) | 98.0% (49/50) |
| `lfm25-8b-q6km` | 7668.2 | 265.3 | 3 | 83.3% | 80.0% (4/5) | 55.0% (11/20) | 88.0% (44/50) |
| `lfm25-8b-q8` | 9623.9 | 222.3 | 3 | 83.3% | 80.0% (4/5) | 60.0% (12/20) | 96.0% (48/50) |
| `qwopus35-9b-coder-mtp-q4km` | 2958.0 | 78.6 | 3 | 91.7% | 90.0% (4/5) | 75.0% (15/20) | 92.0% (46/50) |
