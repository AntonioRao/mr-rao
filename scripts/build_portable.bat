@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
title Build Mr. Rao Portable
cd /d "%~dp0.."

echo.
echo === Mr. Rao portable build ===
echo Target PCs need NO Python, pip, or git.
echo.

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo Creating venv...
    python -m venv venv
    if errorlevel 1 exit /b 1
    call venv\Scripts\activate.bat
)

echo Installing build deps...
python -m pip install -q --upgrade pip
pip install -q -r requirements-build.txt
if errorlevel 1 exit /b 1

echo.
echo [1/6] Icons...
python scripts\generate_icons.py
if errorlevel 1 exit /b 1

echo.
echo [2/6] Quality gate...
call scripts\quality_gate.bat
if errorlevel 1 (
    echo GATE FAILED
    exit /b 1
)

echo.
echo [3/6] Resti di disinstallazioni nel venv...
python scripts\check_venv.py
if errorlevel 1 (
    echo.
    echo Il build si fermerebbe piu' avanti con un errore che non nomina
    echo la causa: PyInstaller importa il residuo come namespace package
    echo e poi ne chiede il percorso, che non esiste.
    exit /b 1
)

echo.
echo [4/6] PyInstaller onedir...
if exist "dist\MrRao" rmdir /s /q "dist\MrRao"
if exist "build\MrRao" rmdir /s /q "build\MrRao"

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
  --collect-all magika ^
  --collect-submodules mr_rao ^
  app.py

if errorlevel 1 (
    echo PyInstaller FAILED
    exit /b 1
)

if not exist "dist\MrRao\MrRao.exe" (
    echo ERROR: dist\MrRao\MrRao.exe missing
    exit /b 1
)

echo.
echo [5/6] Assemble portable folder...
set "OUT=dist\MrRao-Portable"
if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%"
mkdir "%OUT%\app"
xcopy /E /I /Y "dist\MrRao\*" "%OUT%\app\" >nul
copy /Y "static\img\mr-rao.ico" "%OUT%\mr-rao.ico" >nul
copy /Y "scripts\portable_install.bat" "%OUT%\Installa Mr Rao.bat" >nul
copy /Y "scripts\portable_uninstall.bat" "%OUT%\Disinstalla Mr Rao.bat" >nul
REM I due .bat lo chiamano entrambi: senza questo file l'installazione
REM arriva fino ai collegamenti e non ne crea nessuno.
copy /Y "scripts\mr_rao_shell.ps1" "%OUT%\mr_rao_shell.ps1" >nul
if not exist "%OUT%\mr_rao_shell.ps1" (
    echo ERROR: mr_rao_shell.ps1 mancante nel pacchetto
    exit /b 1
)
copy /Y "docs\PORTABLE.md" "%OUT%\LEGGIMI.txt" >nul

REM Licenze: Mr. Rao + terze parti (LGPL pystray obbligatorio in redistribuzione)
copy /Y "LICENSE" "%OUT%\LICENSE.txt" >nul
copy /Y "THIRD_PARTY.md" "%OUT%\THIRD_PARTY.md" >nul
if exist "licenses" xcopy /E /I /Y "licenses" "%OUT%\licenses\" >nul
if exist "docs\LGPL_PYSTRAY.md" (
  mkdir "%OUT%\docs" 2>nul
  copy /Y "docs\LGPL_PYSTRAY.md" "%OUT%\docs\LGPL_PYSTRAY.md" >nul
)

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
echo [6/6] Avvio dell'eseguibile e verifica...
REM Un codice di uscita zero non dice niente su cosa succede al doppio
REM clic: e' gia' capitato di produrre un pacchetto che apriva una
REM finestra nera e si chiudeva. Se ne accorse una persona, non il build.
python scripts/verify_build.py "%OUT%/app/MrRao.exe"
if errorlevel 1 (
    echo.
    echo === BUILD RESPINTO ===
    echo Il pacchetto e' stato costruito ma non funziona: non pubblicarlo.
    exit /b 1
)

echo.
echo === BUILD OK ===
echo Folder: %CD%\%OUT%
echo Licenses: %OUT%\licenses\  (includes pystray LGPL)
echo Copy that folder to USB/network. On target PC run: Installa Mr Rao.bat
echo.
exit /b 0
