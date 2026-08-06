@echo off
chcp 65001 >nul 2>&1
title Mr. Rao - server locale (sviluppo)
color 0B

echo.
echo ===================================================
echo     Avvio di Mr. Rao (codice progetto, UI 2.x)
echo ===================================================
echo.
echo Questa finestra e' il server. Non chiuderla mentre
echo usi l'app nel browser.
echo.

cd /d "%~dp0"

REM NIENTE taskkill: uccidere a forza un'istanza in corso puo' lasciare
REM file .md troncati nella cartella di uscita (la conversione scrive su
REM disco). Se la porta e' occupata ci pensa app.py, che dice CHI la occupa
REM e parte sulla prima libera.

if exist "venv\Scripts\activate.bat" (
    echo Uso ambiente virtuale locale...
    call venv\Scripts\activate.bat
) else (
    echo Uso Python di sistema...
    echo Consiglio: lancia "Installa Mr Rao.bat" prima.
    echo.
)

echo Controllo health dipendenze...
python -m mr_rao.cli health
echo.

echo Avvio server dal codice di QUESTA cartella (non da dist\ o Portable)...
echo Se il browser mostra una versione vecchia: Ctrl+F5 e chiudi gli altri MrRao.exe
echo.

set MR_RAO_DEBUG=0
set MR_RAO_OPEN_BROWSER=1
python app.py
