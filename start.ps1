# MFOSIS launcher (Windows / PowerShell)
#
#   Right-click this file -> "Run with PowerShell", or from a terminal:
#       cd C:\path\to\project-sih-
#       .\start.ps1
#
# Opens the backend and frontend each in their OWN titled window, so it is
# obvious at a glance which is which and neither gets accidentally closed or
# typed into. Close a window to stop that server.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# --- checks -----------------------------------------------------------------

$venvPython = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "ERROR: backend virtualenv not found at backend\.venv" -ForegroundColor Red
    Write-Host "Create it first:" -ForegroundColor Yellow
    Write-Host "    cd backend"
    Write-Host "    py -3.11 -m venv .venv"
    Write-Host "    .\.venv\Scripts\Activate.ps1"
    Write-Host "    pip install -r requirements.txt"
    exit 1
}

if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
    Write-Host "ERROR: frontend dependencies not installed." -ForegroundColor Red
    Write-Host "Install them first:" -ForegroundColor Yellow
    Write-Host "    cd frontend"
    Write-Host "    npm install"
    exit 1
}

# --- warn about anything already holding our ports ---------------------------

foreach ($port in 8000, 5173) {
    $inUse = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($inUse) {
        Write-Host "NOTE: port $port is already in use — an old server is probably still running." -ForegroundColor Yellow
        Write-Host "      Close that window first, or the new one will pick a different port." -ForegroundColor Yellow
    }
}

# --- launch ------------------------------------------------------------------

Write-Host "Starting MFOSIS backend  -> http://127.0.0.1:8000" -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$Host.UI.RawUI.WindowTitle = 'MFOSIS BACKEND (do not close)';" +
    "Set-Location '$root\backend';" +
    ". .\.venv\Scripts\Activate.ps1;" +
    "uvicorn app.main:app --reload --port 8000"
)

Start-Sleep -Seconds 2

Write-Host "Starting MFOSIS frontend -> http://localhost:5173" -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$Host.UI.RawUI.WindowTitle = 'MFOSIS FRONTEND (do not close)';" +
    "Set-Location '$root\frontend';" +
    "npm run dev"
)

Write-Host ""
Write-Host "Two windows opened. Give them ~10 seconds, then browse to:" -ForegroundColor Green
Write-Host "    http://localhost:5173" -ForegroundColor Green
Write-Host ""
Write-Host "Leave both windows open while using the app. Close them to stop." -ForegroundColor DarkGray
