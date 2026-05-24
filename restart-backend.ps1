# restart-backend.ps1
# Usage depuis Claude : PowerShell(".\restart-backend.ps1")
# Tue les process sur 8000, vide le pycache, relance uvicorn.

param(
    [int]$Port = 8000,
    [switch]$NoReload,
    [switch]$Background   # Lance en arrière-plan sans fenêtre (utile depuis Claude Code)
)

$BackendDir = Join-Path $PSScriptRoot "backend"
$UvicornExe = Join-Path $BackendDir ".venv\Scripts\uvicorn.exe"

Write-Host "=== Redemarrage backend LeComptoirImmo ===" -ForegroundColor Cyan

# 1. Tuer tout process ecoutant sur $Port
Write-Host "[1/3] Arret des process sur le port $Port..." -ForegroundColor Yellow
$conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conns) {
    foreach ($c in $conns) {
        try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop } catch {}
    }
    Start-Sleep 2
    Write-Host "      Process tues." -ForegroundColor Green
} else {
    Write-Host "      Aucun process sur le port $Port." -ForegroundColor Green
}

# 2. Vider le pycache dans app/
Write-Host "[2/3] Nettoyage du cache Python..." -ForegroundColor Yellow
$appDir = Join-Path $BackendDir "app"
Get-ChildItem -Path $appDir -Recurse -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $appDir -Recurse -Filter "__pycache__" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "      Cache nettoye." -ForegroundColor Green

# 3. Lancer uvicorn
Write-Host "[3/3] Demarrage uvicorn sur le port $Port..." -ForegroundColor Yellow
$env:PYTHONDONTWRITEBYTECODE = "1"
$reloadFlag = if ($NoReload) { "" } else { "--reload" }
Set-Location $BackendDir
Write-Host ""
Write-Host "Backend : http://localhost:$Port" -ForegroundColor Cyan
Write-Host "Docs    : http://localhost:$Port/api/docs" -ForegroundColor Cyan
Write-Host ""
$PythonExe = Join-Path $BackendDir ".venv\Scripts\python.exe"
if ($Background) {
    $env:PYTHONUNBUFFERED = "1"
    $proc = Start-Process -FilePath $PythonExe -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port",$Port,"--log-level","warning" -WorkingDirectory $BackendDir -PassThru -NoNewWindow
    Start-Sleep 10
    $r = try { (Invoke-RestMethod "http://127.0.0.1:$Port/health").status } catch { "DOWN" }
    Write-Host "Backend PID $($proc.Id) : $r" -ForegroundColor $(if ($r -eq "ok") {"Green"} else {"Red"})
} elseif ($NoReload) {
    & $UvicornExe app.main:app --host 127.0.0.1 --port $Port
} else {
    & $UvicornExe app.main:app --host 127.0.0.1 --port $Port --reload
}
