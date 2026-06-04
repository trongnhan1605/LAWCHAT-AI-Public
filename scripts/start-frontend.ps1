param(
    [string]$HostName = "localhost",
    [int]$Port = 5173
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path $PSScriptRoot -Parent
$frontendDir = Join-Path $repoRoot "frontend"

if (-not (Test-Path $frontendDir)) {
    throw "Missing frontend directory: $frontendDir"
}

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "node_modules not found. Running npm install first..."
    Push-Location $frontendDir
    try {
        npm install
    }
    finally {
        Pop-Location
    }
}

Write-Host "Starting frontend at http://$HostName`:$Port"

Set-Location $frontendDir
npm run dev -- --host $HostName --port $Port
