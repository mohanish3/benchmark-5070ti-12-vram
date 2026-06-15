# Model Benchmark Report
Generated: 2026-06-15 05:41

## Summary

| Model | PP tok/s | TG tok/s | Tool acc | Param acc | Code pass@1 | GSM8K acc | NGL |
|-------|----------|----------|----------|-----------|-------------|-----------|-----|
| gemma4-12b-coder-q4km | 1302 | 30 | 75.0% | 66.7% | 90.0% | 86.7% | 99 |
| gemma4-12b-q4km | 2475 | 52 | 92.6% | 88.9% | 30.0% | 98.0% | 99 |
| gemma4-12b-q5km | 2396 | 47 | 92.6% | 88.9% | 35.0% | 98.0% | 99 |
| gemma4-12b-qat-q4kxl | 2737 | 59 | 91.7% | 91.7% | 40.0% | 80.0% | 99 |
| lfm25-8b-q6km | 7668 | 265 | 81.5% | 81.5% | 55.0% | 88.0% | 99 |
| lfm25-8b-q8 | 9624 | 222 | 81.5% | 81.5% | 60.0% | 96.0% | 99 |
| omnicoder-9b-q4km | 3089 | 78 | 96.3% | 96.3% | 95.0% | 56.0% | 99 |
| omnicoder-9b-q5km | 3165 | 71 | 100.0% | 96.3% | 85.0% | 66.0% | 99 |
| qwen35-9b-glm51-distill-q5km | 2863 | 69 | 96.3% | 96.3% | 85.0% | 92.0% | 99 |
| qwen35-9b-glm51-q4km | 2981 | 80 | 92.6% | 92.6% | 75.0% | 90.0% | 99 |
| qwen35-9b-opus-distill-q4km | 3082 | 80 | 92.6% | 92.6% | 80.0% | 92.0% | 99 |
| qwen35-9b-opus-distill-q5km | 3178 | 70 | 96.3% | 96.3% | 65.0% | 98.0% | 99 |
| qwopus35-9b-coder-mtp-q4km | 2958 | 79 | 92.6% | 88.9% | 75.0% | 92.0% | 99 |

## Speed (PP = prefill, TG = generation, 512 tok)

| Model | PP tok/s | TG tok/s | NGL | Notes |
|-------|----------|----------|-----|-------|
| gemma4-12b-coder-q4km | 1302.2 | 30.5 | 99 | Full GPU; 128k ctx |
| gemma4-12b-q4km | 2474.5 | 52.1 | 99 | Full GPU; 128k ctx |
| gemma4-12b-q5km | 2396.0 | 46.6 | 99 | Full GPU; 128k ctx |
| gemma4-12b-qat-q4kxl | 2737.4 | 58.8 | 99 | Full GPU; legacy speed |
| lfm25-8b-q6km | 7668.2 | 265.3 | 99 | Full GPU; legacy speed |
| lfm25-8b-q8 | 9623.9 | 222.3 | 99 | Full GPU; 128k ctx |
| omnicoder-9b-q4km | 3089.2 | 77.8 | 99 | Full GPU; 128k ctx |
| omnicoder-9b-q5km | 3165.4 | 70.5 | 99 | Full GPU; 128k ctx |
| qwen35-9b-glm51-distill-q5km | 2862.7 | 69.2 | 99 | Full GPU; 128k ctx |
| qwen35-9b-glm51-q4km | 2980.8 | 80.2 | 99 | Full GPU; legacy speed |
| qwen35-9b-opus-distill-q4km | 3082.1 | 79.9 | 99 | Full GPU; 128k ctx |
| qwen35-9b-opus-distill-q5km | 3178.4 | 70.4 | 99 | Full GPU; 128k ctx |
| qwopus35-9b-coder-mtp-q4km | 2958.0 | 78.6 | 99 | Full GPU; legacy speed |

## Agentic Tool Calling (30 tests)

| Model | Tool acc | Param acc | No-tool acc | Overall |
|-------|----------|-----------|-------------|---------|
| gemma4-12b-coder-q4km | 75.0% | 66.7% | 66.7% | 70.0% |
| gemma4-12b-q4km | 92.6% | 88.9% | 66.7% | 88.3% |
| gemma4-12b-q5km | 92.6% | 88.9% | 66.7% | 88.3% |
| gemma4-12b-qat-q4kxl | 91.7% | 91.7% | 66.7% | 86.7% |
| lfm25-8b-q6km | 81.5% | 81.5% | 100.0% | 83.3% |
| lfm25-8b-q8 | 81.5% | 81.5% | 100.0% | 83.3% |
| omnicoder-9b-q4km | 96.3% | 96.3% | 66.7% | 93.3% |
| omnicoder-9b-q5km | 100.0% | 96.3% | 100.0% | 98.3% |
| qwen35-9b-glm51-distill-q5km | 96.3% | 96.3% | 100.0% | 96.7% |
| qwen35-9b-glm51-q4km | 92.6% | 92.6% | 66.7% | 90.0% |
| qwen35-9b-opus-distill-q4km | 92.6% | 92.6% | 100.0% | 93.3% |
| qwen35-9b-opus-distill-q5km | 96.3% | 96.3% | 100.0% | 96.7% |
| qwopus35-9b-coder-mtp-q4km | 92.6% | 88.9% | 100.0% | 91.7% |

## Coding (HumanEval subset, 20 problems)

| Model | pass@1 | Passed/Total |
|-------|--------|--------------|
| gemma4-12b-coder-q4km | 90.0% | 9/10 |
| gemma4-12b-q4km | 30.0% | 6/20 |
| gemma4-12b-q5km | 35.0% | 7/20 |
| gemma4-12b-qat-q4kxl | 40.0% | 4/10 |
| lfm25-8b-q6km | 55.0% | 11/20 |
| lfm25-8b-q8 | 60.0% | 12/20 |
| omnicoder-9b-q4km | 95.0% | 19/20 |
| omnicoder-9b-q5km | 85.0% | 17/20 |
| qwen35-9b-glm51-distill-q5km | 85.0% | 17/20 |
| qwen35-9b-glm51-q4km | 75.0% | 15/20 |
| qwen35-9b-opus-distill-q4km | 80.0% | 16/20 |
| qwen35-9b-opus-distill-q5km | 65.0% | 13/20 |
| qwopus35-9b-coder-mtp-q4km | 75.0% | 15/20 |

## Reasoning (GSM8K, 50 problems)

| Model | Accuracy | Correct/Total |
|-------|----------|---------------|
| gemma4-12b-coder-q4km | 86.7% | 13/15 |
| gemma4-12b-q4km | 98.0% | 49/50 |
| gemma4-12b-q5km | 98.0% | 49/50 |
| gemma4-12b-qat-q4kxl | 80.0% | 12/15 |
| lfm25-8b-q6km | 88.0% | 44/50 |
| lfm25-8b-q8 | 96.0% | 48/50 |
| omnicoder-9b-q4km | 56.0% | 28/50 |
| omnicoder-9b-q5km | 66.0% | 33/50 |
| qwen35-9b-glm51-distill-q5km | 92.0% | 46/50 |
| qwen35-9b-glm51-q4km | 90.0% | 45/50 |
| qwen35-9b-opus-distill-q4km | 92.0% | 46/50 |
| qwen35-9b-opus-distill-q5km | 98.0% | 49/50 |
| qwopus35-9b-coder-mtp-q4km | 92.0% | 46/50 |

---
*Benchmarks run with llama.cpp SM120 build, RTX 5070 Ti Laptop GPU (12GB)*