# Mr. Rao quality gate, per chi lavora in PowerShell.
#
# Questo file non ripete i passi del gate: li esegue chiamando
# quality_gate.bat, che ne resta l'unica definizione.
#
# Prima era una seconda implementazione, e ha fatto esattamente quello che
# fanno le seconde implementazioni: e' rimasta indietro. Diceva "[1/3]"
# quando i passi erano cinque, non conosceva il controllo delle licenze ne'
# quello dei documenti pubblicati, e nessuno la chiamava -- quindi nessuno
# se ne accorgeva. Chi apriva il repository e leggeva questo file si faceva
# un'idea sbagliata di cosa venga controllato prima di un commit.
#
# Un solo elenco di passi, due modi di lanciarlo.

$ErrorActionPreference = 'Continue'

$gate = Join-Path $PSScriptRoot 'quality_gate.bat'
if (-not (Test-Path $gate)) {
    Write-Host "ERRORE: manca $gate" -ForegroundColor Red
    exit 1
}

& $gate
exit $LASTEXITCODE
