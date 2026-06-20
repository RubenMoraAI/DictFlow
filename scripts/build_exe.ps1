# Build DictFlow.exe (standalone Windows executable) with PyInstaller.
# Run from anywhere:  .\scripts\build_exe.ps1
# The result is dist\DictFlow.exe — a single self-contained file.

$ErrorActionPreference = "Stop"

# Always operate from the repository root (one level above this script).
Set-Location (Split-Path -Parent $PSScriptRoot)

# Use the project's virtual environment if present, otherwise the system Python.
if (Test-Path ".\.venv\Scripts\python.exe") {
    $py = ".\.venv\Scripts\python.exe"
} else {
    $py = "python"
}

Write-Host "Installing build dependencies..." -ForegroundColor Cyan
& $py -m pip install -r requirements.txt
& $py -m pip install pyinstaller

Write-Host "Building DictFlow.exe..." -ForegroundColor Cyan
$iconArg = @()
if (Test-Path ".\assets\dictflow.ico") { $iconArg = @("--icon", "assets\dictflow.ico") }
& $py -m PyInstaller --noconfirm --onefile --windowed --name DictFlow `
    @iconArg `
    --collect-all customtkinter `
    --collect-all sounddevice `
    --collect-all keyring `
    mainsoft.py

Write-Host "`nDone. Your executable is at: dist\DictFlow.exe" -ForegroundColor Green
