param(
    [string]$PromptFile = ".\PROMPT.md",
    [int]$MaxIterations = 10,
    [int]$SleepSeconds = 2,
    [switch]$AutoCommit
)

if (-not (Get-Command opencode -ErrorAction SilentlyContinue)) {
    Write-Error "opencode is not installed or not in PATH."
    exit 1
}

if (-not (Test-Path $PromptFile)) {
    Write-Error "Prompt file not found: $PromptFile"
    exit 1
}

$logDir = ".\ralph-logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

for ($i = 1; $i -le $MaxIterations; $i++) {
    Write-Host ""
    Write-Host "=== Ralph iteration $i / $MaxIterations ===" -ForegroundColor Cyan

    $basePrompt = Get-Content $PromptFile -Raw

    $loopPrompt = @"
$basePrompt

Ralph loop instructions:
- Continue from the current repository state.
- Read existing files before making changes.
- Make the next highest-value increment toward completion.
- Run relevant checks/tests after changes.
- If the task is fully complete, end your response with exactly: COMPLETE
"@

    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $outFile = Join-Path $logDir "iteration_${i}_$timestamp.txt"

    try {
        $output = & opencode run $loopPrompt 2>&1 | Tee-Object -FilePath $outFile
        $exitCode = $LASTEXITCODE
    }
    catch {
        Write-Warning "opencode crashed on iteration $i"
        Write-Warning $_
        break
    }

    if ($exitCode -ne 0) {
        Write-Warning "opencode exited with code $exitCode on iteration $i"
        break
    }

    if ($AutoCommit) {
        $hasChanges = (git status --porcelain 2>$null)
        if ($LASTEXITCODE -eq 0 -and $hasChanges) {
            git add -A
            git commit -m "ralph: iteration $i"
        }
    }

    $fullOutput = ($output | Out-String)

    if ($fullOutput -match '(?m)^COMPLETE\s*$') {
        Write-Host "Task marked COMPLETE on iteration $i" -ForegroundColor Green
        break
    }

    if ($i -lt $MaxIterations) {
        Start-Sleep -Seconds $SleepSeconds
    }
}

Write-Host ""
Write-Host "Ralph loop finished." -ForegroundColor Yellow