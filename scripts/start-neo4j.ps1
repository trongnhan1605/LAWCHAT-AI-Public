$ErrorActionPreference = "Stop"

$repoRoot = Split-Path $PSScriptRoot -Parent
$neo4jHome = Join-Path $repoRoot "tools\neo4j-community-4.4.47"
$neo4jBat = Join-Path $neo4jHome "bin\neo4j.bat"
$javaHome = "C:\Program Files\Microsoft\jdk-11.0.16.101-hotspot"
$boltPort = 7687
$httpPort = 7474

function Test-ListeningPort {
    param([int]$Port)
    $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)
}

if (-not (Test-Path $neo4jBat)) {
    throw "Missing Neo4j local binary: $neo4jBat"
}

if (-not (Test-Path $javaHome)) {
    throw "Missing JAVA_HOME: $javaHome"
}

if ((Test-ListeningPort -Port $boltPort) -and (Test-ListeningPort -Port $httpPort)) {
    Write-Host "Neo4j is already running:"
    Write-Host "  Browser: http://localhost:$httpPort"
    Write-Host "  Bolt:    bolt://localhost:$boltPort"
    exit 0
}

$env:JAVA_HOME = $javaHome
$env:PATH = "$javaHome\bin;$env:PATH"

Write-Host "Starting Neo4j in this terminal..."
Write-Host "Browser: http://localhost:$httpPort"
Write-Host "Bolt:    bolt://localhost:$boltPort"
Write-Host "Press Ctrl+C in this terminal to stop Neo4j."

Set-Location $neo4jHome
& $neo4jBat console --verbose
