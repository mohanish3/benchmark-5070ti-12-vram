$speedLog = "benchmarks\speed_rerun.log"
$safetensorsLog = "benchmarks\safetensors_run.log"

Write-Host "[queue] Waiting for speed rerun to finish..."
while (-not (Select-String -Path $speedLog -Pattern "=== DONE ===" -Quiet -ErrorAction SilentlyContinue)) {
    Start-Sleep -Seconds 15
}

Write-Host "[queue] Speed rerun done. Rerunning gemma4-12b-q4km coding (missed in speed pass)..."
$env:PYTHONUTF8 = "1"
.\benchmarks\run_benchmark.ps1 -SkipConvert -ModelsOnly "gemma4-12b-q4km" 2>&1 | Tee-Object -FilePath "benchmarks\gemma_coding_rerun.log"

Write-Host "[queue] gemma4-12b-q4km done. Launching safetensors benchmark..."
.\benchmarks\run_benchmark.ps1 -ModelsOnly "omnicoder-9b-q4km,qwopus35-9b-coder-q4km,qwen35-9b-opus-distill-q4km,lfm25-8b-q6km" 2>&1 | Tee-Object -FilePath $safetensorsLog
Write-Host "[queue] Safetensors run complete."
