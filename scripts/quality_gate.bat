@echo off
REM Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
REM SPDX-License-Identifier: AGPL-3.0-or-later
REM Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
REM GNU Affero General Public License pubblicata dalla Free Software Foundation,
REM versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
cd /d "%~dp0.."
if exist "venv\Scripts\python.exe" (
    set PY=venv\Scripts\python.exe
) else (
    set PY=python
)
echo === Mr. Rao quality gate ===
echo [1/6] compileall...
%PY% -m compileall -q app.py config.py mr_rao
if errorlevel 1 exit /b 1
REM compileall vede la sintassi, non gli import: un modulo che esplode al
REM caricamento -- import circolare, un nome che non c'e' -- lo supera a
REM pieni voti e rompe il programma. Il controllo girava gia' in CI e
REM nell'hook opzionale, ma non qui: mancava proprio a chi lancia il gate
REM prima di una pull request, cioe' a chi lo usa piu' spesso.
echo [2/6] import di ogni modulo...
%PY% scripts\check_import.py
if errorlevel 1 exit /b 1
echo [3/6] health...
%PY% -m mr_rao.cli health
if errorlevel 1 exit /b 1
echo [4/6] licenze di terze parti allineate...
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
echo [5/6] pytest...
%PY% -m pytest tests -q --tb=short
if errorlevel 1 exit /b 1
echo [6/6] documenti pubblicati allineati...
REM Stessa malattia delle licenze, altro organo: un documento invecchia
REM senza rompere niente. Qui il conteggio dei test lo sa solo chi ha
REM appena eseguito l'intera suite, quindi il controllo sta nel gate e
REM non fra i test -- che possono essere lanciati anche su un file solo.
%PY% scripts\check_docs.py
if errorlevel 1 exit /b 1
echo === GATE PASSED ===
exit /b 0
