@echo off
cd /d "%~dp0.."
if exist "venv\Scripts\python.exe" (
    set PY=venv\Scripts\python.exe
) else (
    set PY=python
)
echo === Mr. Rao quality gate ===
echo [1/4] compileall...
%PY% -m compileall -q app.py config.py mr_rao
if errorlevel 1 exit /b 1
echo [2/4] health...
%PY% -m mr_rao.cli health
if errorlevel 1 exit /b 1
echo [3/4] licenze di terze parti allineate...
REM Un elenco scritto a mano invecchia in silenzio: la prima stesura
REM sbagliava la licenza di Scrubadub e ometteva python-stdnum (LGPL).
%PY% scripts\gen_third_party.py --check
if errorlevel 1 exit /b 1
echo [4/4] pytest...
%PY% -m pytest tests -q --tb=short
if errorlevel 1 exit /b 1
echo === GATE PASSED ===
exit /b 0
