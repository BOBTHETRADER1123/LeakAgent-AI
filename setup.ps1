$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
py -3.12 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 first.' }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if (!(Test-Path .env)) { Copy-Item .env.example .env }
Write-Host 'Setup complete. Run the ingestion command in README.md.'
