# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Scarica le righe **italiane** di Ai4Privacy, e nient'altro.

Perche' solo l'italiano
-----------------------

Il corpus ha 464k righe in otto lingue; a noi servono le 55 004 italiane, e
prenderle con il filtro del server invece di scaricare 566 MB e buttarne il
88% e' l'unica differenza fra un banco che si rifa' in dieci minuti e uno
che nessuno rifa'.

Licenza -- da leggere prima di usarlo
-------------------------------------

`ai4privacy/open-pii-masking-500k` NON e' semplicemente CC-BY-4.0, come si
legge in giro. Il campo `license` dice `other`, e il README spiega perche':
il dataset e' stato **generato con Llama 3.1/3.3**, quindi porta con se' la
**Llama Community License** e la relativa Acceptable Use Policy, che si
ereditano usandolo e ridistribuendolo.

Qui non si ridistribuisce niente: le righe restano sul disco di chi esegue
lo script, come per il corpus pubblico. Ma l'attribuzione va in `NOTICE.md`
e la catena di licenze va guardata **prima** di legarla a un prodotto
commerciale.

Cosa questo corpus NON puo' misurare
------------------------------------

Le righe italiane sono **tradotte a macchina e sintetiche**: «luglio 4o,
2008» e' «July 4th, 2008» passato in italiano, e «Christopherus Kimete» non
e' un nome italiano. Misurare qui il richiamo dei **nomi** e delle **date**
darebbe un numero falso in basso, e la reazione istintiva a un richiamo
basso e' allentare le guardie -- la direzione degli 8 904 errori di
`name_guess`.

Per i nomi italiani la fonte resta la Gazzetta Ufficiale. Questo corpus
serve ai riconoscitori dove conta **la forma** e non la lingua, ed e' il
banco `bench_richiamo_forme.py` a dire quali, e perche' gli altri no.

Uso
---

    venv\\Scripts\\python scripts\\scarica_corpus_ai4privacy.py --in CARTELLA
    venv\\Scripts\\python scripts\\scarica_corpus_ai4privacy.py --in CARTELLA --quante 5000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DATASET = "ai4privacy/open-pii-masking-500k-ai4privacy"
BASE = "https://datasets-server.huggingface.co/filter"
LOTTO = 100  # il massimo che il servizio restituisce per richiesta
NOME = "ai4privacy-it.jsonl"


def indirizzo(offset: int, quante: int) -> str:
    q = urllib.parse.urlencode(
        {
            "dataset": DATASET,
            "config": "default",
            "split": "train",
            "where": "\"language\"='it'",
            "offset": offset,
            "limit": quante,
        }
    )
    return f"{BASE}?{q}"


ATTESE = (2, 5, 12, 30, 60, 120)  # crescente: il 500 e' di carico, non di richiesta


def un_lotto(offset: int, quante: int) -> tuple[list[dict], int]:
    """Un lotto di righe, con parecchi tentativi. Solleva se non ce la fa.

    Non restituisce una lista vuota in caso di errore: un lotto perso in
    silenzio farebbe un corpus piu' piccolo del previsto, e un banco che
    misura su meno righe di quante crede da' numeri piu' bassi senza che
    nessuno sappia perche'.

    L'attesa cresce fino a due minuti perche' il servizio sbaglia **a
    intermittenza**: lo stesso offset risponde 500 e poi 200 senza che sia
    cambiato niente. Con quattro tentativi ravvicinati un lotto su cento
    fallisce, e per un corpus da 120 richieste vuol dire che lo
    scaricamento non arriva quasi mai in fondo.
    """
    ultimo: Exception | None = None
    for attesa in (*ATTESE, None):
        try:
            with urllib.request.urlopen(indirizzo(offset, quante), timeout=90) as r:
                d = json.load(r)
            return [x["row"] for x in d["rows"]], int(d.get("num_rows_total", 0))
        except (urllib.error.URLError, OSError, TimeoutError, ValueError) as e:
            ultimo = e
            if attesa is None:
                break
            time.sleep(attesa)
    raise RuntimeError(f"lotto a offset {offset} non recuperato: {ultimo}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--in", dest="dove", required=True, type=Path)
    p.add_argument("--quante", type=int, default=0, help="0 = tutte le righe italiane")
    a = p.parse_args()

    a.dove.mkdir(parents=True, exist_ok=True)
    destinazione = a.dove / NOME

    righe, totale = un_lotto(0, LOTTO)
    limite = totale if a.quante <= 0 else min(a.quante, totale)
    print(f"{totale} righe italiane nel corpus; ne prendo {limite}")

    # L'offset si conta a parte dal numero di righe prese: con un buco in
    # mezzo i due numeri divergono, e riusare `len(righe)` come offset
    # rileggerebbe all'infinito il lotto saltato.
    offset = len(righe)
    buchi: list[int] = []
    while offset < limite:
        quante = min(LOTTO, limite - offset)
        try:
            lotto, _ = un_lotto(offset, quante)
        except RuntimeError as e:
            # Un lotto che non arriva **si dichiara e si salta**, non ferma
            # tutto: dopo sette tentativi in due minuti il problema non e'
            # passeggero, e buttare le righe gia' prese non lo risolve. Il
            # buco finisce nell'impronta, quindi un corpus incompleto non
            # puo' passare per intero.
            print(f"  BUCO a offset {offset}: {e}", file=sys.stderr)
            buchi.append(offset)
            offset += quante
            continue
        if not lotto:
            print(f"  il servizio non da' piu' righe a offset {offset}: mi fermo")
            break
        righe += lotto
        offset += quante
        if len(righe) % 2000 < LOTTO:
            print(f"  {len(righe)}/{limite}")

    righe = righe[:limite]
    with destinazione.open("w", encoding="utf-8") as f:
        for r in righe:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # L'impronta e' sul contenuto: due esecuzioni che danno righe diverse
    # devono dare numeri diversi **e dirlo**, non somigliarsi e basta.
    dati = destinazione.read_bytes()
    nota = f" con {len(buchi)} buchi a {buchi}" if buchi else ""
    (a.dove / "ai4privacy-it.sha256").write_text(
        f"{hashlib.sha256(dati).hexdigest()}  {len(righe)} righe{nota}\n", encoding="utf-8"
    )
    print(f"\n{len(righe)} righe in {destinazione} ({len(dati) / 1e6:.1f} MB)")
    print(f"impronta: {hashlib.sha256(dati).hexdigest()[:16]}")
    if len(righe) < limite:
        print(f"ATTENZIONE: {limite - len(righe)} righe in meno del previsto", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
