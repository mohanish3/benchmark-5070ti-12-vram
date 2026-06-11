$env:PYTHONUTF8 = "1"
$log = "benchmarks\pipeline.log"
$models = "gemma4-12b-q4km,qwen35-9b-glm51-q4km,omnicoder-9b-q4km,qwen35-9b-opus-distill-q4km,lfm25-8b-q6km,qwopus35-9b-coder-mtp-q4km"

function Log($msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    "$ts $msg" | Tee-Object -FilePath $log -Append
}

Log "=== RTX 5070 Ti expanded benchmark start ==="
.\benchmarks\run_benchmark.ps1 -SkipConvert -Expanded -ForceRerun -ModelsOnly $models *>&1 | Tee-Object -FilePath $log -Append
Log "=== RTX 5070 Ti expanded benchmark complete ==="
