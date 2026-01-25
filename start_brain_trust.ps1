# Start Brain Trust Environment
Write-Host "Starting Brain Trust..." -ForegroundColor Green

# 1. Start Backend (New Window)
# Using precise quoting for PowerShell ArgumentList
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; ..\.venv\Scripts\uvicorn app.main:app --reload"

# 2. Start Frontend (New Window)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

# 3. Wait a moment then open Browser
Start-Sleep -Seconds 5
Start-Process "http://localhost:3000"

Write-Host "Services launched in new windows." -ForegroundColor Green
Write-Host "Please check the new windows for startup status."
