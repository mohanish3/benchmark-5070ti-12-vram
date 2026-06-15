<#
.SYNOPSIS
  Local GGUF benchmark suite: speed -> tool-call -> coding -> reasoning.

.DESCRIPTION
  Benchmarks local GGUF models listed in the registry below.
  Set MODEL_ROOT in .env to the directory that contains bench-models/.

.PARAMETER ModelsOnly
  Comma-separated model IDs to run.

.PARAMETER SkipSpeed
  Skip speed benchmark.

.PARAMETER ForceRerun
  Re-run even when result JSON files already exist.

.PARAMETER Expanded
  Speed 3 reps, tool calls 30, coding 20 HumanEval, reasoning 50 GSM8K.
#>
param(
    [string]$ModelsOnly = "",
    [switch]$SkipSpeed,
    [switch]$ForceRerun,
    [switch]$Expanded
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

$ROOT      = Split-Path $PSScriptRoot -Parent
$BENCH_DIR = $PSScriptRoot
$RESULTS   = Join-Path $BENCH_DIR "results"
$ENV_FILE  = Join-Path $ROOT ".env"

function Import-DotEnv($path) {
    if (-not (Test-Path $path)) { return }
    foreach ($rawLine in (Get-Content $path)) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#") -or $line -notmatch "=") { continue }
        $key, $value = $line -split "=", 2
        $key = $key.Trim()
        $value = $value.Trim().Trim('"').Trim("'")
        if ($key) { [Environment]::SetEnvironmentVariable($key, $value, "Process") }
    }
}

Import-DotEnv $ENV_FILE

if (-not $env:MODEL_ROOT) {
    throw "MODEL_ROOT missing. Create .env with MODEL_ROOT=C:\path\to\models-root"
}

$MODEL_ROOT = $env:MODEL_ROOT
$MODELS_DIR = Join-Path $MODEL_ROOT "bench-models"

$SM120_BIN  = Join-Path $ROOT "tools\llama.cpp-sm120-src\build-sm120\bin\Release"
$CUDA_BIN   = Join-Path $ROOT "tools\llama-cpp-cuda-b9509"
$LLAMA_SRV  = Join-Path $SM120_BIN "llama-server.exe"
$LLAMA_BNH  = Join-Path $CUDA_BIN  "llama-bench.exe"

$LLAMA_PORT = 8090
$LLAMA_HOST = "127.0.0.1"

$MODELS = @(
    @{
        id          = "omnicoder-9b-q4km"
        display     = "Tesslate/OmniCoder-9B"
        file        = "omnicoder-9b-q4km\omnicoder-9b-q4_k_m.gguf"
        ngl         = 99
        ctx         = 131072
        threads     = 8
        cpu_offload = $false
    },
    @{
        id          = "omnicoder-9b-q5km"
        display     = "Tesslate/OmniCoder-9B Q5_K_M"
        file        = "omnicoder-9b-q5km\omnicoder-9b-q5_k_m.gguf"
        ngl         = 99
        ctx         = 131072
        threads     = 8
        cpu_offload = $false
    },
    @{
        id          = "qwopus35-9b-coder-mtp-q4km"
        display     = "Jackrong/Qwopus3.5-9B-Coder-MTP"
        file        = "qwopus35-9b-coder-q4km\Qwopus3.5-9B-Coder-MTP-Q4_K_M.gguf"
        ngl         = 99
        ctx         = 131072
        threads     = 8
        cpu_offload = $false
    },
    @{
        id          = "gemma4-12b-q4km"
        display     = "unsloth/gemma-4-12b-it"
        file        = "gemma4-12b-q4km\gemma-4-12b-it-Q4_K_M.gguf"
        ngl         = 99
        ctx         = 131072
        threads     = 8
        cpu_offload = $false
    },
    @{
        id          = "gemma4-12b-q5km"
        display     = "unsloth/gemma-4-12b-it Q5_K_M"
        file        = "gemma4-12b-q5km\gemma-4-12b-it-Q5_K_M.gguf"
        ngl         = 99
        ctx         = 131072
        threads     = 8
        cpu_offload = $false
    },
    @{
        id          = "qwen35-9b-opus-distill-q4km"
        display     = "Jackrong/Qwen3.5-9B Claude Opus Distill"
        file        = "qwen35-9b-opus-distill-q4km\Qwen3.5-9B.Q4_K_M.gguf"
        ngl         = 99
        ctx         = 131072
        threads     = 8
        cpu_offload = $false
    },
    @{
        id          = "qwen35-9b-opus-distill-q5km"
        display     = "Jackrong/Qwen3.5-9B Claude Opus Distill Q5_K_M"
        file        = "qwen35-9b-opus-distill-q5km\Qwen3.5-9B.Q5_K_M.gguf"
        ngl         = 99
        ctx         = 131072
        threads     = 8
        cpu_offload = $false
    },
    @{
        id          = "lfm25-8b-q6km"
        display     = "LiquidAI/LFM2.5-8B-A1B"
        file        = "lfm25-8b-q6km\LFM2.5-8B-A1B-Q6_K.gguf"
        ngl         = 99
        ctx         = 131072
        threads     = 8
        cpu_offload = $false
    },
    @{
        id          = "lfm25-8b-q8"
        display     = "LiquidAI/LFM2.5-8B-A1B Q8_0"
        file        = "lfm25-8b-q8\LFM2.5-8B-A1B-Q8_0.gguf"
        ngl         = 99
        ctx         = 131072
        threads     = 8
        cpu_offload = $false
    },
    @{
        id          = "qwen35-9b-glm51-q4km"
        display     = "Jackrong/Qwen3.5-9B GLM5.1 Distill"
        file        = "qwen35-9b-glm51-distill-q4km\Qwen3.5-9B-GLM5.1-Distill-v1-Q4_K_M.gguf"
        ngl         = 99
        ctx         = 131072
        threads     = 8
        cpu_offload = $false
    },
    @{
        id          = "qwen35-9b-glm51-distill-q5km"
        display     = "Jackrong/Qwen3.5-9B GLM5.1 Distill Q5_K_M"
        file        = "qwen35-9b-glm51-distill-q5km\Qwen3.5-9B-GLM5.1-Distill-v1-Q5_K_M.gguf"
        ngl         = 99
        ctx         = 131072
        threads     = 8
        cpu_offload = $false
    }
)

function Log($msg, $color = "Cyan") {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg" -ForegroundColor $color
}

function LogOk($msg)   { Log "[OK] $msg" "Green" }
function LogErr($msg)  { Log "[ERR] $msg" "Red" }
function LogWarn($msg) { Log "[WARN] $msg" "Yellow" }

function Invoke-NativeLogged($exe, $procArgs) {
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $exe @procArgs 2>&1 | ForEach-Object { Write-Host "$_" }
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldPreference
    }
}

function Stop-LlamaServer {
    Get-CimInstance Win32_Process |
        Where-Object { $_.Name -eq "llama-server.exe" -and $_.CommandLine -match "--port $LLAMA_PORT" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
}

function Wait-ServerReady($maxSec = 180) {
    for ($i = 0; $i -lt $maxSec; $i++) {
        try {
            Invoke-RestMethod "http://$LLAMA_HOST`:$LLAMA_PORT/v1/models" -TimeoutSec 2 | Out-Null
            return $true
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

function Resolve-ModelPath($model) {
    $path = Join-Path $MODELS_DIR $model.file
    if (-not (Test-Path $path)) {
        throw "Missing model file: $path"
    }
    return $path
}

function Start-LlamaServer($modelPath, $model) {
    Stop-LlamaServer

    $logOut = Join-Path $BENCH_DIR "llama-bench-server.out.log"
    $logErr = Join-Path $BENCH_DIR "llama-bench-server.err.log"

    $args = @(
        "-m", "`"$modelPath`"",
        "--host", $LLAMA_HOST,
        "--port", $LLAMA_PORT,
        "-c", $model.ctx,
        "-ngl", $model.ngl,
        "-t", $model.threads,
        "-n", "4096",
        "-b", "8192",
        "-ub", "1024",
        "-fa", "on",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "-a", $model.id,
        "--reasoning", "auto",
        "--reasoning-budget", "0",
        "--prio", "2",
        "--threads-http", "4",
        "--metrics",
        "--log-verbosity", "0",
        "--no-log-prefix",
        "--no-log-timestamps",
        "--jinja"
    )

    Log "Starting llama-server for $($model.id)..."
    Start-Process -FilePath $LLAMA_SRV -ArgumentList $args `
        -RedirectStandardOutput $logOut -RedirectStandardError $logErr `
        -WindowStyle Hidden | Out-Null

    if (-not (Wait-ServerReady)) {
        $err = Get-Content $logErr -Tail 20 -ErrorAction SilentlyContinue
        throw "llama-server not ready after 180s. Last errors:`n$err"
    }
    LogOk "Server ready at http://$LLAMA_HOST`:$LLAMA_PORT"
}

function Run-SpeedBench($model, $modelPath, $outDir) {
    $outFile = Join-Path $outDir "speed.json"
    if ((Test-Path $outFile) -and -not $ForceRerun) { LogOk "Speed exists, skipping"; return }
    $procArgs = @(
        "$BENCH_DIR\bench_speed.py",
        "--model", $modelPath,
        "--ngl", $model.ngl,
        "--ctx", $model.ctx,
        "--threads", $model.threads,
        "--output", $outFile,
        "--reps", $(if ($Expanded) { "3" } else { "1" })
    )
    $exitCode = Invoke-NativeLogged "python" $procArgs
    if ($exitCode -ne 0) { LogWarn "Speed bench returned exit $exitCode" } else { LogOk "Speed done" }
}

function Run-ToolCallBench($model, $outDir) {
    $outFile = Join-Path $outDir "toolcall.json"
    if ((Test-Path $outFile) -and -not $ForceRerun) { LogOk "Toolcall exists, skipping"; return }
    $nTests = if ($Expanded) { 30 } elseif ($model.cpu_offload) { 10 } else { 15 }
    $procArgs = @(
        "$BENCH_DIR\bench_toolcall.py",
        "--base-url", "http://$LLAMA_HOST`:$LLAMA_PORT/v1",
        "--model", $model.id,
        "--output", $outFile,
        "--timeout", "90",
        "--n-tests", $nTests
    )
    $exitCode = Invoke-NativeLogged "python" $procArgs
    if ($exitCode -ne 0) { LogWarn "Toolcall bench returned exit $exitCode" } else { LogOk "Toolcall done" }
}

function Run-CodingBench($model, $outDir) {
    $outFile = Join-Path $outDir "coding.json"
    if ((Test-Path $outFile) -and -not $ForceRerun) { LogOk "Coding exists, skipping"; return }
    $procArgs = @(
        "$BENCH_DIR\bench_coding.py",
        "--base-url", "http://$LLAMA_HOST`:$LLAMA_PORT/v1",
        "--model", $model.id,
        "--output", $outFile,
        "--timeout", "300"
    )
    if ($Expanded) { $procArgs += "--full" }
    $exitCode = Invoke-NativeLogged "python" $procArgs
    if ($exitCode -ne 0) { LogWarn "Coding bench returned exit $exitCode" } else { LogOk "Coding done" }
}

function Run-ReasoningBench($model, $outDir) {
    $outFile = Join-Path $outDir "reasoning.json"
    if ((Test-Path $outFile) -and -not $ForceRerun) { LogOk "Reasoning exists, skipping"; return }
    $limit = if ($Expanded) { 50 } elseif ($model.cpu_offload) { 8 } else { 15 }
    $procArgs = @(
        "$BENCH_DIR\bench_reasoning.py",
        "--base-url", "http://$LLAMA_HOST`:$LLAMA_PORT/v1",
        "--model", $model.id,
        "--limit", $limit,
        "--output", $outFile,
        "--timeout", "300"
    )
    $exitCode = Invoke-NativeLogged "python" $procArgs
    if ($exitCode -ne 0) { LogWarn "Reasoning bench returned exit $exitCode" } else { LogOk "Reasoning done" }
}

function Test-RequestedResultsExist($outDir) {
    $required = @("toolcall.json", "coding.json", "reasoning.json")
    if (-not $SkipSpeed) { $required += "speed.json" }
    foreach ($file in $required) {
        if (-not (Test-Path (Join-Path $outDir $file))) { return $false }
    }
    return $true
}

$targetModels = $MODELS
if ($ModelsOnly) {
    $ids = $ModelsOnly -split "," | ForEach-Object { $_.Trim() }
    $targetModels = @($MODELS | Where-Object { $ids -contains $_.id })
    if (-not $targetModels) {
        LogErr "No models matched: $ModelsOnly"
        exit 1
    }
}

foreach ($bin in @($LLAMA_SRV, $LLAMA_BNH)) {
    if (-not (Test-Path $bin)) {
        LogErr "Missing binary: $bin"
        exit 1
    }
}

New-Item -ItemType Directory -Force -Path $RESULTS | Out-Null

$failed = @()
Log "=== LOCAL GGUF BENCHMARK SUITE ===" "Magenta"
Log "Models: $($targetModels.Count)" "White"
Log "Model root: $MODEL_ROOT" "White"
Log "Results: $RESULTS" "White"
Log ""

foreach ($model in $targetModels) {
    Log "=== $($model.display) ===" "Magenta"
    $outDir = Join-Path $RESULTS $model.id
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    if ((Test-RequestedResultsExist $outDir) -and -not $ForceRerun) {
        LogOk "All requested results exist, skipping $($model.id)"
        continue
    }

    try {
        $modelPath = Resolve-ModelPath $model
        if (-not $SkipSpeed) { Run-SpeedBench $model $modelPath $outDir }
        Start-LlamaServer $modelPath $model
        Run-ToolCallBench $model $outDir
        Run-CodingBench $model $outDir
        Run-ReasoningBench $model $outDir
        LogOk "$($model.id) complete"
    } catch {
        LogErr "FAILED $($model.id): $_"
        $failed += $model.id
    } finally {
        Stop-LlamaServer
    }
    Log ""
}

$reportArgs = @(
    "$BENCH_DIR\report.py",
    "--results-dir", $RESULTS,
    "--output", (Join-Path $BENCH_DIR "benchmark_report.md")
)
$reportExit = Invoke-NativeLogged "python" $reportArgs
if ($reportExit -ne 0) { LogWarn "Report generation returned exit $reportExit" }

if ($failed) {
    LogErr "Failed models: $($failed -join ', ')"
    exit 1
}

LogOk "Done"
