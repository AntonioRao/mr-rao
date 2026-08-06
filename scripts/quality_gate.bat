@echo off
cd /d "%~dp0.."
if exist "venv\Scripts\python.exe" (
    set PY=venv\Scripts\python.exe
) else (
    set PY=python
)
echo === Mr. Rao quality gate ===
echo [1/3] compileall...
%PY% -m compileall -q app.py config.py mr_rao
if errorlevel 1 exit /b 1
echo [2/3] health...
%PY% -m mr_rao.cli health
if errorlevel 1 exit /b 1
echo [3/3] pytest...
%PY% -m pytest tests -q --tb=short
if errorlevel 1 exit /b 1
echo === GATE PASSED ===
exit /b 0
