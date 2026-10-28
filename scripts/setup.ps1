# Memory Séance Lite setup for Windows (PowerShell).
#   .\scripts\setup.ps1          default model (gemma3:1b)
#   .\scripts\setup.ps1 -Low     very low-resource model (qwen3:0.6b)
param([switch]$Low)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$Model = if ($Low) { "qwen3:0.6b" } else { "gemma3:1b" }

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) { throw "Python 3.10+ is required. Install it from https://www.python.org/downloads/" }

if (-not (Test-Path .venv)) { & $py.Source -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
(Get-Content .env) -replace '^MSL_MODEL=.*', "MSL_MODEL=$Model" | Set-Content .env

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  Write-Host "Ollama is not installed. Get it from https://ollama.com/download, then run:  ollama pull $Model"
} else {
  & ollama list *> $null
  if ($LASTEXITCODE -ne 0) { Write-Host "Ollama is not running. Start it, then run:  ollama pull $Model" }
  else { & ollama pull $Model }
}

Write-Host ""
Write-Host "Setup done. Start the app with:"
Write-Host "  .\.venv\Scripts\python.exe -m app.main"
Write-Host "Then open http://127.0.0.1:8000"
