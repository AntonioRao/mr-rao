@echo off
chcp 65001 >nul 2>&1
title Motore MarkItDown Web App
color 0B

echo.
echo ===================================================
echo     Avvio del Server MarkItDown in corso...
echo ===================================================
echo.
echo ATTENZIONE: Questa finestra e' il "cervello" dell'app.
echo Non chiuderla mentre stai usando l'applicazione nel browser!
echo Quando hai finito, puoi chiudere liberamente questa finestra.
echo.

:: Vai nella cartella dello script (in caso venga lanciato dal Desktop)
cd /d "%~dp0"

:: Controlla se esiste un ambiente virtuale e usalo
if exist "venv\Scripts\activate.bat" (
    echo Uso ambiente virtuale locale...
    call venv\Scripts\activate.bat
) else (
    echo Uso Python di sistema...
    echo (Consiglio: lancia "Installa MarkItDown.bat" per creare un ambiente isolato)
    echo.
)

echo Avvio del browser in corso...

:: Aspetta 2 secondi in background per dare tempo al server di avviarsi
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:5000"

:: Avvia il server Flask in questa finestra
python app.py
