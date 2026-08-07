@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0.."
REM --attendi tiene aperta la finestra quando c'e' qualcosa da leggere:
REM redazioni fatte o, soprattutto, sospetti. Prima si chiudeva sempre
REM all'istante e restava un .md senza alcuna idea di cosa fosse stato
REM tolto o segnalato -- il percorso piu' comodo, e quindi il piu' usato,
REM saltava in silenzio il controllo che PRIVACY.md chiama «quello che
REM conta». Su un documento pulito continua a chiudersi da sola: fermarsi
REM per dire «niente» insegna a chiudere senza leggere.
if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -m mr_rao.cli convert --attendi %*
) else (
    python -m mr_rao.cli convert --attendi %*
)
if errorlevel 1 pause
