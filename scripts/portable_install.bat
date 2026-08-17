@echo off
chcp 65001 >nul 2>&1
REM Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
REM SPDX-License-Identifier: AGPL-3.0-or-later
REM Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
REM GNU Affero General Public License pubblicata dalla Free Software Foundation,
REM versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
title Installazione Mr. Rao Portable
cd /d "%~dp0"

echo.
echo ╔═══════════════════════════════════════════════════════╗
echo ║     MR. RAO PORTABLE — Installazione locale           ║
echo ║     Nessun Python, pip o git richiesti                ║
echo ╚═══════════════════════════════════════════════════════╝
echo.

if not exist "app\MrRao.exe" (
    echo ERRORE: manca app\MrRao.exe
    echo Questa cartella deve essere il pacchetto generato da build_portable.
    pause
    exit /b 1
)

set "INSTALL_DIR=%LOCALAPPDATA%\MrRao"
echo Destinazione: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Aggiornando una versione precedente, xcopy sovrascrive ma non rimuove: i
REM file di dipendenze non piu' incluse resterebbero li' per sempre. Misurato
REM aggiornando da 1.3.2 a 1.3.3: 120 MB di librerie morte rimaste sul disco.
if exist "%INSTALL_DIR%\app" (
    echo Rimozione versione precedente...
    rmdir /s /q "%INSTALL_DIR%\app" 2>nul
    if exist "%INSTALL_DIR%\app" (
        echo.
        echo ATTENZIONE: non riesco a rimuovere la versione precedente.
        echo Probabilmente Mr. Rao e' in esecuzione: chiudilo e rilancia.
        echo.
        pause
        exit /b 1
    )
)

echo Copia file...
xcopy /E /I /Y "app\*" "%INSTALL_DIR%\app\" >nul
if exist "mr-rao.ico" copy /Y "mr-rao.ico" "%INSTALL_DIR%\mr-rao.ico" >nul
if exist "app\mr-rao.ico" copy /Y "app\mr-rao.ico" "%INSTALL_DIR%\mr-rao.ico" >nul 2>nul
if exist "static\img\mr-rao.ico" copy /Y "static\img\mr-rao.ico" "%INSTALL_DIR%\mr-rao.ico" >nul 2>nul

:: Prefer ico next to install
if not exist "%INSTALL_DIR%\mr-rao.ico" if exist "%~dp0mr-rao.ico" copy /Y "%~dp0mr-rao.ico" "%INSTALL_DIR%\mr-rao.ico" >nul

echo Collegamenti e menu contestuale...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0mr_rao_shell.ps1" -InstallDir "%INSTALL_DIR%"
set "SHELL_RC=%ERRORLEVEL%"

echo.
if "%SHELL_RC%"=="0" (
    echo Installazione completata.
    echo Avvia da Desktop: Mr. Rao
) else (
    echo Installazione completata, ma con qualche collegamento in meno.
    echo Vedi le righe FALLITO qui sopra.
)
echo Oppure: %INSTALL_DIR%\app\MrRao.exe
echo.
pause
