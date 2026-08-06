@echo off
chcp 65001 >nul 2>&1
title Disinstalla Mr. Rao Portable
set "INSTALL_DIR=%LOCALAPPDATA%\MrRao"

echo Rimuovo %INSTALL_DIR% ...
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"

del /q "%USERPROFILE%\Desktop\Mr. Rao.lnk" 2>nul
del /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Mr. Rao.lnk" 2>nul
del /q "%APPDATA%\Microsoft\Windows\SendTo\Mr. Rao.lnk" 2>nul

reg delete "HKCU\Software\Classes\*\shell\MrRao" /f 2>nul
reg delete "HKCU\Software\Classes\SystemFileAssociations\.pdf\shell\MrRao" /f 2>nul
reg delete "HKCU\Software\Classes\SystemFileAssociations\.eml\shell\MrRao" /f 2>nul
reg delete "HKCU\Software\Classes\SystemFileAssociations\.docx\shell\MrRao" /f 2>nul

echo Mr. Rao rimosso.
pause
