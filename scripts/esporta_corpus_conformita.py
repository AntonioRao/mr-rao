# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Congela cosa fa il motore di redazione, caso per caso, per chi lo riscrive.

Il motore (`mr_rao/privacy.py`, `mr_rao/en_formats.py`, `mr_rao/it_names.py`)
sta per essere portato in TypeScript per un prodotto separato. Due
implementazioni della stessa regola non restano uguali da sole: divergono, e
in un motore di redazione una divergenza non si vede — il documento esce
lo stesso, con dentro un dato in piu' o una parola di troppo tolta. E' una
fuga silenziosa, cioe' il modo peggiore di sbagliare per un programma il cui
mestiere e' far vedere cosa e' stato tolto.

La contromisura non e' una specifica scritta in prosa: e' un **corpus di
conformita'**. Ingressi congelati (`corpus/casi.jsonl`, curato a mano) e
uscite esatte (`corpus/atteso.json`, generato da qui). L'implementazione
TypeScript non deve somigliare a questa: deve riprodurre queste stringhe,
carattere per carattere, e questi conteggi, voce per voce.

**I due file hanno due nature diverse, e non vanno confuse.** `casi.jsonl`
si scrive una volta e si allunga: e' copertura, e togliere una riga vuol
dire smettere di guardare un caso. `atteso.json` e' un artefatto: si
rigenera ogni volta che il motore cambia di proposito, e il diff mostra
esattamente cosa e' cambiato — che e' il momento in cui ci si accorge di
aver cambiato anche qualcos'altro.

**L'impronta e' cio' che rende il meccanismo vivo.** Nel file finisce la
versione dell'applicazione e lo SHA-256 dei tre sorgenti del motore.
`tests/test_corpus_conformita.py` la riverifica: se qualcuno tocca il motore
e non rigenera, la suite Python diventa rossa **qui**, non fra sei mesi
sull'estensione. Senza impronta il corpus resterebbe verde mentre invecchia,
e un corpus invecchiato e' peggio di nessun corpus: dice di si' a una
implementazione che riproduce fedelmente un motore che non esiste piu'.

Uso:  venv\\Scripts\\python scripts\\esporta_corpus_conformita.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from config import APP_VERSION  # noqa: E402
from mr_rao.privacy import apply_privacy_filter, options_from_dict  # noqa: E402

CASI = RADICE / "corpus" / "casi.jsonl"
ATTESO = RADICE / "corpus" / "atteso.json"

# I tre file che l'implementazione TypeScript deve riprodurre. L'elenco e'
# esplicito e non un glob su `mr_rao/`: un modulo che non c'entra col motore
# — l'interfaccia, l'OCR — cambia di continuo, e farne dipendere l'impronta
# vorrebbe dire chiedere di rigenerare il corpus per motivi che col motore
# non hanno niente a che fare. A quel punto lo si rigenera senza guardare il
# diff, ed e' come non averlo.
SORGENTI = ("mr_rao/privacy.py", "mr_rao/en_formats.py", "mr_rao/it_names.py")


def leggi_casi() -> list[dict]:
    """Un oggetto JSON per riga, nell'ordine in cui sono scritti.

    L'ordine si conserva perche' e' l'ordine in cui il corpus si legge: i
    casi di uno stesso riconoscitore stanno vicini, e un diff che li
    rimescolasse renderebbe illeggibile proprio il file che esiste per
    essere letto.
    """
    casi: list[dict] = []
    visti: set[str] = set()
    for n, riga in enumerate(CASI.read_text(encoding="utf-8").splitlines(), 1):
        riga = riga.strip()
        if not riga or riga.startswith("//"):
            continue
        try:
            caso = json.loads(riga)
        except json.JSONDecodeError as e:
            raise SystemExit(f"{CASI.name}, riga {n}: JSON non valido ({e})")
        for campo in ("id", "gruppo", "testo", "opzioni", "nota"):
            if campo not in caso:
                raise SystemExit(f"{CASI.name}, riga {n}: manca il campo '{campo}'")
        if caso["id"] in visti:
            # Due casi con lo stesso identificativo: il secondo scriverebbe
            # sopra il primo nell'atteso, e la copertura sparirebbe senza
            # che nessuno perda una riga da nessuna parte.
            raise SystemExit(f"{CASI.name}, riga {n}: id duplicato '{caso['id']}'")
        visti.add(caso["id"])
        casi.append(caso)
    return casi


def impronta() -> dict:
    """Versione dell'app e SHA-256 dei sorgenti del motore.

    **I fine riga vengono normalizzati prima di calcolare l'impronta**, e non
    e' pignoleria: la prima versione leggeva i byte grezzi ed e' diventata
    rossa in CI il giorno stesso. Su Windows git converte in CRLF nella copia
    di lavoro, sul runner Linux resta LF: stesso contenuto, byte diversi,
    impronta diversa. Il controllo diceva «il motore e' cambiato» quando il
    motore non era stato toccato.

    Un controllo che grida al lupo per una causa che non c'entra e' peggio di
    uno assente: la prima volta lo si indaga, la seconda si rigenera il
    corpus per far tacere il rosso — ed e' esattamente il gesto che questo
    presidio esiste per impedire.
    """
    return {
        "app": APP_VERSION,
        "sorgenti": {nome: sha_sorgente(RADICE / nome) for nome in SORGENTI},
    }


def sha_sorgente(percorso) -> str:
    """SHA-256 del contenuto, indipendente da come git ha scritto le righe."""
    testo = percorso.read_text(encoding="utf-8")
    return hashlib.sha256(testo.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def esegui(caso: dict) -> dict:
    """Il caso passato nel motore, esattamente come lo passa l'applicazione."""
    uscita, rapporto = apply_privacy_filter(
        caso["testo"], options_from_dict(caso["opzioni"])
    )
    return {
        "gruppo": caso["gruppo"],
        "uscita": uscita,
        "report": rapporto.to_dict(),
    }


def calcola(casi: list[dict]) -> dict:
    return {
        "motore": impronta(),
        "casi": {caso["id"]: esegui(caso) for caso in casi},
    }


def main() -> int:
    if not CASI.is_file():
        print(f"ERRORE: manca il corpus {CASI}", file=sys.stderr)
        return 1
    casi = leggi_casi()
    dati = calcola(casi)
    ATTESO.parent.mkdir(parents=True, exist_ok=True)
    ATTESO.write_text(
        json.dumps(dati, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    # Il riepilogo non e' decorazione: e' l'unico momento in cui si vede se
    # il corpus e' ancora capace di dire di no. Un corpus di soli casi
    # positivi non puo' accorgersi di un motore che redige troppo, e
    # dall'esterno ha esattamente lo stesso aspetto di uno buono.
    con_dati = sum(1 for c in dati["casi"].values() if c["report"]["total"] > 0)
    puliti = sum(1 for c in dati["casi"].values() if c["report"]["total"] == 0)
    sospetti = sum(
        1 for c in dati["casi"].values() if c["report"]["suspects_total"] > 0
    )
    print(f"  scritto {ATTESO.relative_to(RADICE)}")
    print(f"  {len(casi)} casi, {len(set(c['gruppo'] for c in casi))} gruppi")
    print(f"  {con_dati} con sostituzioni, {puliti} senza, {sospetti} con sospetti")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
