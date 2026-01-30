@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "start_brain_trust.ps1"
pause
