# Runs the MFOSIS frontend dev server. Normally launched by ..\start.ps1, but
# you can run it directly too. Keep this window open; close it to stop it.

$Host.UI.RawUI.WindowTitle = "MFOSIS FRONTEND (do not close)"

$frontend = Join-Path $PSScriptRoot "..\frontend"
Set-Location $frontend

npm run dev
