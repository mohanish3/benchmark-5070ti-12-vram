<#
.SYNOPSIS
  Full model benchmark suite: download → speed → tool-call → coding → reasoning → delete

.DESCRIPTION
  Benchmarks all models in docs/model_list.md on:
  - Speed (PP/TG tok/s via llama-bench, 128k ctx, 512 tok)
  - Agentic tool calling (25 BFCL-style tests)
  - Coding (20 HumanEval problems, pass@1)
  - Reasoning (50 GSM8K problems, accuracy)

  Permanent models (marked below) are kept after benchmarking.
  All others are deleted after their benchmark run.

  GGUF models are downloaded directly.
  SafeTensors models are downloaded, converted, quantized to Q4_K_M, then deleted.

.PARAMETER ModelsOnly
  Comma-separated model IDs to run (default: all). e.g. "gemma4-12b-q4km,qwen35-9b-glm51-q4km"

.PARAMETER SkipSpeed
  Skip speed benchmark (useful for quick iteration)

.PARAMETER SkipConvert
  Skip safetensors models (run only GGUF models)

.EXAMPLE
  .\run_benchmark.ps1
  .\run_benchmark.ps1 -ModelsOnly "gemma4-12b-q4km"
  .\run_benchmark.ps1 -SkipSpeed
#>
param(
    [string]$ModelsOnly = "",
    [switch]$SkipSpeed,
    [switch]$SkipConvert,
    [switch]$ForceRerun,
    [switch]$Expanded
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"   # prevent CP1252 crash on Unicode chars in Python output
$env:HF_HUB_DISABLE_XET = "1"  # avoid stalled Xet transfers on large safetensors
$env:HF_HUB_ENABLE_HF_TRANSFER = "0"
$env:HF_HUB_DISABLE_PROGRESS_BARS = "1"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
$ROOT       = Split-Path $PSScriptRoot -Parent
$BENCH_DIR  = $PSScriptRoot
$RESULTS    = Join-Path $BENCH_DIR "results"
$MODEL_ROOT_CANDIDATES = @(
    $env:MODEL_ROOT,
    (Join-Path $ROOT "..\Agent Crew Models"),
    (Join-Path $ROOT "..\Agents\Agent Crew Models"),
    (Join-Path $ROOT "..\..\Agent Crew Models")
) | Where-Object { $_ }
$MODEL_ROOT = $MODEL_ROOT_CANDIDATES | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $MODEL_ROOT) {
    $MODEL_ROOT = Join-Path $ROOT "..\Agent Crew Models"
}
$MODELS_DIR = Join-Path $MODEL_ROOT "bench-models"
$HF_CACHE   = "$env:USERPROFILE\.cache\huggingface\hub"

$SM120_BIN  = Join-Path $ROOT "tools\llama.cpp-sm120-src\build-sm120\bin\Release"
$CUDA_BIN   = Join-Path $ROOT "tools\llama-cpp-cuda-b9509"
# SM120 build: optimized llama-server for RTX 5070 Ti (Blackwell SM120)
# CUDA b9509 build: llama-bench and llama-quantize (SM120 build only compiled server)
$LLAMA_SRV  = Join-Path $SM120_BIN "llama-server.exe"
$LLAMA_BNH  = Join-Path $CUDA_BIN  "llama-bench.exe"
$LLAMA_QNT  = Join-Path $CUDA_BIN  "llama-quantize.exe"
$CONVERT_PY = Join-Path $ROOT "tools\llama.cpp-sm120-src\convert_hf_to_gguf.py"

$LLAMA_PORT = 8090  # Use non-default port to avoid conflicts
$LLAMA_HOST = "127.0.0.1"

# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------
# format: "gguf" = download GGUF directly
#         "safetensors" = download safetensors, convert+quantize to Q4_K_M

$MODELS = @(
    @{
        id           = "omnicoder-9b-q4km"
        display      = "Tesslate/OmniCoder-9B"
        repo         = "Tesslate/OmniCoder-9B"
        format       = "gguf"
        gguf_file    = "omnicoder-9b-q4_k_m.gguf"
        ngl          = 99
        ctx          = 131072
        threads      = 8
        permanent    = $true
        cpu_offload  = $false
    },
    @{
        id           = "qwopus35-9b-coder-q4km"
        display      = "Jackrong/Qwopus3.5-9B-Coder"
        repo         = "Jackrong/Qwopus3.5-9B-Coder"
        format       = "safetensors"
        gguf_out     = "qwopus35-9b-coder-Q4_K_M.gguf"
        ngl          = 99
        ctx          = 131072
        threads      = 8
        permanent    = $false
        cpu_offload  = $false
    },
    @{
        id           = "qwopus35-9b-coder-mtp-q4km"
        display      = "Jackrong/Qwopus3.5-9B-Coder-MTP-GGUF"
        repo         = "Jackrong/Qwopus3.5-9B-Coder-MTP-GGUF"
        format       = "gguf"
        gguf_file    = "Qwopus3.5-9B-Coder-MTP-Q4_K_M.gguf"
        local_path   = Join-Path $MODELS_DIR "qwopus35-9b-coder-q4km\Qwopus3.5-9B-Coder-MTP-Q4_K_M.gguf"
        ngl          = 99
        ctx          = 131072
        threads      = 8
        permanent    = $true
        cpu_offload  = $false
    },
    @{
        id           = "gemma4-12b-q4km"
        display      = "unsloth/gemma-4-12b-it-GGUF [DOWNLOADED]"
        repo         = "unsloth/gemma-4-12b-it-GGUF"
        format       = "gguf"
        gguf_file    = "gemma-4-12b-it-Q4_K_M.gguf"
        local_path   = Join-Path $MODELS_DIR "gemma4-12b-q4km\gemma-4-12b-it-Q4_K_M.gguf"
        ngl          = 99
        ctx          = 131072
        threads      = 8
        permanent    = $true   # DON'T DELETE
        cpu_offload  = $false
    },
    @{
        id           = "qwen35-9b-opus-distill-q4km"
        display      = "Jackrong/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-v2"
        repo         = "Jackrong/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-v2"
        format       = "gguf"
        gguf_file    = "Qwen3.5-9B.Q4_K_M.gguf"
        local_path   = Join-Path $MODELS_DIR "qwen35-9b-opus-distill-q4km\Qwen3.5-9B.Q4_K_M.gguf"
        ngl          = 99
        ctx          = 131072
        threads      = 8
        permanent    = $true
        cpu_offload  = $false
    },
    @{
        id           = "lfm25-8b-q6km"
        display      = "LiquidAI/LFM2.5-8B-A1B"
        repo         = "LiquidAI/LFM2.5-8B-A1B"
        format       = "gguf"
        gguf_file    = "LFM2.5-8B-A1B-Q6_K.gguf"
        local_path   = Join-Path $MODELS_DIR "lfm25-8b-q6km\LFM2.5-8B-A1B-Q6_K.gguf"
        ngl          = 99
        ctx          = 131072
        threads      = 8
        permanent    = $true
        cpu_offload  = $false
    },
    @{
        id           = "qwen35-9b-glm51-q4km"
        display      = "Jackrong/Qwen3.5-9B-GLM5.1-Distill-v1-GGUF"
        repo         = "Jackrong/Qwen3.5-9B-GLM5.1-Distill-v1-GGUF"
        format       = "gguf"
        gguf_file    = "Qwen3.5-9B-GLM5.1-Distill-v1-Q4_K_M.gguf"
        local_path   = Join-Path $MODELS_DIR "qwen35-9b-glm51-distill-q4km\Qwen3.5-9B-GLM5.1-Distill-v1-Q4_K_M.gguf"
        ngl          = 99
        ctx          = 131072
        threads      = 8
        permanent    = $false
        cpu_offload  = $false
    }
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Log($msg, $color = "Cyan") {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $msg" -ForegroundColor $color
}

function LogOk($msg)   { Log "[OK] $msg" "Green" }
function LogErr($msg)  { Log "[ERR] $msg" "Red" }
function LogWarn($msg) { Log "[WARN] $msg" "Yellow" }

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

function Find-GGUFInHFCache($repo, $filename) {
    $repoSlug = $repo -replace "/", "--"
    $cacheDir = Join-Path $HF_CACHE "models--$repoSlug"
    if (-not (Test-Path $cacheDir)) { return $null }
    return Get-ChildItem $cacheDir -Recurse -Filter $filename -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
}

function Invoke-HuggingFaceCli($cliArgs) {
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & huggingface-cli @cliArgs 2>&1 | ForEach-Object { Write-Host "$_" }
        if ($LASTEXITCODE -ne 0) {
            throw "huggingface-cli failed (exit $LASTEXITCODE): $($cliArgs -join ' ')"
        }
    } finally {
        $ErrorActionPreference = $oldPreference
    }
}

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

function ConvertTo-HFUrlPath($path) {
    return (($path -split "/") | ForEach-Object { [uri]::EscapeDataString($_) }) -join "/"
}

function Test-HFExclude($path, $patterns) {
    foreach ($pattern in $patterns) {
        if ($path -like $pattern) {
            return $true
        }
    }
    return $false
}

function Download-HFRepoDirect($repo, $localDir, $excludePatterns) {
    $apiRepo = ConvertTo-HFUrlPath $repo
    $apiUrl = "https://huggingface.co/api/models/$apiRepo/tree/main?recursive=1"
    Log "Listing HF repo files via API: $repo"
    $files = Invoke-RestMethod -Uri $apiUrl -TimeoutSec 60
    $files = @($files | Where-Object { $_.type -eq "file" -and -not (Test-HFExclude $_.path $excludePatterns) })

    $i = 0
    foreach ($file in $files) {
        $i++
        $relative = $file.path
        $dest = Join-Path $localDir ($relative -replace "/", [IO.Path]::DirectorySeparatorChar)
        $destDir = Split-Path $dest -Parent
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null

        if ((Test-Path $dest) -and $file.size -and ((Get-Item $dest).Length -eq [int64]$file.size)) {
            LogOk "[$i/$($files.Count)] Exists: $relative"
            continue
        }

        $urlPath = ConvertTo-HFUrlPath $relative
        $url = "https://huggingface.co/$apiRepo/resolve/main/$urlPath"
        Log "[$i/$($files.Count)] Downloading: $relative"
        $curlArgs = @(
            "--location",
            "--fail",
            "--retry", "10",
            "--retry-delay", "5",
            "--continue-at", "-",
            "--silent",
            "--show-error",
            "--output", $dest,
            $url
        )
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            & curl.exe @curlArgs 2>&1 | ForEach-Object { Write-Host "$_" }
            if ($LASTEXITCODE -ne 0) {
                throw "curl failed (exit $LASTEXITCODE): $relative"
            }
        } finally {
            $ErrorActionPreference = $oldPreference
        }
    }
}

function Download-GGUF($model) {
    if ($model.local_path -and (Test-Path $model.local_path)) {
        LogOk "Using local GGUF: $($model.local_path)"
        return $model.local_path
    }

    $outDir = Join-Path $MODELS_DIR $model.id
    $outFile = Join-Path $outDir $model.gguf_file
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    if (Test-Path $outFile) {
        LogOk "GGUF already at $outFile"
        return $outFile
    }

    # Check HF cache first
    $cached = Find-GGUFInHFCache $model.repo $model.gguf_file
    if ($cached) {
        LogOk "Found in HF cache: $cached"
        return $cached
    }

    Log "Downloading GGUF: $($model.repo) / $($model.gguf_file)"
    $env:PYTHONUTF8 = "1"
    Invoke-HuggingFaceCli @("download", $model.repo, $model.gguf_file, "--local-dir", $outDir, "--max-workers", "1")
    if (-not (Test-Path $outFile)) {
        throw "Download failed: $outFile not found"
    }
    LogOk "Downloaded: $outFile"
    return $outFile
}

function Convert-SafeTensors($model) {
    $stDir   = Join-Path $MODELS_DIR "$($model.id)-st"
    $f16File = Join-Path (Join-Path $MODELS_DIR $model.id) "$($model.id)-F16.gguf"
    $q4File  = Join-Path (Join-Path $MODELS_DIR $model.id) $model.gguf_out

    New-Item -ItemType Directory -Force -Path (Join-Path $MODELS_DIR $model.id) | Out-Null

    if (Test-Path $q4File) {
        LogOk "Converted GGUF already exists: $q4File"
        return $q4File
    }

    if ($model.warn) { LogWarn $model.warn }

    # Step 1: Download safetensors
    Log "Downloading safetensors: $($model.repo) - large, may take a while..."
    New-Item -ItemType Directory -Force -Path $stDir | Out-Null
    $env:PYTHONUTF8 = "1"
    Download-HFRepoDirect $model.repo $stDir @("*.gguf", "*.pt", "*.bin")
    LogOk "Download complete"

    # Step 2: Convert to F16 GGUF
    Log "Converting to GGUF F16..."
    $convArgs = @(
        $CONVERT_PY,
        $stDir,
        "--outfile", $f16File,
        "--outtype", "f16"
    )
    & python @convArgs
    if ($LASTEXITCODE -ne 0) {
        throw "convert_hf_to_gguf.py failed (exit $LASTEXITCODE)"
    }
    LogOk "F16 GGUF: $f16File"

    # Step 3: Quantize to Q4_K_M
    Log "Quantizing to Q4_K_M..."
    $qntArgs = @($f16File, $q4File, "Q4_K_M")
    & $LLAMA_QNT @qntArgs
    if ($LASTEXITCODE -ne 0) {
        throw "llama-quantize failed (exit $LASTEXITCODE)"
    }
    LogOk "Q4_K_M: $q4File"

    # Step 4: Delete safetensors dir and F16 GGUF
    Log "Cleaning up safetensors and F16 intermediates..."
    Remove-Item $stDir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item $f16File -Force -ErrorAction SilentlyContinue
    LogOk "Cleanup done"

    return $q4File
}

function Get-ModelPath($model) {
    if ($model.format -eq "gguf") {
        return Download-GGUF $model
    } else {
        if ($SkipConvert) {
            LogWarn "Skipping safetensors model: $($model.id)"
            return $null
        }
        return Convert-SafeTensors $model
    }
}

function Delete-Model($model, $modelPath) {
    if ($model.permanent) {
        Log "Keeping permanent model: $modelPath"
        return
    }
    $dir = Join-Path $MODELS_DIR $model.id
    if (Test-Path $dir) {
        Log "Deleting $dir ..."
        Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue
        LogOk "Deleted"
    }
    # Also cleanup HF cache for non-permanent GGUF downloads
    if ($model.format -eq "gguf") {
        $repoSlug = $model.repo -replace "/", "--"
        $cacheDir = Join-Path $HF_CACHE "models--$repoSlug"
        if (Test-Path $cacheDir) {
            Log "Deleting HF cache: $cacheDir ..."
            Remove-Item $cacheDir -Recurse -Force -ErrorAction SilentlyContinue
            LogOk "HF cache deleted"
        }
    }
}

function Start-LlamaServer($modelPath, $model) {
    Stop-LlamaServer  # ensure clean state

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
        "--jinja"  # Enable jinja templates for tool calling
    )

    Log "Starting llama-server for $($model.id) ngl=$($model.ngl) ctx=$($model.ctx)..."
    Start-Process -FilePath $LLAMA_SRV -ArgumentList $args `
        -RedirectStandardOutput $logOut -RedirectStandardError $logErr `
        -WindowStyle Hidden | Out-Null

    Log "Waiting for server ready..."
    if (-not (Wait-ServerReady)) {
        $err = Get-Content $logErr -Tail 20 -ErrorAction SilentlyContinue
        throw "llama-server not ready after 180s. Last errors:`n$err"
    }
    LogOk "Server ready at http://$LLAMA_HOST`:$LLAMA_PORT"
}

function Run-SpeedBench($model, $modelPath, $outDir) {
    $outFile = Join-Path $outDir "speed.json"
    if ((Test-Path $outFile) -and -not $ForceRerun) {
        LogOk "Speed results exist, skipping"
        return
    }
    Log "Running speed benchmark (llama-bench)..."
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
    if ($exitCode -ne 0) { LogWarn "Speed bench returned exit $exitCode" }
    else { LogOk "Speed done" }
}

function Run-ToolCallBench($model, $outDir) {
    $outFile = Join-Path $outDir "toolcall.json"
    if ((Test-Path $outFile) -and -not $ForceRerun) { LogOk "Toolcall results exist, skipping"; return }
    # 35B offload models get fewer tests unless expanded.
    $nTests = if ($Expanded) { 30 } elseif ($model.cpu_offload) { 10 } else { 15 }
    Log "Running tool-calling benchmark: $nTests tests..."
    $procArgs = @(
        "$BENCH_DIR\bench_toolcall.py",
        "--base-url", "http://$LLAMA_HOST`:$LLAMA_PORT/v1",
        "--model", $model.id,
        "--output", $outFile,
        "--timeout", "90",
        "--n-tests", $nTests
    )
    $exitCode = Invoke-NativeLogged "python" $procArgs
    if ($exitCode -ne 0) { LogWarn "Toolcall bench returned exit $exitCode" }
    else { LogOk "Toolcall done" }
}

function Run-CodingBench($model, $outDir) {
    $outFile = Join-Path $outDir "coding.json"
    if ((Test-Path $outFile) -and -not $ForceRerun) { LogOk "Coding results exist, skipping"; return }
    # 10 problems for all models (fast enough at 9B, manageable at 35B with 2min timeout each)
    Log "Running coding benchmark: 10 HumanEval problems..."
    $procArgs = @(
        "$BENCH_DIR\bench_coding.py",
        "--base-url", "http://$LLAMA_HOST`:$LLAMA_PORT/v1",
        "--model", $model.id,
        "--output", $outFile,
        "--timeout", "300"
    )
    if ($Expanded) {
        $procArgs += "--full"
    }
    $exitCode = Invoke-NativeLogged "python" $procArgs
    if ($exitCode -ne 0) { LogWarn "Coding bench returned exit $exitCode" }
    else { LogOk "Coding done" }
}

function Run-ReasoningBench($model, $outDir) {
    $outFile = Join-Path $outDir "reasoning.json"
    if ((Test-Path $outFile) -and -not $ForceRerun) { LogOk "Reasoning results exist, skipping"; return }
    # 35B: 8 problems unless expanded; expanded runs 50 GSM8K problems.
    $limit = if ($Expanded) { 50 } elseif ($model.cpu_offload) { 8 } else { 15 }
    Log "Running reasoning benchmark: $limit GSM8K problems..."
    $procArgs = @(
        "$BENCH_DIR\bench_reasoning.py",
        "--base-url", "http://$LLAMA_HOST`:$LLAMA_PORT/v1",
        "--model", $model.id,
        "--limit", $limit,
        "--output", $outFile,
        "--timeout", "300"
    )
    $exitCode = Invoke-NativeLogged "python" $procArgs
    if ($exitCode -ne 0) { LogWarn "Reasoning bench returned exit $exitCode" }
    else { LogOk "Reasoning done" }
}

function Test-RequestedResultsExist($outDir) {
    $required = @("toolcall.json", "coding.json", "reasoning.json")
    if (-not $SkipSpeed) {
        $required += "speed.json"
    }
    foreach ($file in $required) {
        if (-not (Test-Path (Join-Path $outDir $file))) {
            return $false
        }
    }
    return $true
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# Filter models if requested
$targetModels = $MODELS
if ($ModelsOnly) {
    $ids = $ModelsOnly -split "," | ForEach-Object { $_.Trim() }
    $targetModels = @($MODELS | Where-Object { $ids -contains $_.id })
    if (-not $targetModels) {
        LogErr "No models matched: $ModelsOnly"
        exit 1
    }
}

# Validate binaries
foreach ($bin in @($LLAMA_SRV, $LLAMA_BNH, $LLAMA_QNT)) {
    if (-not (Test-Path $bin)) {
        LogErr "Missing binary: $bin"
        exit 1
    }
}
if (-not (Test-Path $CONVERT_PY)) {
    LogErr "Missing: $CONVERT_PY"
    exit 1
}

New-Item -ItemType Directory -Force -Path $MODELS_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $RESULTS | Out-Null

$total = $targetModels.Count
$done  = 0
$failed = @()

Log "=== MODEL BENCHMARK SUITE ===" "Magenta"
Log "Models to benchmark: $total" "White"
Log "Results dir: $RESULTS" "White"
Log ""

foreach ($model in $targetModels) {
    $done++
    Log "=== [$done/$total] $($model.display) ===" "Magenta"

    $outDir = Join-Path $RESULTS $model.id
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    if ((Test-RequestedResultsExist $outDir) -and -not $ForceRerun) {
        LogOk "All requested results exist, skipping $($model.id)"
        Log ""
        continue
    }

    $modelPath = $null
    try {
        # 1. Get model path (download or convert)
        $modelPath = Get-ModelPath $model
        if (-not $modelPath) {
            LogWarn "Skipped (no model path)"
            continue
        }

        # 2. Speed benchmark (doesn't need server)
        if (-not $SkipSpeed) {
            Run-SpeedBench $model $modelPath $outDir
        }

        # 3. Start llama-server for API benchmarks
        Start-LlamaServer $modelPath $model

        # 4. Tool calling
        Run-ToolCallBench $model $outDir

        # 5. Coding
        Run-CodingBench $model $outDir

        # 6. Reasoning
        Run-ReasoningBench $model $outDir

        LogOk "$($model.id) complete"

    } catch {
        LogErr "FAILED $($model.id): $_"
        $failed += $model.id
    } finally {
        Stop-LlamaServer
        if ($modelPath -and -not $model.permanent) {
            try { Delete-Model $model $modelPath } catch { LogWarn "Cleanup failed: $_" }
        }
    }

    Log ""
}

# Generate report
Log "=== GENERATING REPORT ===" "Magenta"
$reportArgs = @(
    "$BENCH_DIR\report.py",
    "--results-dir", $RESULTS,
    "--output", (Join-Path $BENCH_DIR "benchmark_report.md")
)
$reportExit = Invoke-NativeLogged "python" $reportArgs
if ($reportExit -ne 0) {
    LogWarn "Report generation returned exit $reportExit"
}

Log ""
Log "=== DONE ===" "Magenta"
Log "Results: $RESULTS"
Log "Report:  $(Join-Path $BENCH_DIR 'benchmark_report.md')"

if ($failed) {
    LogErr "Failed models: $($failed -join ', ')"
    exit 1
}
