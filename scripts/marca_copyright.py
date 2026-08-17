# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Intestazione di copyright e SPDX su ogni sorgente di prima parte.

## Perche' un'intestazione, se il repository e' gia' pubblico

Non impedisce niente: la copia di questo codice e' **gia' legale**, l'AGPL-3.0 la permette. Serve a
un'altra cosa -- rendere visibili gli obblighi che quella licenza porta con se': attribuzione, stessa
licenza sulle modifiche, codice sorgente disponibile a chi usa il servizio in rete. Un file trovato altrove
senza intestazione apre una discussione su chi l'abbia scritto e su cosa sia dovuto; lo stesso file con
nome, anno e licenza la chiude subito, e toglie la difesa piu' comoda -- "non sapevo fosse coperto".

## Cosa NON si marca, e perche' e' importante sbagliare per difetto

Codice di terze parti porta la **sua** licenza: metterci sopra la nostra sarebbe una falsa attribuzione --
lo stesso illecito da cui ci si difende, al contrario. Qui non ce n'e' di vendorizzato nel repository (le
dipendenze Python arrivano da pip, dichiarate in THIRD_PARTY.md), ma il filtro resta per percorso oltre che
per estensione: `docs/landing/publish/index.html` e `docs/landing/publish/en/index.html` sono **output
rigenerato** da `_rebuild.py` a partire dai sorgenti in `docs/landing/`, e marcarli vorrebbe dire perdere
l'intestazione alla prossima rigenerazione senza che nessuno se ne accorga. Il resto di
`docs/landing/publish/` (`impresa/`, `plus/`, `sito-nav.css`) non e' generato da niente: sono pagine vere,
e si marcano come qualunque altro sorgente -- l'esclusione e' sui due file esatti, non sulla cartella.

Nel dubbio il file resta senza intestazione: un file di prima parte non marcato e' un'occasione persa, un
file altrui marcato e' un problema legale.

## Vincoli tecnici da non dimenticare

Lo shebang e la riga di codifica restano in cima, prima dell'intestazione. `@echo off` nei `.bat` resta
primo per lo stesso motivo: e' quello che spegne l'eco dei comandi, e un commento scritto sopra verrebbe
stampato a schermo una volta. Il BOM si conserva se un file lo ha gia'; il testo dell'intestazione stessa e'
scritto in ASCII puro (apostrofo al posto dell'accento, come il resto dei commenti di questo repository) per
non introdurre in un `.ps1` senza BOM il primo carattere accentato che PowerShell 5.1 non saprebbe leggere.

## Idempotente

Riconosce l'intestazione dalla riga SPDX e non la duplica. Rilanciarlo aggiorna l'anno se e' cambiato.

Uso:  python scripts/marca_copyright.py            elenca cosa farebbe
      python scripts/marca_copyright.py --scrivi   applica
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANNO = "2026"
TITOLARE = "Antonio Andrea Rao"
SPDX = "AGPL-3.0-or-later"

RIGHE = [
    f"Mr. Rao -- Copyright (c) {ANNO} {TITOLARE}.",
    f"SPDX-License-Identifier: {SPDX}",
    "Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della",
    "GNU Affero General Public License pubblicata dalla Free Software Foundation,",
    "versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.",
]

# Estensione -> famiglia di commento. Tre famiglie, non due come in VALOR: qui c'e'
# anche il markup, e i .bat non capiscono `#`.
CANCELLETTO = {".py", ".ps1", ".sh"}
REM_STYLE = {".bat"}
BLOCCO = {".js", ".css"}
HTML_STYLE = {".html"}
ESTENSIONI = CANCELLETTO | REM_STYLE | BLOCCO | HTML_STYLE

# Percorsi generati: la prossima build li riscrive comunque, marcarli e' inutile e
# rischia di perdere l'intestazione senza che nessuno se ne accorga. Sono SOLO i due
# file che _rebuild.py scrive (vedi PAGINE li'), non l'intera cartella: dentro
# docs/landing/publish/ vivono anche pagine vere non generate (impresa/, plus/,
# sito-nav.css), e un'esclusione per prefisso le avrebbe scambiate per output.
ALTRUI = re.compile(r"^docs/landing/publish/(index\.html|en/index\.html)$")

# Righe che devono restare in cima al file, prima di qualunque commento nostro.
PRIMA = re.compile(r"^(#!|# -\*- coding|<!DOCTYPE|@charset|'use strict'|@echo off|chcp\s)")


def sorgenti() -> list[str]:
    fuori = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8").stdout.splitlines()
    return [p for p in fuori
            if Path(p).suffix in ESTENSIONI and not ALTRUI.search(p)]


def intestazione(suffisso: str) -> str:
    if suffisso in CANCELLETTO:
        return "".join(f"# {r}\n" for r in RIGHE)
    if suffisso in REM_STYLE:
        return "".join(f"REM {r}\n" for r in RIGHE)
    if suffisso in HTML_STYLE:
        return "<!--\n" + "\n".join(f"  {r}" for r in RIGHE) + "\n-->\n"
    return "/* " + "\n   ".join(RIGHE) + " */\n"


def applica(percorso: str, scrivi: bool) -> str:
    f = ROOT / percorso
    grezzo = f.read_bytes()
    # Il BOM si conserva: se domani un .ps1 di questo elenco arrivasse con caratteri
    # accentati e un BOM gia' suo, toglierlo romperebbe PowerShell 5.1 senza un errore
    # visibile. L'intestazione che scriviamo e' ASCII, ma il resto del file puo' non
    # esserlo.
    bom = grezzo.startswith(b"\xef\xbb\xbf")
    testo = grezzo.decode("utf-8-sig")
    # L'intestazione SPDX si controlla PRIMA di quella in prosa, non dopo: le sue
    # stesse righe contengono "GNU Affero General Public License" (RIGHE qui sopra),
    # quindi un file gia' marcato da questo script supererebbe anche il controllo
    # prosa. Nell'ordine sbagliato il ramo che aggiorna l'anno non scatterebbe mai
    # su un file marcato da noi -- trovato da un test di mutazione (tests/test_tutela_codice.py)
    # che marca un file e ricontrolla: senza questo ordine tornava "gia' marcato
    # (prosa)" invece di rifare il controllo sull'anno.
    if f"SPDX-License-Identifier: {SPDX}" in testo[:2000]:
        vecchio = re.search(r"Copyright \(c\) (\d{4})", testo[:2000])
        if vecchio and vecchio.group(1) != ANNO:
            testo = testo[:2000].replace(f"Copyright (c) {vecchio.group(1)}",
                                         f"Copyright (c) {ANNO}") + testo[2000:]
            if scrivi:
                f.write_bytes((b"\xef\xbb\xbf" if bom else b"") + testo.encode("utf-8"))
            return "anno aggiornato"
        return "gia' marcato"
    # Due file (app.py, mr_rao/__init__.py) portano gia' una nota AGPL completa in
    # prosa inglese, non nel formato SPDX: aggiungere la nostra sopra sarebbe una
    # duplicazione visibile, non un'intestazione mancante. La finestra e' stretta
    # (1500 caratteri) apposta -- i18n.py contiene la stessa frase, ma dentro un
    # dizionario di traduzioni mostrate a schermo, molto piu' in basso nel file: a
    # quella distanza non e' la nota del file, e' un valore.
    if "GNU Affero General Public License" in testo[:1500]:
        return "gia' marcato (prosa)"

    righe = testo.split("\n")
    i = 0
    while i < len(righe) and PRIMA.match(righe[i].strip()):
        i += 1
    testa = "\n".join(righe[:i]) + ("\n" if i else "")
    coda = "\n".join(righe[i:])
    nuovo = testa + intestazione(Path(percorso).suffix) + coda
    if scrivi:
        f.write_bytes((b"\xef\xbb\xbf" if bom else b"") + nuovo.encode("utf-8"))
    return "marcato"


def main() -> None:
    scrivi = "--scrivi" in sys.argv
    conti: dict[str, int] = {}
    for p in sorgenti():
        esito = applica(p, scrivi)
        conti[esito] = conti.get(esito, 0) + 1
    print(f"sorgenti di prima parte: {sum(conti.values())}")
    for k, v in sorted(conti.items()):
        print(f"  {k}: {v}")
    if not scrivi:
        print("(prova a vuoto: non ho scritto niente -- rilancia con --scrivi)")


main()
