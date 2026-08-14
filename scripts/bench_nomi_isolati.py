"""Quanto costa trattare un nome di battesimo **da solo**.

## Perché esiste

Oggi un nome isolato non viene sostituito: diventa un sospetto. La ragione
è che «Rosa», «Vera», «Costa» sono nomi *e* parole italiane. Ma quella
ragione non vale per «Walter», «Nazzareno», «Ludovica», che parole non
sono — ed è la proposta P9.2 del backlog.

**La proposta non si valuta leggendo il codice.** Il motore ha già ritirato
un'euristica sui nomi per un numero misurato — 8 904 sostituzioni sbagliate
su venti moduli in bianco — e questa va pesata con lo stesso metro. Il
banco tiene due popolazioni opposte:

* **persona** — un nome di battesimo che identifica qualcuno. Non prenderlo
  è il difetto che la proposta vuole chiudere;
* **non-persona** — lo stesso genere di parola dentro un odonimo («via
  Vittorio Emanuele»), un'intitolazione («ospedale Umberto I», «premio Italo
  Calvino») o un toponimo con il santo («San Giovanni Rotondo»). Prenderlo
  rovina un documento vero.

Gli stessi nomi compaiono di qua e di là apposta: Vittorio, Umberto,
Leonardo, Marco, Giuseppe. Se un motore li distingue non è perché conosce
la parola, è perché guarda cosa ci sta intorno — che è l'unica strada
onesta.

## Come si legge l'uscita

    presi        quante «persona» vengono sostituite   (più è alto, meglio è)
    falsi        quante «non-persona» vengono sostituite  (deve restare 0)

Uso:

    venv\\Scripts\\python scripts\\bench_nomi_isolati.py
    venv\\Scripts\\python scripts\\bench_nomi_isolati.py --dettaglio
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter  # noqa: E402

CASI = RADICE / "tests" / "dati" / "nomi_isolati.jsonl"


def carica() -> list[dict]:
    with CASI.open(encoding="utf-8") as f:
        return [json.loads(riga) for riga in f if riga.strip()]


def sparito(caso: dict, prosa: bool, **opzioni) -> bool:
    """Il bersaglio è stato tolto **come nome di persona**?

    Due precisazioni, e tutte e due sono state pagate scrivendo il banco.

    Si guarda **il bersaglio** e non il numero di sostituzioni: un caso può
    contenere altri dati — una data, un numero civico — e contarli
    renderebbe il banco verde per il motivo sbagliato.

    E si pretende un segnaposto di **nome**. La prima stesura si accontentava
    che il bersaglio sparisse, e contava 18 falsi positivi su un motore che
    non aveva ancora la funzione in prova: quelle righe erano indirizzi, e
    «via Vittorio Emanuele 24» diventa `{{ADDRESS_1}}` — il nome sparisce
    perché è dentro l'indirizzo, che è il comportamento giusto. Un banco che
    non distingue le due cose misura la grandezza sbagliata.
    """
    fuori, _ = apply_privacy_filter(
        caso["testo"], PrivacyOptions(prosa=prosa, **opzioni)
    )
    return caso["bersaglio"] not in fuori and "{{NAME" in fuori


def misura(prosa: bool, **opzioni) -> tuple[list[dict], list[dict]]:
    casi = carica()
    persone = [c for c in casi if c["atteso"] == "persona"]
    altro = [c for c in casi if c["atteso"] == "non-persona"]
    return (
        [c for c in persone if sparito(c, prosa, **opzioni)],
        [c for c in altro if sparito(c, prosa, **opzioni)],
    )


def confronta(prosa: bool, dettaglio: bool) -> int:
    """Il numero che conta è il **delta**, non il valore assoluto.

    Parte di questi casi il motore li tratta già oggi, perché contengono due
    parole maiuscole adiacenti («Giuseppe Meazza», «Italo Calvino») e la
    regola delle coppie non sa che quello è uno stadio. È un difetto suo,
    più vecchio di questa funzione, e va misurato a parte: quello che si
    chiede qui è **quanto cambia accendendo `names_alone`**.
    """
    prima_presi, prima_falsi = misura(prosa)
    dopo_presi, dopo_falsi = misura(prosa, names_alone=True)
    nuovi_presi = [c for c in dopo_presi if c not in prima_presi]
    nuovi_falsi = [c for c in dopo_falsi if c not in prima_falsi]
    modo = "prosa" if prosa else "modulo"
    print(
        f"  {modo:7} presi {len(prima_presi):2} -> {len(dopo_presi):2}"
        f"  (+{len(nuovi_presi)})"
        f"   falsi {len(prima_falsi):2} -> {len(dopo_falsi):2}"
        f"  (+{len(nuovi_falsi)})"
    )
    if dettaglio:
        for c in nuovi_presi:
            print(f"      preso  {c['id']}  {c['testo']}")
        for c in nuovi_falsi:
            print(f"      FALSO  {c['id']}  {c['testo']}")
        rimasti = [c for c in carica()
                   if c["atteso"] == "persona" and c not in dopo_presi]
        for c in rimasti:
            print(f"      perso  {c['id']}  {c['testo']}")
    return len(nuovi_falsi)


def main() -> int:
    dettaglio = "--dettaglio" in sys.argv
    print("nomi di battesimo isolati: senza -> con `names_alone`")
    peggio = 0
    for prosa in (True, False):
        peggio = max(peggio, confronta(prosa, dettaglio))
    # Il banco non decide se la funzione va accesa di serie — quello lo
    # dicono i due numeri messi accanto. Fallisce se la funzione **aggiunge**
    # falsi positivi, perché quelli non si negoziano.
    if peggio:
        print(f"\nFALSI POSITIVI NUOVI: {peggio}. Un documento vero verrebbe rovinato.")
        return 1
    print("\nnessun falso positivo nuovo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
