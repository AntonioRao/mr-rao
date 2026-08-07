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

echo [1/6] Verifica Python...
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

echo [2/6] Creazione ambiente virtuale (venv)...
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

echo [3/6] Installazione dipendenze (include beautifulsoup4, Flask, RapidOCR...)...
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

echo [5/6] Generazione icone (logo, favicon, mr-rao.ico)...
python scripts\generate_icons.py
if %ERRORLEVEL% neq 0 (
    echo       AVVISO: generazione icone fallita — lo shortcut usera' l'icona di default.
) else (
    echo       Icone OK: static\img\mr-rao.ico
)
echo.

echo [6/6] Collegamenti e menu contestuale...
REM Stesso script del pacchetto portable, con i percorsi di questa
REM installazione: da sorgente non c'e' un MrRao.exe, quindi il
REM collegamento punta al .bat di avvio, il menu contestuale a quello che
REM accetta un file come argomento, e l'icona al .ico del repository.
REM
REM Prima qui c'erano due script separati che facevano la stessa cosa in
REM modo leggermente diverso da quello del pacchetto: l'elenco delle
REM estensioni viveva in due posti, e la disinstallazione ne conosceva uno
REM solo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\mr_rao_shell.ps1" -InstallDir "%~dp0" -Avvio "%~dp0Avvia Mr Rao.bat" -ApriCon "%~dp0scripts\open_with_mr_rao.bat" -Icona "%~dp0static\img\mr-rao.ico"
if errorlevel 1 (
    echo       AVVISO: alcuni collegamenti non sono stati creati.
    echo               Mr. Rao si avvia comunque da "Avvia Mr Rao.bat".
) else (
    echo       Collegamenti e menu contestuale configurati.
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
