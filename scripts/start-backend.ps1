param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

function Test-PythonModule {
    param(
        [string]$PythonPath,
        [string]$ModuleName
    )

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $PythonPath -c "import $ModuleName" *> $null
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

$python = "python"
if ((Test-Path $venvPython) -and (Test-PythonModule -PythonPath $venvPython -ModuleName "uvicorn")) {
    $python = $venvPython
}
elseif (Test-Path $venvPython) {
    Write-Host ".venv found but uvicorn is not installed there. Falling back to global python."
}

if (-not (Test-Path $backendDir)) {
    throw "Missing backend directory: $backendDir"
}

$env:PYTHONPATH = $backendDir

Write-Host "Starting backend at http://$HostName`:$Port"
Write-Host "PYTHONPATH=$env:PYTHONPATH"

Set-Location $repoRoot

$uvicornArgs = @(
    "-m",
    "uvicorn",
    "src.main:app",
    "--host",
    $HostName,
    "--port",
    "$Port"
)

if (-not $NoReload) {
    $uvicornArgs += "--reload"
}

& $python @uvicornArgs
