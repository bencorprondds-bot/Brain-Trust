@echo off
echo Starting Brain Trust Backend...
cd backend
..\.venv\Scripts\uvicorn app.main:app --reload
pause
