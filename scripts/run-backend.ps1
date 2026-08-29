# Runs the MFOSIS backend. Normally launched by ..\start.ps1, but you can run
# it directly too. Keep this window open; close it to stop the server.

$Host.UI.RawUI.WindowTitle = "MFOSIS BACKEND (do not close)"

$backend = Join-Path $PSScriptRoot "..\backend"
Set-Location $backend

. .\.venv\Scripts\Activate.ps1

uvicorn app.main:app --reload --port 8000
