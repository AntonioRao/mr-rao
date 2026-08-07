@echo off
cd /d "%~dp0.."
if exist "venv\Scripts\python.exe" (
    set PY=venv\Scripts\python.exe
) else (
    set PY=python
)
echo === Mr. Rao quality gate ===
echo [1/5] compileall...
%PY% -m compileall -q app.py config.py mr_rao
if errorlevel 1 exit /b 1
echo [2/5] health...
%PY% -m mr_rao.cli health
if errorlevel 1 exit /b 1
echo [3/5] licenze di terze parti allineate...
REM Un elenco scritto a mano invecchia in silenzio: la prima stesura
REM sbagliava la licenza di Scrubadub e ometteva python-stdnum (LGPL).
REM
REM Questo controllo confronta THIRD_PARTY.md con le versioni **installate**,
REM quindi ha senso solo dove le versioni sono quelle del manutentore. Su un
REM runner pulito pip ne risolve altre e il confronto fallisce per il motivo
REM sbagliato: non perche' l'elenco sia sbagliato, ma perche' e' un altro
REM ambiente. ci.yml lo salta gia' per questo, con lo stesso ragionamento.
REM Qui la scelta e' esplicita e ha un nome, invece di essere un passo
REM silenziosamente assente.
if defined MR_RAO_GATE_NO_LICENCE_CHECK (
    echo       saltato: MR_RAO_GATE_NO_LICENCE_CHECK impostata
) else (
    %PY% scripts\gen_third_party.py --check
    if errorlevel 1 exit /b 1
)
echo [4/5] pytest...
%PY% -m pytest tests -q --tb=short
if errorlevel 1 exit /b 1
echo [5/5] documenti pubblicati allineati...
REM Stessa malattia delle licenze, altro organo: un documento invecchia
REM senza rompere niente. Qui il conteggio dei test lo sa solo chi ha
REM appena eseguito l'intera suite, quindi il controllo sta nel gate e
REM non fra i test -- che possono essere lanciati anche su un file solo.
%PY% scripts\check_docs.py
if errorlevel 1 exit /b 1
echo === GATE PASSED ===
exit /b 0
