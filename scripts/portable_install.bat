@echo off
chcp 65001 >nul 2>&1
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

echo Creazione collegamento Desktop e menu Start...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root='%~dp0'; $inst='%INSTALL_DIR%'; $ico=Join-Path $inst 'mr-rao.ico'; if (-not (Test-Path $ico)) { $ico = Join-Path $inst 'app\mr-rao.ico' }; $exe=Join-Path $inst 'app\MrRao.exe'; $desk=[Environment]::GetFolderPath('Desktop'); $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut((Join-Path $desk 'Mr. Rao.lnk')); $s.TargetPath=$exe; $s.WorkingDirectory=(Join-Path $inst 'app'); $s.Description='Mr. Rao - Markdown offline'; if (Test-Path $ico) { $s.IconLocation=\"$ico,0\" }; $s.Save(); $start=Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'; $s2=$w.CreateShortcut((Join-Path $start 'Mr. Rao.lnk')); $s2.TargetPath=$exe; $s2.WorkingDirectory=(Join-Path $inst 'app'); if (Test-Path $ico) { $s2.IconLocation=\"$ico,0\" }; $s2.Save(); Write-Host 'Shortcut OK'"

echo Menu contestuale / Invia a...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$exe='%INSTALL_DIR%\app\MrRao.exe'; $ico='%INSTALL_DIR%\mr-rao.ico'; if (-not (Test-Path $ico)) { $ico=$exe }; $sendTo=[Environment]::GetFolderPath('SendTo'); $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut((Join-Path $sendTo 'Mr. Rao.lnk')); $s.TargetPath=$exe; $s.WorkingDirectory=(Split-Path $exe); $s.IconLocation=\"$ico,0\"; $s.Save(); function Set-Verb($p){ New-Item -Path $p -Force|Out-Null; Set-ItemProperty -Path $p -Name '(Default)' -Value 'Apri con Mr. Rao'; Set-ItemProperty -Path $p -Name 'Icon' -Value $ico; $c=Join-Path $p 'command'; New-Item -Path $c -Force|Out-Null; Set-ItemProperty -Path $c -Name '(Default)' -Value ('\"{0}\" \"%%1\"' -f $exe) }; Set-Verb 'HKCU:\Software\Classes\*\shell\MrRao'; foreach($e in @('.pdf','.eml','.docx','.png','.jpg','.xlsx','.txt')){ Set-Verb (\"HKCU:\\Software\\Classes\\SystemFileAssociations\\$e\\shell\\MrRao\") }; Write-Host 'Shell OK'"

echo.
echo Installazione completata.
echo Avvia da Desktop: Mr. Rao
echo Oppure: %INSTALL_DIR%\app\MrRao.exe
echo.
pause
