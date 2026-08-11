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
echo [1/7] Icone (gia' versionate, si controlla che ci siano)...
REM Le icone NON si rigenerano qui. Sono artefatti versionati, prodotti da
REM scripts\generate_icons.py quando cambia il disegno -- che richiede
REM svglib/rlPyCairo, librerie che di proposito non stanno in
REM requirements.txt perche' il prodotto non le usa.
REM
REM Rigenerarle a ogni build voleva dire due cose, entrambe successe: la
REM build si rompe su una macchina che non ha quegli strumenti, e su una
REM macchina con caratteri diversi il pacchetto esce con un marchio
REM leggermente diverso da quello nel repository. Qui si verifica solo che
REM i file esistano.
python -c "import sys;from pathlib import Path;m=[f for f in ('static/img/logo.png','static/img/favicon.ico','static/img/mr-rao.ico','static/img/favicon-64.png') if not Path(f).exists()];sys.exit(('mancano: '+', '.join(m)) if m else 0)"
if errorlevel 1 exit /b 1

REM Licenze rigenerate dentro QUESTO venv, se richiesto.
REM
REM Serve quando il pacchetto costruito qui verra' distribuito: THIRD_PARTY.md
REM elenca le versioni risolte sulla macchina di chi l'ha generato, e su un
REM runner pulito pip ne installa altre. Finche' il build serve solo a dire
REM si'/no la differenza e' accettabile; da quando il pacchetto viene firmato
REM e pubblicato non lo e' piu', perche' si distribuirebbe un elenco di
REM licenze che non descrive cio' che c'e' dentro -- e fra quelle c'e'
REM pystray (LGPL), che in redistribuzione ha obblighi veri.
REM
REM Sta qui e non nel workflow di proposito: qui il venv e' gia' quello che
REM costruira' il pacchetto, quindi «stesso ambiente» e' vero per
REM costruzione. Nel workflow avrebbe richiesto un `pip install` suo, cioe'
REM proprio l'ambiente preparato a mano che quel lavoro deve escludere.
REM
REM Spento di default: in locale THIRD_PARTY.md e' un file versionato, e
REM riscriverlo a ogni build lascerebbe modifiche non richieste.
if defined MR_RAO_RIGENERA_LICENZE (
    echo Licenze rigenerate da questo venv...
    python scripts\gen_third_party.py
    if errorlevel 1 exit /b 1
)

echo.
echo [2/7] Quality gate...
call scripts\quality_gate.bat
if errorlevel 1 (
    echo GATE FAILED
    exit /b 1
)

echo.
echo [3/7] Resti di disinstallazioni nel venv...
python scripts\check_venv.py
if errorlevel 1 (
    echo.
    echo Il build si fermerebbe piu' avanti con un errore che non nomina
    echo la causa: PyInstaller importa il residuo come namespace package
    echo e poi ne chiede il percorso, che non esiste.
    exit /b 1
)

echo.
echo [4/7] PyInstaller onedir...
if exist "dist\MrRao" rmdir /s /q "dist\MrRao"
if exist "build\MrRao" rmdir /s /q "build\MrRao"

REM `--noconsole`: niente finestra nera al doppio click.
REM
REM ATTENZIONE: la trappola sta qui e NON in MrRao.spec. Quel file non e'
REM tracciato (.gitignore, riga `*.spec`) ed e' rigenerato da PyInstaller a
REM ogni build proprio da questa riga di comando. Correggere `console=True`
REM li' dentro sembra risolvere e non cambia niente: al build successivo il
REM file viene riscritto da qui. Il punto unico e' questo flag, e la CI lancia
REM questo stesso .bat.
REM
REM Da solo `--noconsole` romperebbe la riga di comando: senza console
REM allegata `sys.stdout` diventa `None`, e `MrRao.exe convert file.pdf`
REM funzionerebbe senza stampare niente -- il modo peggiore di rompersi. La
REM console si aggancia quando serve, in `console_win.py`, chiamato come prima
REM riga di app.py. **Le due cose vanno insieme.**
pyinstaller --noconfirm --clean --onedir --noconsole --name MrRao ^
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
  --hidden-import=rapidocr ^
  --hidden-import=docx ^
  --hidden-import=pdfplumber ^
  --hidden-import=PIL ^
  --collect-all rapidocr ^
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
echo [5/7] Assemble portable folder...
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
echo [6/7] Avvio dell'eseguibile e verifica...
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
echo [7/7] Archivi per la release...
REM Due archivi, stesso contenuto. Quello a nome fisso serve perche'
REM GitHub pubblica /releases/latest/download/NOME solo se NOME non cambia
REM da una versione all'altra: e' cio' che rende possibile il link di
REM scaricamento diretto nei README. Creandoli qui non si puo' dimenticare
REM il secondo -- e dimenticarlo rompe quei link in silenzio.
python scripts\make_release_zip.py
if errorlevel 1 exit /b 1

echo.
echo === BUILD OK ===
echo Folder: %CD%\%OUT%
echo Licenses: %OUT%\licenses\  (includes pystray LGPL)
echo Copy that folder to USB/network. On target PC run: Installa Mr Rao.bat
echo.
exit /b 0
