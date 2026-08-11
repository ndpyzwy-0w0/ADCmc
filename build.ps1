# Build ADCmc into a single-file Windows exe
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> Installing dependencies..."
python -m pip install -r requirements.txt

Write-Host "==> Building exe with PyInstaller..."
python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name ADCmc `
  --manifest dpi.manifest `
  --distpath dist `
  --workpath build `
  main.py

Write-Host ""
Write-Host "Done: $PSScriptRoot\dist\ADCmc.exe"
