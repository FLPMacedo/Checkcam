# Build do CheckCam.exe (EXE único: checklist + dashboard).
#
# Uso:  .\build_exe.ps1
#
# Requer PyInstaller (pip install pyinstaller). Gera dist\CheckCam.exe.
# ffmpeg e os browsers do Playwright NÃO são embutidos (são grandes) — devem
# ser distribuídos ao lado do EXE em assets\, conforme o README.

$ErrorActionPreference = "Stop"

Write-Host "Limpando build anterior..." -ForegroundColor Cyan
if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist)  { Remove-Item dist  -Recurse -Force }

Write-Host "Compilando com PyInstaller..." -ForegroundColor Cyan
python -m PyInstaller CheckCam.spec --noconfirm

if (Test-Path "dist\CheckCam.exe") {
    Write-Host "OK: dist\CheckCam.exe" -ForegroundColor Green
} else {
    Write-Host "FALHOU: dist\CheckCam.exe não foi gerado." -ForegroundColor Red
    exit 1
}
