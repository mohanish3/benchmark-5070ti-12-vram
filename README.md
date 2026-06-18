# RTX 5070 Ti 12GB VRAM Local LLM Benchmarks

Benchmarks for local GGUF models on a laptop NVIDIA GeForce RTX 5070 Ti GPU with 12 GB VRAM.

Goal: help people with similar hardware compare local model speed, coding, reasoning, and tool-call behavior.

## Hardware

- GPU: NVIDIA GeForce RTX 5070 Ti Laptop GPU, 12 GB VRAM
- CPU: Intel Core Ultra 9 275HX
- OS: Windows
- Runtime: llama.cpp
- Speed binary: `tools/llama-cpp-cuda-b9509/llama-bench.exe`
- Server binary: `tools/llama.cpp-sm120-src/build-sm120/bin/Release/llama-server.exe`

## Results

Expanded run: speed 3 reps, toolcall 30 tests including 5 multi-tool cases, coding 20 HumanEval problems, reasoning 50 GSM8K problems.

Speed test now enforces 128k context for newly generated rows (`fit_min_ctx = 131072`). Retained legacy rows have `fit_min_ctx = null` in the JSON summary.

| Model | PP t/s | TG t/s | Speed reps | Tool overall | Multi-tool | Coding | Reasoning |
|---|---:|---:|---:|---:|---:|---:|---:|
| `gemma4-12b-q4km` | 2474.5 | 52.1 | 3 | 88.3% | 80.0% (4/5) | 30.0% (6/20) | 98.0% (49/50) |
| `gemma4-12b-q5km` | 2396.0 | 46.6 | 3 | 88.3% | 80.0% (4/5) | 35.0% (7/20) | 98.0% (49/50) |
| `gemma4-12b-q6k` | 1474.1 | 36.5 | 3 | 88.3% | 80.0% (4/5) | 30.0% (6/20) | 98.0% (49/50) |
| `gemma4-12b-coder-q4km` | 1881.2 | 42.3 | 3 | 83.3% | 100.0% (5/5) | 70.0% (14/20) | 96.0% (48/50) |
| `qwen35-9b-glm51-q4km` | 2980.8 | 80.2 | 3 | 90.0% | 100.0% (5/5) | 75.0% (15/20) | 90.0% (45/50) |
| `qwen35-9b-glm51-distill-q5km` | 2862.7 | 69.2 | 3 | 96.7% | 100.0% (5/5) | 85.0% (17/20) | 92.0% (46/50) |
| `omnicoder-9b-q4km` | 3089.2 | 77.8 | 3 | 93.3% | 100.0% (5/5) | 95.0% (19/20) | 56.0% (28/50) |
| `omnicoder-9b-q5km` | 3165.4 | 70.5 | 3 | 98.3% | 100.0% (5/5) | 85.0% (17/20) | 66.0% (33/50) |
| `omnicoder-9b-q6k` | 2786.3 | 64.6 | 3 | 100.0% | 100.0% (5/5) | 70.0% (14/20) | 76.0% (38/50) |
| `qwen35-9b-opus-distill-q4km` | 3082.1 | 79.9 | 3 | 93.3% | 100.0% (5/5) | 80.0% (16/20) | 92.0% (46/50) |
| `qwen35-9b-opus-distill-q5km` | 3178.4 | 70.4 | 3 | 96.7% | 100.0% (5/5) | 65.0% (13/20) | 98.0% (49/50) |
| `lfm25-8b-q6km` | 7668.2 | 265.3 | 3 | 83.3% | 80.0% (4/5) | 55.0% (11/20) | 88.0% (44/50) |
| `lfm25-8b-q8` | 9623.9 | 222.3 | 3 | 83.3% | 80.0% (4/5) | 60.0% (12/20) | 96.0% (48/50) |
| `qwopus35-9b-coder-mtp-q4km` | 2958.0 | 78.6 | 3 | 91.7% | 80.0% (4/5) | 75.0% (15/20) | 92.0% (46/50) |
| `vibethinker-3b-bf16` | 5453.3 | 71.2 | 3 | 10.0% | 0.0% (0/5) | 5.0% (1/20) | 100.0% (50/50) |

VibeThinker note: `vibethinker-3b-bf16` reasoned perfectly on GSM8K but did not emit callable tool markup in tool tests, so tool and param accuracy were 0%.

Notable failures: `lfm25-8b-q6km` and `lfm25-8b-q8` each failed one multi-tool case, `T28` (`send_email` + `create_calendar_event`), with llama-server HTTP 500. `gemma4-12b-q5km` failed `T30` (multi-tool: reminder + unit conversion) and `T18` (translate Japanese). `gemma4-12b-coder-q4km` failed `T05`/`T18` (translate — answered directly instead of calling tool) and `T16` (percent calculation — answered directly) and `T21` (no-tool basic math — called `calculate` when it shouldn't).

## Model Files

Model files are not stored in this repo. Put GGUF files under a model root with this layout:

```text
<MODEL_ROOT>/
  bench-models/
    gemma4-12b-q4km/
      gemma-4-12b-it-Q4_K_M.gguf
    gemma4-12b-q5km/
      gemma-4-12b-it-Q5_K_M.gguf
    gemma4-12b-coder-q4km/
      gemma4-coding-Q4_K_M.gguf
    qwen35-9b-glm51-distill-q4km/
      Qwen3.5-9B-GLM5.1-Distill-v1-Q4_K_M.gguf
    qwen35-9b-glm51-distill-q5km/
      Qwen3.5-9B-GLM5.1-Distill-v1-Q5_K_M.gguf
    omnicoder-9b-q4km/
      omnicoder-9b-q4_k_m.gguf
    omnicoder-9b-q5km/
      omnicoder-9b-q5_k_m.gguf
    omnicoder-9b-q6k/
      omnicoder-9b-q6_k.gguf
    qwen35-9b-opus-distill-q4km/
      Qwen3.5-9B.Q4_K_M.gguf
    qwen35-9b-opus-distill-q5km/
      Qwen3.5-9B.Q5_K_M.gguf
    lfm25-8b-q6km/
      LFM2.5-8B-A1B-Q6_K.gguf
    lfm25-8b-q8/
      LFM2.5-8B-A1B-Q8_0.gguf
    qwopus35-9b-coder-q4km/
      Qwopus3.5-9B-Coder-MTP-Q4_K_M.gguf
    vibethinker-3b-bf16/
      VibeThinker-3B-BF16.gguf
```

Create `.env` from `.env.example`:

```powershell
Copy-Item .env.example .env
```

Then edit:

```text
MODEL_ROOT=C:\path\to\models
```

Excluded from benchmark set:

- `gemma-4-12B-it-qat-UD-Q4_K_XL.gguf`
- standalone `qwopus35-9b-coder-q4km`

## Scripts

| Script | Purpose |
|---|---|
| `benchmarks/run_benchmark.ps1` | Windows orchestrator for local GGUF benchmark run |
| `benchmarks/bench_speed.py` | llama-bench PP/TG speed |
| `benchmarks/bench_toolcall.py` | Tool-call benchmark, including multi-tool cases |
| `benchmarks/bench_coding.py` | HumanEval coding benchmark |
| `benchmarks/bench_reasoning.py` | GSM8K reasoning benchmark |
| `benchmarks/report.py` | Markdown/JSON report generator |

## Run

```powershell
.\benchmarks\run_benchmark.ps1 -Expanded -ForceRerun -ModelsOnly "gemma4-12b-q4km,qwen35-9b-glm51-q4km,qwen35-9b-glm51-distill-q5km,omnicoder-9b-q4km,omnicoder-9b-q5km,qwen35-9b-opus-distill-q4km,qwen35-9b-opus-distill-q5km,lfm25-8b-q6km,lfm25-8b-q8,qwopus35-9b-coder-mtp-q4km,vibethinker-3b-bf16"
```

Generated run output goes under `benchmarks/results/<model>/`.

Published result artifacts:

- `results/expanded_benchmark_summary.json`
- `results/benchmark_tests.json`
- `results/json/<model>/`
