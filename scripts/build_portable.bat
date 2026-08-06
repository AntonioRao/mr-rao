@echo off
chcp 65001 >nul 2>&1
title Build Mr. Rao Portable (offline, no Python on target)
cd /d "%~dp0.."

echo.
echo === Mr. Rao — build pacchetto portable ===
echo Nessun git/pip richiesto sul PC destinazione.
echo.

if not exist "venv\Scripts\python.exe" (
    echo Crea venv e installa dipendenze...
    python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements-build.txt
) else (
    call venv\Scripts\activate.bat
    pip install -q -r requirements-build.txt
)

echo.
echo [1/4] Icone...
python scripts\generate_icons.py

echo.
echo [2/4] Quality gate...
call scripts\quality_gate.bat
if errorlevel 1 (
    echo GATE FALLITO — interrompo la build.
    exit /b 1
)

echo.
echo [3/4] PyInstaller (onedir, tutte le dipendenze incluse)...
if exist "dist\MrRao" rmdir /s /q "dist\MrRao"
if exist "build\MrRao" rmdir /s /q "build\MrRao"

:: --console: consente CLI convert / "Apri con"; tray e UI restano disponibili
pyinstaller --noconfirm --clean --onedir --console --name MrRao ^
  --icon "static\img\mr-rao.ico" ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --hidden-import=mr_rao ^
  --hidden-import=mr_rao.routes ^
  --hidden-import=mr_rao.converter ^
  --hidden-import=mr_rao.eml_parser ^
  --hidden-import=mr_rao.ocr_service ^
  --hidden-import=mr_rao.privacy ^
  --hidden-import=mr_rao.profiles ^
  --hidden-import=mr_rao.watch_service ^
  --hidden-import=mr_rao.jobs ^
  --hidden-import=mr_rao.tray ^
  --hidden-import=mr_rao.cli ^
  --hidden-import=bs4 ^
  --hidden-import=rapidocr_onnxruntime ^
  --hidden-import=pdfplumber ^
  --hidden-import=PIL ^
  --collect-all rapidocr_onnxruntime ^
  --collect-all onnxruntime ^
  --collect-all markitdown ^
  --collect-submodules mr_rao ^
  app.py

if errorlevel 1 (
    echo PyInstaller FALLITO
    exit /b 1
)

echo.
echo [4/4] Assemblaggio cartella portable...
set OUT=dist\MrRao-Portable
if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%"
xcopy /E /I /Y "dist\MrRao\*" "%OUT%\app\" >nul
copy /Y "static\img\mr-rao.ico" "%OUT%\mr-rao.ico" >nul
copy /Y "scripts\portable_install.bat" "%OUT%\Installa Mr Rao.bat" >nul
copy /Y "scripts\portable_uninstall.bat" "%OUT%\Disinstalla Mr Rao.bat" >nul
copy /Y "docs\PORTABLE.md" "%OUT%\LEGGIMI.txt" >nul 2>nul
if not exist "%OUT%\LEGGIMI.txt" (
  echo Mr. Rao Portable > "%OUT%\LEGGIMI.txt"
  echo Esegui "Installa Mr Rao.bat" — non serve Python ne' git. >> "%OUT%\LEGGIMI.txt"
)

:: launcher console-friendly for CLI
(
echo @echo off
echo cd /d "%%~dp0app"
echo start "" "MrRao.exe" %%*
) > "%OUT%\Avvia Mr Rao.bat"

(
echo @echo off
echo cd /d "%%~dp0app"
echo MrRao.exe %%*
) > "%OUT%\MrRao-CLI.bat"

echo.
echo === BUILD COMPLETATA ===
echo Cartella: %CD%\%OUT%
echo Copia l'intera cartella su USB / rete e sul PC target esegui:
echo   Installa Mr Rao.bat
echo.
exit /b 0
