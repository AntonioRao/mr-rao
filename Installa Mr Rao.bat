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

echo [4/6] Gate di qualita' (pytest)...
python -m pytest tests -q --tb=line
if %ERRORLEVEL% neq 0 (
    echo.
    echo AVVISO: alcuni test non sono passati. L'app potrebbe funzionare comunque.
    echo         Controlla l'output sopra. Continuare e' possibile.
) else (
    echo       Tutti i test OK.
)
echo.

echo [5/7] Generazione icone (logo, favicon, mr-rao.ico)...
python scripts\generate_icons.py
if %ERRORLEVEL% neq 0 (
    echo       AVVISO: generazione icone fallita — lo shortcut usera' l'icona di default.
) else (
    echo       Icone OK: static\img\mr-rao.ico
)
echo.

echo [6/7] Collegamento Desktop con icona...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\create_desktop_shortcut.ps1" -ProjectRoot "%~dp0"
if %ERRORLEVEL% neq 0 (
    echo       Fallback: creo Mr Rao.bat sul Desktop senza .ico
    set SCRIPT_DIR=%~dp0
    set DESKTOP=%USERPROFILE%\Desktop
    (
    echo @echo off
    echo cd /d "%SCRIPT_DIR%"
    echo call "Avvia Mr Rao.bat"
    ) > "%DESKTOP%\Mr Rao.bat"
) else (
    echo       Collegamento: Desktop\Mr. Rao.lnk  (icona mr-rao.ico)
)
echo.

echo [7/7] Menu contestuale Windows (Invia a / Apri con)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_shell_integration.ps1" -ExePath "%~dp0scripts\open_with_mr_rao.bat" -IconPath "%~dp0static\img\mr-rao.ico" 2>nul
if errorlevel 1 (
    echo       Shell integration opzionale non applicata.
) else (
    echo       Invia a / Apri con Mr. Rao configurati.
)
echo.

echo ╔═══════════════════════════════════════════════════════╗
echo ║   INSTALLAZIONE COMPLETATA                            ║
echo ║                                                       ║
echo ║   Avvio: doppio clic su "Mr. Rao" sul Desktop         ║
echo ║   oppure "Avvia Mr Rao.bat"                           ║
echo ║                                                       ║
echo ║   CLI:  venv\Scripts\python -m mr_rao.cli --help      ║
echo ║   Portable (no Python): scripts\build_portable.bat    ║
echo ║   Docs: docs\  e  README.md                           ║
echo ╚═══════════════════════════════════════════════════════╝
echo.
pause
