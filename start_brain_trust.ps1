# Start Brain Trust Environment
Write-Host "Starting Brain Trust..." -ForegroundColor Green

# Get the directory where this script lives
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
Write-Host "Running from: $ScriptDir" -ForegroundColor Cyan

# 1. Start Backend (New Window)
Start-Process powershell -WorkingDirectory "$ScriptDir\backend" -ArgumentList "-NoExit", "-Command", "& '..\\.venv\\Scripts\\uvicorn.exe' app.main:app --reload"

# 2. Start Frontend (New Window)
Start-Process powershell -WorkingDirectory "$ScriptDir\frontend" -ArgumentList "-NoExit", "-Command", "npm run dev"

# 3. Wait a moment then open Browser
Start-Sleep -Seconds 5
Start-Process "http://localhost:3000"

Write-Host "Services launched in new windows." -ForegroundColor Green
Write-Host "Backend: http://localhost:8000"
Write-Host "Frontend: http://localhost:3000"
