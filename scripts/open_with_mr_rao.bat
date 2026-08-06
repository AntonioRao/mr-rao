@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0.."
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -m mr_rao.cli convert %*
) else (
    python -m mr_rao.cli convert %*
)
if errorlevel 1 pause
