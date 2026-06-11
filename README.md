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

Expanded run: speed 3 reps, tool calls 30 tests including 5 multi-tool cases, coding 20 HumanEval problems, reasoning 50 GSM8K problems.

| Model | PP t/s | TG t/s | Speed reps | Tool overall | Multi-tool | Coding | Reasoning |
|---|---:|---:|---:|---:|---:|---:|---:|
| `gemma4-12b-q4km` | 2252.9 | 51.5 | 3 | 88.3% | 80.0% (4/5) | 30.0% (6/20) | 98.0% (49/50) |
| `qwen35-9b-glm51-q4km` | 2980.8 | 80.2 | 3 | 90.0% | 100.0% (5/5) | 75.0% (15/20) | 90.0% (45/50) |
| `omnicoder-9b-q4km` | 3208.8 | 78.5 | 3 | 93.3% | 100.0% (5/5) | 95.0% (19/20) | 56.0% (28/50) |
| `qwen35-9b-opus-distill-q4km` | 2987.3 | 79.9 | 3 | 93.3% | 100.0% (5/5) | 80.0% (16/20) | 92.0% (46/50) |
| `lfm25-8b-q6km` | 7668.2 | 265.3 | 3 | 83.3% | 80.0% (4/5) | 55.0% (11/20) | 88.0% (44/50) |
| `qwopus35-9b-coder-mtp-q4km` | 2958.0 | 78.6 | 3 | 91.7% | 90.0% (4/5) | 75.0% (15/20) | 92.0% (46/50) |

Notable failure: `lfm25-8b-q6km` failed one multi-tool case, `T28` (`send_email` + `create_calendar_event`), with llama-server HTTP 500.

## Model Files

Model files are not stored in this repo. Put GGUF files under a model root with this layout:

```text
<MODEL_ROOT>/
  bench-models/
    gemma4-12b-q4km/
      gemma-4-12b-it-Q4_K_M.gguf
    qwen35-9b-glm51-distill-q4km/
      Qwen3.5-9B-GLM5.1-Distill-v1-Q4_K_M.gguf
    omnicoder-9b-q4km/
      omnicoder-9b-q4_k_m.gguf
    qwen35-9b-opus-distill-q4km/
      Qwen3.5-9B.Q4_K_M.gguf
    lfm25-8b-q6km/
      LFM2.5-8B-A1B-Q6_K.gguf
    qwopus35-9b-coder-q4km/
      Qwopus3.5-9B-Coder-MTP-Q4_K_M.gguf
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
.\benchmarks\run_benchmark.ps1 -Expanded -ForceRerun -ModelsOnly "gemma4-12b-q4km,qwen35-9b-glm51-q4km,omnicoder-9b-q4km,qwen35-9b-opus-distill-q4km,lfm25-8b-q6km,qwopus35-9b-coder-mtp-q4km"
```

Generated run output goes under `benchmarks/results/<model>/`.

Published result artifacts:

- `results/expanded_benchmark_summary.json`
- `results/benchmark_tests.json`
- `results/json/<model>/`
