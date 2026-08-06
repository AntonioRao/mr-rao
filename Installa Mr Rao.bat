@echo off
chcp 65001 >nul 2>&1
title Installazione Mr. Rao
color 0B

echo.
echo ╔═══════════════════════════════════════════════════════╗
echo ║           INSTALLAZIONE  MR. RAO                      ║
echo ║     Documenti → Markdown · OCR · Privacy IT           ║
echo ╚═══════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [1/5] Verifica Python...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERRORE: Python non trovato!
    echo   1. Vai su https://www.python.org/downloads/
    echo   2. Spunta "Add Python to PATH"
    echo   3. Riavvia e rilancia questo script
    pause
    exit /b 1
)
python --version
echo       Python trovato.
echo.

echo [2/5] Creazione ambiente virtuale (venv)...
if exist "venv" (
    echo       Ambiente virtuale gia' presente, lo riutilizzo.
) else (
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo ERRORE: Impossibile creare il venv.
        pause
        exit /b 1
    )
    echo       Ambiente virtuale creato.
)
echo.

echo [3/5] Installazione dipendenze (include beautifulsoup4, Flask, RapidOCR...)...
echo.
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERRORE: Installazione dipendenze fallita.
    echo        Controlla la connessione e riprova.
    pause
    exit /b 1
)
echo.
echo       Dipendenze installate (beautifulsoup4 per HTML email, ecc.).
echo.

echo [4/5] Gate di qualita' (pytest)...
python -m pytest tests -q --tb=line
if %ERRORLEVEL% neq 0 (
    echo.
    echo AVVISO: alcuni test non sono passati. L'app potrebbe funzionare comunque.
    echo         Controlla l'output sopra. Continuare e' possibile.
) else (
    echo       Tutti i test OK.
)
echo.

echo [5/5] Collegamento Desktop...
set SCRIPT_DIR=%~dp0
set DESKTOP=%USERPROFILE%\Desktop
(
echo @echo off
echo cd /d "%SCRIPT_DIR%"
echo call "Avvia Mr Rao.bat"
) > "%DESKTOP%\Mr Rao.bat"
echo       Collegamento: Desktop\Mr Rao.bat
echo.

echo ╔═══════════════════════════════════════════════════════╗
echo ║   INSTALLAZIONE COMPLETATA                            ║
echo ║                                                       ║
echo ║   Avvio: doppio clic su "Mr Rao" sul Desktop          ║
echo ║   oppure "Avvia Mr Rao.bat"                           ║
echo ║                                                       ║
echo ║   CLI:  venv\Scripts\python -m mr_rao.cli --help      ║
echo ║   Docs: docs\  e  README.md                           ║
echo ╚═══════════════════════════════════════════════════════╝
echo.
pause
