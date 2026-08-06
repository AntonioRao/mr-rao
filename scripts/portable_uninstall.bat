@echo off
chcp 65001 >nul 2>&1
title Disinstalla Mr. Rao Portable
setlocal EnableExtensions
set "INSTALL_DIR=%LOCALAPPDATA%\MrRao"

REM L'elenco delle estensioni deve restare identico a quello di
REM portable_install.bat. Quando divergevano, la disinstallazione lasciava
REM voci di menu orfane che puntavano a un eseguibile non piu' esistente:
REM cliccarle non faceva nulla, e l'utente non aveva modo di capire perche'.
set "ESTENSIONI=.pdf .eml .docx .doc .png .jpg .jpeg .xlsx .pptx .txt"

echo Chiusura di Mr. Rao, se in esecuzione...
taskkill /IM MrRao.exe >nul 2>&1

echo Rimozione di %INSTALL_DIR% ...
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"
if exist "%INSTALL_DIR%" (
    echo.
    echo ATTENZIONE: non riesco a rimuovere %INSTALL_DIR%
    echo Chiudi Mr. Rao e le finestre di Esplora risorse aperte li' dentro.
    echo.
)

echo Rimozione collegamenti...
del /q "%USERPROFILE%\Desktop\Mr. Rao.lnk" 2>nul
del /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Mr. Rao.lnk" 2>nul
del /q "%APPDATA%\Microsoft\Windows\SendTo\Mr. Rao.lnk" 2>nul

echo Rimozione voci del menu contestuale...
reg delete "HKCU\Software\Classes\*\shell\MrRao" /f >nul 2>&1
for %%E in (%ESTENSIONI%) do (
    reg delete "HKCU\Software\Classes\SystemFileAssociations\%%E\shell\MrRao" /f >nul 2>&1
)

echo.
echo Mr. Rao rimosso.
echo Le cartelle di lavoro con i tuoi documenti NON sono state toccate.
echo.
pause
