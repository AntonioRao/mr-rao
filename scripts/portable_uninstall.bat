@echo off
chcp 65001 >nul 2>&1
REM Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
REM SPDX-License-Identifier: AGPL-3.0-or-later
REM Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
REM GNU Affero General Public License pubblicata dalla Free Software Foundation,
REM versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
title Disinstalla Mr. Rao Portable
setlocal EnableExtensions
set "INSTALL_DIR=%LOCALAPPDATA%\MrRao"

REM Collegamenti e voci di menu li toglie lo stesso script che li crea:
REM l'elenco delle estensioni sta in un posto solo. Quando ne esistevano
REM due copie sono andate fuori sincrono, e la disinstallazione lasciava
REM voci orfane che puntavano a un eseguibile non piu' esistente:
REM cliccarle non faceva nulla, e non c'era modo di capire perche'.

REM Prima con garbo, poi sul serio. taskkill senza /F manda una richiesta
REM di chiusura che un'applicazione console puo' semplicemente ignorare: il
REM processo resta, la cartella resta bloccata, e la disinstallazione
REM finisce con un avviso invece che con una disinstallazione.
echo Chiusura di Mr. Rao, se in esecuzione...
taskkill /IM MrRao.exe >nul 2>&1
taskkill /IM MrRao.exe /F /T >nul 2>&1

echo Rimozione di %INSTALL_DIR% ...
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"
if exist "%INSTALL_DIR%" (
    echo.
    echo ATTENZIONE: non riesco a rimuovere %INSTALL_DIR%
    echo Chiudi le finestre di Esplora risorse aperte li' dentro e rilancia.
    echo I collegamenti e le voci di menu vengono tolti lo stesso.
    echo.
)

echo Rimozione collegamenti e voci di menu...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0mr_rao_shell.ps1" -InstallDir "%INSTALL_DIR%" -Remove

echo.
echo Mr. Rao rimosso.
echo Le cartelle di lavoro con i tuoi documenti NON sono state toccate.
echo.
pause
