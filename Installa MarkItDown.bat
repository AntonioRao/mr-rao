@echo off
chcp 65001 >nul 2>&1
title Installazione MarkItDown Web App
color 0B

echo.
echo ╔═══════════════════════════════════════════════════════╗
echo ║     INSTALLAZIONE MARKITDOWN WEB APP                 ║
echo ║     Convertitore Documenti + OCR                     ║
echo ╚═══════════════════════════════════════════════════════╝
echo.

:: -------------------------------------------------------
:: 1. Verifica che Python sia installato
:: -------------------------------------------------------
echo [1/4] Verifica Python...

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ ERRORE: Python non trovato!
    echo.
    echo Per installare Python:
    echo   1. Vai su https://www.python.org/downloads/
    echo   2. Scarica la versione piu' recente per Windows
    echo   3. IMPORTANTE: durante l'installazione, spunta
    echo      la casella "Add Python to PATH"
    echo   4. Riavvia il computer
    echo   5. Rilancia questo script
    echo.
    pause
    exit /b 1
)

:: Mostra la versione di Python trovata
python --version
echo       ✅ Python trovato!
echo.

:: -------------------------------------------------------
:: 2. Crea ambiente virtuale (venv)
:: -------------------------------------------------------
echo [2/4] Creazione ambiente virtuale (venv)...

if exist "venv" (
    echo       Ambiente virtuale gia' presente, lo riutilizzo.
) else (
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo.
        echo ❌ ERRORE: Impossibile creare l'ambiente virtuale.
        echo    Assicurati che Python sia installato correttamente.
        pause
        exit /b 1
    )
    echo       ✅ Ambiente virtuale creato!
)
echo.

:: -------------------------------------------------------
:: 3. Attiva il venv e installa dipendenze
:: -------------------------------------------------------
echo [3/4] Installazione dipendenze (potrebbe richiedere qualche minuto)...
echo.

call venv\Scripts\activate.bat

python -m pip install --upgrade pip >nul 2>&1

pip install -r requirements.txt

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ ERRORE: Installazione dipendenze fallita.
    echo    Controlla la tua connessione internet e riprova.
    pause
    exit /b 1
)

echo.
echo       ✅ Tutte le dipendenze installate!
echo.

:: -------------------------------------------------------
:: 4. Crea collegamento sul Desktop
:: -------------------------------------------------------
echo [4/4] Creazione collegamento sul Desktop...

set SCRIPT_DIR=%~dp0
set DESKTOP=%USERPROFILE%\Desktop

:: Crea un file .bat sul Desktop che punta al launcher
(
echo @echo off
echo cd /d "%SCRIPT_DIR%"
echo call "Avvia MarkItDown.bat"
) > "%DESKTOP%\MarkItDown Web App.bat"

echo       ✅ Collegamento creato sul Desktop!
echo.

:: -------------------------------------------------------
:: Fine
:: -------------------------------------------------------
echo.
echo ╔═══════════════════════════════════════════════════════╗
echo ║                                                       ║
echo ║   ✅ INSTALLAZIONE COMPLETATA CON SUCCESSO!          ║
echo ║                                                       ║
echo ║   Per avviare l'app:                                  ║
echo ║     • Fai doppio clic su "MarkItDown Web App"         ║
echo ║       che trovi sul Desktop                           ║
echo ║     • Oppure lancia "Avvia MarkItDown.bat"            ║
echo ║       da questa cartella                              ║
echo ║                                                       ║
echo ╚═══════════════════════════════════════════════════════╝
echo.
pause
