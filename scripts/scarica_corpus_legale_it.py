"""Scarica un corpus italiano etichettato di testi amministrativi e legali.

A cosa serve, e perche' non basta quello che avevamo
-----------------------------------------------------

Tutti i banchi di questo progetto misurano bene i **falsi positivi**: quante
volte il motore sbaglia su documenti che non contengono niente. Per il
**richiamo** -- quanto ci sfugge -- l'unico materiale etichettato che
avevamo era `ai4privacy`, e sui dati con un conto dietro non si puo' usare:

* delle 51 carte di credito nelle righe italiane, **3** passano Luhn;
* di IBAN non ce n'e' **nessuno**: l'etichetta non esiste proprio;
* i telefoni hanno quasi tutti prefissi internazionali inesistenti
  (`+871`, `+75`, `+83`).

Un richiamo misurato li' darebbe numeri bassissimi e falsi: il motore
rifiuta quei valori **giustamente**, perche' l'aritmetica non torna.

Questo corpus e' diverso, ed e' il motivo per cui vale la pena averne due:
i valori sono generati con i conti giusti (Luhn, mod-97, carattere di
controllo), i testi sono italiani amministrativi e legali, e ogni entita'
porta `start`, `end` e un campo `checksum_ok` gia' calcolato.

`checksum_ok` non si crede sulla parola
----------------------------------------

E' comodo e non e' una prova: e' un campo scritto da chi ha generato i
dati. Il banco ricalcola i conti per conto suo -- Luhn, mod-97, carattere
di controllo del codice fiscale -- e usa `checksum_ok` solo per confronto.
Fidarsi di un'etichetta altrui per decidere cosa il nostro motore *avrebbe
dovuto* trovare renderebbe la misura una catena di due opinioni.

Perche' lo split `validation` e non `train`
--------------------------------------------

`train` ha 1,4 milioni di righe per 1,8 GB: scaricarlo per farci un banco
sarebbe come tenere una biblioteca per leggere un capitolo. `validation` ne
ha 29 297 in 29 MB, ed e' lo split fatto apposta per valutare -- cioe'
esattamente cio' che stiamo facendo.

Licenza
-------

MIT. Niente catene ereditate, a differenza di `ai4privacy` (che porta con
se' anche la licenza del modello con cui e' stato generato). Qui non si
ridistribuisce comunque niente: le righe restano sul disco di chi esegue lo
script, e l'attribuzione va in `NOTICE.md`.

Cosa NON puo' misurare
----------------------

E' **sintetico**: i testi nascono da modelli riempiti con valori generati.
Va benissimo per i dati che hanno una forma e un conto -- e' il loro punto
di forza -- e non prova niente sulla prosa vera, dove il nostro problema
sono i nomi in contesti insoliti. Per quella la fonte resta la Gazzetta
Ufficiale.

Uso
---

    venv\\Scripts\\python scripts\\scarica_corpus_legale_it.py --in CARTELLA
    venv\\Scripts\\python scripts\\scarica_corpus_legale_it.py --in CARTELLA --quante 5000
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

DATASET = "rizzoaiacademy/anonimizzazione-testi-italiano-clean"
SPLIT = "validation"
BASE = "https://datasets-server.huggingface.co/rows"
LOTTO = 100  # il massimo che il servizio restituisce per richiesta
NOME = "legale-it.jsonl"

# Attese crescenti: il servizio sbaglia **a intermittenza** -- lo stesso
# offset risponde 500 e poi 200 senza che sia cambiato niente. Con pochi
# tentativi ravvicinati un lotto su cento fallisce, e su trecento richieste
# vuol dire che lo scaricamento non arriva quasi mai in fondo.
ATTESE = (2, 5, 12, 30, 60, 120)

# I campi che servono al banco. Il resto -- `tokens`, `bio_labels` -- e' per
# addestrare un modello, pesa quasi quanto tutto il file e non lo usiamo:
# tenerlo vorrebbe dire un corpus quattro volte piu' grande per niente.
CAMPI = ("source_text", "entities", "template_id")


def indirizzo(offset: int, quante: int) -> str:
    q = urllib.parse.urlencode(
        {
            "dataset": DATASET,
            "config": "default",
            "split": SPLIT,
            "offset": offset,
            "length": quante,
        }
    )
    return f"{BASE}?{q}"


def un_lotto(offset: int, quante: int) -> tuple[list[dict], int]:
    """Un lotto di righe. Solleva se non ce la fa: un lotto perso in
    silenzio darebbe un corpus piu' piccolo del previsto, e un banco che
    misura su meno righe di quante crede da' numeri piu' bassi senza che
    nessuno sappia perche'."""
    ultimo: Exception | None = None
    for attesa in (*ATTESE, None):
        try:
            with urllib.request.urlopen(indirizzo(offset, quante), timeout=90) as r:
                d = json.load(r)
            righe = [{k: x["row"][k] for k in CAMPI} for x in d["rows"]]
            return righe, int(d.get("num_rows_total", 0))
        except (urllib.error.URLError, OSError, TimeoutError, ValueError, KeyError) as e:
            ultimo = e
            if attesa is None:
                break
            time.sleep(attesa)
    raise RuntimeError(f"lotto a offset {offset} non recuperato: {ultimo}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--in", dest="dove", required=True, type=Path)
    p.add_argument("--quante", type=int, default=0, help="0 = tutto lo split")
    a = p.parse_args()

    a.dove.mkdir(parents=True, exist_ok=True)
    destinazione = a.dove / NOME

    righe, totale = un_lotto(0, LOTTO)
    limite = totale if a.quante <= 0 else min(a.quante, totale)
    print(f"{totale} righe nello split «{SPLIT}»; ne prendo {limite}")

    offset = len(righe)
    buchi: list[int] = []
    while offset < limite:
        quante = min(LOTTO, limite - offset)
        try:
            lotto, _ = un_lotto(offset, quante)
        except RuntimeError as e:
            # Un lotto che non arriva **si dichiara e si salta**: dopo sette
            # tentativi in due minuti il problema non e' passeggero, e
            # buttare le righe gia' prese non lo risolve. Il buco finisce
            # nell'impronta, quindi un corpus incompleto non puo' passare
            # per intero.
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

    dati = destinazione.read_bytes()
    nota = f" con {len(buchi)} buchi a {buchi}" if buchi else ""
    (a.dove / "legale-it.sha256").write_text(
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
