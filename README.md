# RTX 5070 Ti 12GB VRAM Local LLM Benchmarks

Benchmarks for local GGUF models on a laptop NVIDIA GeForce RTX 5070 Ti GPU with 12 GB VRAM.

This repo is meant to help people with similar hardware understand expected local model speed and quality tradeoffs.

## Hardware

- GPU: NVIDIA GeForce RTX 5070 Ti Laptop GPU, 12 GB VRAM
- CPU: Intel Core Ultra 9 275HX
- OS: Windows
- Runtime: llama.cpp
- Speed binary: `tools/llama-cpp-cuda-b9509/llama-bench.exe`
- Server binary: `tools/llama.cpp-sm120-src/build-sm120/bin/Release/llama-server.exe`

## Model Storage

Model files are not stored in this repo.

Model files are expected under a model root containing `bench-models/`.
The runner auto-detects a few sibling workspace layouts, but the most
portable option is to set `MODEL_ROOT` before running:

```powershell
$env:MODEL_ROOT = "C:\path\to\Agent Crew Models"
```

Required local GGUF files:

| Model ID | Expected GGUF |
|---|---|
| `gemma4-12b-q4km` | `$MODEL_ROOT/bench-models/gemma4-12b-q4km/gemma-4-12b-it-Q4_K_M.gguf` |
| `qwen35-9b-glm51-q4km` | `$MODEL_ROOT/bench-models/qwen35-9b-glm51-distill-q4km/Qwen3.5-9B-GLM5.1-Distill-v1-Q4_K_M.gguf` |
| `omnicoder-9b-q4km` | `$MODEL_ROOT/bench-models/omnicoder-9b-q4km/omnicoder-9b-q4_k_m.gguf` |
| `qwen35-9b-opus-distill-q4km` | `$MODEL_ROOT/bench-models/qwen35-9b-opus-distill-q4km/Qwen3.5-9B.Q4_K_M.gguf` |
| `lfm25-8b-q6km` | `$MODEL_ROOT/bench-models/lfm25-8b-q6km/LFM2.5-8B-A1B-Q6_K.gguf` |
| `qwopus35-9b-coder-mtp-q4km` | `$MODEL_ROOT/bench-models/qwopus35-9b-coder-q4km/Qwopus3.5-9B-Coder-MTP-Q4_K_M.gguf` |

Excluded:

- `gemma-4-12B-it-qat-UD-Q4_K_XL.gguf`
- `qwopus35-9b-coder-q4km` standalone model

## Benchmarks

Copied scripts live in `benchmarks/`.

| Script | Purpose |
|---|---|
| `bench_speed.py` | llama-bench PP/TG speed, expanded run uses 3 reps |
| `bench_toolcall.py` | Tool-call benchmark, expanded run uses 30 tests including multi-tool calls |
| `bench_coding.py` | HumanEval subset, expanded run uses all 20 embedded problems |
| `bench_reasoning.py` | GSM8K, expanded run uses 50 problems |
| `run_benchmark.ps1` | Windows orchestrator for local GGUF models |
| `run_pipeline.ps1` | Convenience wrapper for queued runs |
| `queue_safetensors.ps1` | Optional queue helper for safetensors models |
| `report.py` | Markdown/JSON report generator |

## Run

Set `MODEL_ROOT`, then run:

```powershell
$env:MODEL_ROOT = "C:\path\to\Agent Crew Models"
.\benchmarks\run_benchmark.ps1 -SkipConvert -Expanded -ForceRerun -ModelsOnly "gemma4-12b-q4km,qwen35-9b-glm51-q4km,omnicoder-9b-q4km,qwen35-9b-opus-distill-q4km,lfm25-8b-q6km,qwopus35-9b-coder-mtp-q4km"
```

Results are JSON files under `benchmarks/results/<model>/`.

Published tabular summary is in `results/expanded_benchmark_results.md`.
The benchmark test manifest is in `results/benchmark_tests.json`.
