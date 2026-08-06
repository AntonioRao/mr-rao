@echo off
chcp 65001 >nul 2>&1
title Mr. Rao — server locale
color 0B

echo.
echo ===================================================
echo     Avvio di Mr. Rao in corso...
echo ===================================================
echo.
echo Questa finestra e' il server. Non chiuderla mentre
echo usi l'app nel browser.
echo.

cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    echo Uso ambiente virtuale locale...
    call venv\Scripts\activate.bat
) else (
    echo Uso Python di sistema...
    echo Consiglio: lancia "Installa Mr Rao.bat" prima.
    echo.
)

echo Controllo health dipendenze...
python -m mr_rao.cli health
echo.

echo Apertura browser su http://127.0.0.1:5000 ...
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:5000"

set MR_RAO_DEBUG=0
python app.py
