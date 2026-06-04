param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoReload,
    [switch]$InstallDependencies
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = Join-Path $repoRoot "backend"
$requirementsFile = Join-Path $backendDir "requirements.txt"
$venvDir = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

function Test-BackendEnvironment {
    param(
        [string]$PythonPath
    )

    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $PythonPath -c "import fastapi, pydantic_settings, pypdf, psycopg, sqlalchemy, uvicorn" *> $null
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

if (-not (Test-Path $backendDir)) {
    throw "Missing backend directory: $backendDir"
}

if (-not (Test-Path $requirementsFile)) {
    throw "Missing requirements file: $requirementsFile"
}

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating LawChat-AI virtual environment at $venvDir"
    & py -3.11 -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to create .venv. Install Python 3.11 and try again."
    }
    $InstallDependencies = $true
}

if ($InstallDependencies -or -not (Test-BackendEnvironment -PythonPath $venvPython)) {
    Write-Host "Installing backend dependencies into LawChat-AI .venv..."
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r $requirementsFile
    if ($LASTEXITCODE -ne 0) {
        throw "Backend dependency installation failed."
    }
}

if (-not (Test-BackendEnvironment -PythonPath $venvPython)) {
    throw "LawChat-AI .venv is missing required backend packages. Run .\scripts\start-backend.ps1 -InstallDependencies."
}

$env:PYTHONPATH = $backendDir
$env:VIRTUAL_ENV = $venvDir

Write-Host "Starting backend at http://$HostName`:$Port"
Write-Host "Python=$venvPython"
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

& $venvPython @uvicornArgs
