# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il richiamo sui nomi, misurato su nomi che i nostri elenchi non contengono.

Perche' esiste
--------------

Nessuno dei due corpora che abbiamo puo' misurare i nomi da solo, e per
ragioni opposte.

Il corpus legale italiano ha **il contesto vero** -- prosa amministrativa
con titoli, firme, formule di chiusura -- ma i suoi nomi sono generati da
elenchi italiani, e i nostri riconoscitori usano elenchi italiani. Misurato:
**il 99,98% dei suoi nomi sta gia' nei nostri elenchi** (18 su 78.540 fuori),
e sullo split `train` da 1,4 milioni di righe la proporzione e' la stessa.
Il richiamo che ne esce, 99,4%, misura quanto i due elenchi si sovrappongano.
Non e' un numero sul motore.

Ai4Privacy ha la proprieta' opposta -- il 95,6% dei suoi nomi e' fuori dai
nostri elenchi -- ma le sue frasi sono frammenti sintetici corti, quasi
senza contesto: «Modello di pianificazione settimanale per Christopherus
Kimete». Li' il richiamo crolla al 3%, ed e' il **pavimento**, non la media:
Mr. Rao e' costruito per chiedere una prova che quelle frasi non contengono.

Questo banco incrocia i due. Prende le frasi del corpus legale, con il loro
contesto, e **sostituisce ogni nome con uno che i nostri elenchi non
contengono**. Quello che resta e' la domanda vera: *quando il testo dichiara
che li' c'e' una persona -- un titolo davanti, una firma, un indirizzo di
posta accanto -- il motore la riconosce anche se non l'ha mai vista?*

Cosa NON dimostra
-----------------

Che il motore vada bene sui nomi in generale. Misura **una** cosa: quanto
del riconoscimento venga dal contesto invece che dall'elenco. Un numero
alto qui e basso su Ai4Privacy dice che le regole di contesto funzionano e
che senza contesto non c'e' niente da fare -- che e' esattamente cio' che
il README dichiara, finalmente con una cifra.

La sostituzione e' **deterministica**: lo stesso nome originale riceve
sempre lo stesso sostituto, nello stesso ordine. Un banco che cambia
risposta a ogni esecuzione non serve a decidere se spedire.

Uso
---

    venv\\Scripts\\python scripts\\bench_nomi_ignoti.py \\
        --legale CARTELLA --ai4privacy CARTELLA
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from mr_rao.privacy import (  # noqa: E402
    FIRST_NAMES,
    SURNAMES,
    PrivacyOptions,
    _mask,
    apply_privacy_filter,
)

NOME_LEGALE = "legale-it.jsonl"
NOME_AI4 = "ai4privacy-it.jsonl"
SOGLIA_PERSI = 0.35


def negli_elenchi(valore: str) -> bool:
    """Almeno una parola sta nei nostri elenchi?

    Basta una: e' la condizione che rende possibile la scorciatoia
    dell'elenco. La particella (`De`, `Di`, `D'`) non conta come parola --
    `De Angelis` e' «angelis» piu' una particella, e trattarla come parola
    a se' farebbe passare per ignoto un cognome italianissimo.
    """
    for parola in re.split(r"[^\wÀ-ÿ]+", valore):
        p = parola.casefold()
        if len(p) <= 2:
            continue
        if p in FIRST_NAMES or p in SURNAMES:
            return True
    return False


def nomi_ignoti(cartella: Path) -> list[str]:
    """I nomi di persona di Ai4Privacy che i nostri elenchi non contengono.

    Si tengono solo quelli di **due o tre parole**: l'unita' di Mr. Rao e' la
    persona intera, e un nome di battesimo isolato non viene redatto di
    proposito. Sostituire `Mario Rossi` con `Adyam` misurerebbe quella
    scelta invece delle regole di contesto.
    """
    sorgente = cartella / NOME_AI4
    if not sorgente.is_file():
        raise SystemExit(f"manca {sorgente}: scripts/scarica_corpus_ai4privacy.py")
    visti: dict[str, None] = {}
    with sorgente.open(encoding="utf-8") as f:
        for riga in f:
            for e in json.loads(riga).get("privacy_mask") or []:
                if (e.get("label") or "") not in ("GIVENNAME", "SURNAME"):
                    continue
                v = " ".join((e.get("value") or "").split())
                if not (2 <= len(v.split()) <= 3):
                    continue
                if negli_elenchi(v):
                    continue
                visti.setdefault(v, None)
    # Ordinati: l'insieme dev'essere lo stesso a ogni esecuzione.
    return sorted(visti)


def scegli(originale: str, pool: list[str]) -> str:
    """Sempre lo stesso sostituto per lo stesso originale.

    L'impronta invece di un generatore casuale: non c'e' un seme da
    ricordare, e due esecuzioni a distanza di mesi danno lo stesso banco.
    """
    h = hashlib.sha256(originale.encode("utf-8")).digest()
    return pool[int.from_bytes(h[:8], "big") % len(pool)]


def rimpiazza(riga: dict, pool: list[str]) -> tuple[str, list[str]] | None:
    """Il testo con i nomi sostituiti, e i nomi nuovi da cercare.

    Torna `None` se anche una sola sostituzione non riesce: un documento
    fatto a meta' misurerebbe una frase che non esiste in nessun corpus.
    """
    testo = riga["source_text"]
    attesi: list[str] = []
    for e in riga.get("entities") or []:
        if e.get("label") != "FULLNAME":
            continue
        originale = e.get("value") or ""
        if not originale or originale not in testo:
            return None
        nuovo = scegli(originale, pool)
        testo = testo.replace(originale, nuovo)
        attesi.append(nuovo)
    return (testo, attesi) if attesi else None


def misura(legale: Path, pool: list[str]) -> dict:
    sorgente = legale / NOME_LEGALE
    if not sorgente.is_file():
        raise SystemExit(f"manca {sorgente}: scripts/scarica_corpus_legale_it.py")

    opzioni = PrivacyOptions()
    esiti: collections.Counter = collections.Counter()
    esempi: list[str] = []
    saltati = 0

    with sorgente.open(encoding="utf-8") as f:
        for riga in f:
            d = json.loads(riga)
            esito = rimpiazza(d, pool)
            if esito is None:
                saltati += 1
                continue
            testo, attesi = esito
            fuori, rapporto = apply_privacy_filter(testo, opzioni)
            sospetti = {s.get("sample") for s in rapporto.to_dict()["suspects"]}
            for nome in attesi:
                if nome not in fuori:
                    esiti["redatto"] += 1
                elif _mask(nome) in sospetti:
                    esiti["segnalato"] += 1
                else:
                    esiti["perso"] += 1
                    if len(esempi) < 10:
                        esempi.append(nome)

    return {
        "redatto": esiti["redatto"],
        "segnalato": esiti["segnalato"],
        "perso": esiti["perso"],
        "documenti_saltati": saltati,
        "esempi_persi": esempi,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--legale", type=Path, required=True)
    p.add_argument("--ai4privacy", type=Path, required=True)
    args = p.parse_args()

    pool = nomi_ignoti(args.ai4privacy)
    print(f"nomi fuori dai nostri elenchi disponibili: {len(pool)}")
    if len(pool) < 100:
        print("ERRORE: troppo pochi per un banco: un pool piccolo fa ripetere "
              "gli stessi nomi e misura quelli, non la regola.", file=sys.stderr)
        return 1
    print(f"  esempi: {pool[:5]}\n")

    r = misura(args.legale, pool)
    totale = r["redatto"] + r["segnalato"] + r["perso"]
    if not totale:
        print("ERRORE: nessun nome misurato.", file=sys.stderr)
        return 1

    print(f"{'redatti':>9}{'segnal.':>9}{'PERSI':>8}{'richiamo':>10}")
    print(f"{r['redatto']:>9}{r['segnalato']:>9}{r['perso']:>8}"
          f"{100 * r['redatto'] / totale:>9.1f}%   (su {totale})")
    print(f"\ndocumenti saltati (nome non ritrovato nel testo): "
          f"{r['documenti_saltati']}")
    if r["esempi_persi"]:
        print(f"persi in silenzio: {r['esempi_persi']}")

    quota_persi = r["perso"] / totale
    print(f"\npersi in silenzio: {100 * quota_persi:.1f}%  (soglia "
          f"{100 * SOGLIA_PERSI:.0f}%)")
    if quota_persi > SOGLIA_PERSI:
        print("SOPRA LA SOGLIA: il contesto non basta piu' a riconoscere una "
              "persona che non e' negli elenchi.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
