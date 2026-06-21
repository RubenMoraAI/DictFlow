# Install DictFlow and make it start automatically when you log in to Windows.
# It copies the built exe to %LOCALAPPDATA%\DictFlow and adds a shortcut to the
# Startup folder (transparent — you can disable it from Task Manager > Startup).
#
# Usage (run from anywhere):
#   .\scripts\install.ps1          install + enable autostart (and launch now)
#   .\scripts\install.ps1 -Remove  remove autostart and the installed copy
param([switch]$Remove)

# Always operate from the repository root (one level above this script).
Set-Location (Split-Path -Parent $PSScriptRoot)

$installDir = Join-Path $env:LOCALAPPDATA "DictFlow"
$installExe = Join-Path $installDir "DictFlow.exe"
$startup    = [Environment]::GetFolderPath("Startup")
$shortcut   = Join-Path $startup "DictFlow.lnk"

if ($Remove) {
    Get-Process DictFlow -ErrorAction SilentlyContinue | Stop-Process -Force
    $links = @(
        $shortcut,
        (Join-Path ([Environment]::GetFolderPath("Desktop")) "DictFlow.lnk"),
        (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\DictFlow.lnk")
    )
    foreach ($l in $links) { if (Test-Path $l) { Remove-Item $l -Force } }
    if (Test-Path $installDir) { Remove-Item $installDir -Recurse -Force; Write-Host "Removed $installDir" }
    Write-Host "DictFlow uninstalled (shortcuts and installed files removed)." -ForegroundColor Green
    return
}

$source = ".\dist\DictFlow.exe"
if (-not (Test-Path $source)) {
    throw "dist\DictFlow.exe not found. Build it first with  .\build_exe.ps1"
}

# Stop any running copy so the file can be replaced.
Get-Process DictFlow -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 400

New-Item -ItemType Directory -Force -Path $installDir | Out-Null
Copy-Item $source $installExe -Force
# Carry over existing settings (prompt, model, shortcuts, hotkey) if present.
if (Test-Path ".\config.json") { Copy-Item ".\config.json" (Join-Path $installDir "config.json") -Force }
Write-Host "Installed to $installExe"

$ws = New-Object -ComObject WScript.Shell

function New-DictFlowShortcut($path) {
    $s = $ws.CreateShortcut($path)
    $s.TargetPath       = $installExe
    $s.WorkingDirectory = $installDir
    $s.IconLocation     = $installExe
    $s.Description       = "DictFlow voice dictation"
    $s.Save()
}

# Startup (auto-start on login), plus Desktop and Start Menu for easy launching.
New-DictFlowShortcut $shortcut
New-DictFlowShortcut (Join-Path ([Environment]::GetFolderPath("Desktop")) "DictFlow.lnk")
New-DictFlowShortcut (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\DictFlow.lnk")

Write-Host "DictFlow installed. It will start automatically when you log in," -ForegroundColor Green
Write-Host "and you can launch it from the Desktop or Start Menu shortcuts."
Write-Host "To undo:  .\scripts\install.ps1 -Remove"

Start-Process $installExe
