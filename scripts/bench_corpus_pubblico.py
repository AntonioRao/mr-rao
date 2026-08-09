"""Il banco che si accorge quando il motore prende **di meno**.

Perche' esiste
--------------

Tutti i banchi di questo progetto misurano una cosa sola: quante volte il
motore sbaglia su documenti che non contengono niente. E' la meta' giusta da
misurare per prima -- un motore che sovra-redige e' inutilizzabile -- ma e'
una meta'.

Nessuno si accorgerebbe del contrario. Se domani una modifica facesse
smettere il riconoscitore di indirizzi di vedere «piazza G. Verdi, 1», i
banchi a verita' zero resterebbero tutti verdi: zero errori su documenti
vuoti e' esattamente cio' che fa anche un motore spento. La perdita di
richiamo e' invisibile per costruzione.

Questo banco guarda l'altra meta', e lo fa sui documenti **che non abbiamo
scritto noi**. E' la lezione piu' cara di questo progetto, pagata due volte:
un corpus scritto in casa contiene solo le trappole a cui ha pensato chi
l'ha scritto. I 41 indirizzi che la 1.16.0 ha tirato fuori dalle Gazzette
Ufficiali, e i 107 cognomi che la 1.17.0 ha tirato fuori dalle stesse, non
li avrebbe trovati nessun banco fatto in casa.

Due gruppi, due domande opposte
-------------------------------

* `itmod--*` e `irs--*` sono **moduli in bianco**: non contengono un solo
  dato personale, quindi ogni sostituzione e' un errore. Atteso: **zero**,
  e deve restare zero;
* `gu--*` e' **prosa giuridica vera**, con dentro indirizzi di ministeri e
  cognomi di ministri. Li' le sostituzioni sono giuste, e il numero non
  deve **scendere**.

Il primo controllo puo' fallire allentando troppo, il secondo stringendo
troppo. Un banco che potesse fallire in una sola direzione sarebbe un banco
che approva meta' degli errori.

Il corpus non sta nel repository
--------------------------------

Sono decine di megabyte scaricati dagli enti che li pubblicano, e non sono
nostri da ridistribuire. Il percorso si passa con `--corpus` oppure con la
variabile d'ambiente `MRRAO_CORPUS`; senza, il banco lo dice e si ferma
invece di misurare niente e sembrare verde.

L'atteso congelato porta anche **l'impronta dell'elenco dei file**: puntare
il banco a un corpus diverso darebbe numeri diversi per il motivo sbagliato,
e questo lo distingue da una regressione vera.

Uso
---

    venv\\Scripts\\python scripts\\bench_corpus_pubblico.py --corpus CARTELLA
    venv\\Scripts\\python scripts\\bench_corpus_pubblico.py --corpus CARTELLA --rigenera
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter  # noqa: E402

ATTESO = RADICE / "tests" / "dati" / "corpus_pubblico_atteso.json"

# I gruppi in cui ogni sostituzione e' un errore.
VERITA_ZERO = ("itmod", "irs")


def corpo(t: str) -> str:
    """Via il frontmatter YAML.

    Un corpus fatto di conversioni gia' fatte porta dentro la firma di
    Mr. Rao, e «generator: Mr. Rao 1.x» contiene un titolo professionale
    seguito da una parola maiuscola: il motore la riconosce, giustamente, e
    chi conta si ritrova un errore per documento che non c'entra niente.
    """
    if t.startswith("---"):
        fine = t.find("\n---", 3)
        if fine != -1:
            return t[fine + 4:]
    return t


def trova_corpus(indicato: Path | None) -> Path | None:
    if indicato:
        return indicato if indicato.is_dir() else None
    da_ambiente = os.environ.get("MRRAO_CORPUS")
    if da_ambiente and Path(da_ambiente).is_dir():
        return Path(da_ambiente)
    return None


def impronta(file: list[Path]) -> str:
    """Quali documenti, non quanti: due corpora della stessa taglia danno
    numeri diversi, e senza questo sembrerebbe una regressione."""
    h = hashlib.sha256()
    for f in sorted(file):
        h.update(f.name.encode("utf-8"))
    return h.hexdigest()[:16]


def misura(cartella: Path) -> dict:
    file = sorted(cartella.glob("*.txt"))
    conteggi: dict[str, dict[str, int]] = {}
    opzioni = PrivacyOptions()
    for f in file:
        gruppo = f.name.split("--")[0]
        _, rep = apply_privacy_filter(
            corpo(f.read_text(encoding="utf-8", errors="replace")), opzioni)
        per_gruppo = conteggi.setdefault(gruppo, {})
        for categoria, n in rep.counts.items():
            per_gruppo[categoria] = per_gruppo.get(categoria, 0) + n
    return {
        "impronta": impronta(file),
        "documenti": len(file),
        "conteggi": {g: dict(sorted(c.items())) for g, c in sorted(conteggi.items())},
    }


def confronta(atteso: dict, ora: dict) -> list[str]:
    """Restituisce i guasti. Vuoto = tutto a posto."""
    guasti: list[str] = []
    if atteso["impronta"] != ora["impronta"]:
        return [f"corpus diverso da quello congelato "
                f"({ora['documenti']} documenti, impronta {ora['impronta']}, "
                f"attesa {atteso['impronta']}): i numeri non sono confrontabili"]

    for gruppo in VERITA_ZERO:
        n = sum(ora["conteggi"].get(gruppo, {}).values())
        if n:
            guasti.append(
                f"{gruppo}: {n} sostituzioni su moduli in bianco, atteso zero — "
                f"{ora['conteggi'][gruppo]}")

    for gruppo, categorie in atteso["conteggi"].items():
        if gruppo in VERITA_ZERO:
            continue
        adesso = ora["conteggi"].get(gruppo, {})
        for categoria, quante in categorie.items():
            ha = adesso.get(categoria, 0)
            if ha < quante:
                guasti.append(
                    f"{gruppo}/{categoria}: da {quante} a {ha} — il motore "
                    f"prende MENO di prima su documenti veri")
    return guasti


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", type=Path, default=None)
    p.add_argument("--rigenera", action="store_true",
                   help="congela i numeri attuali come nuovo atteso")
    args = p.parse_args()

    cartella = trova_corpus(args.corpus)
    if cartella is None:
        print("Nessun corpus: --corpus CARTELLA oppure MRRAO_CORPUS.")
        print("I documenti non stanno nel repository (vedi il docstring).")
        return 2

    ora = misura(cartella)
    print(f"{ora['documenti']} documenti, impronta {ora['impronta']}")
    for gruppo, categorie in ora["conteggi"].items():
        marchio = "  (atteso zero)" if gruppo in VERITA_ZERO else ""
        print(f"  {gruppo:<8} {sum(categorie.values()):>5}{marchio}   {categorie}")
    for gruppo in VERITA_ZERO:
        if gruppo not in ora["conteggi"]:
            print(f"  {gruppo:<8} {0:>5}  (atteso zero)")

    if args.rigenera:
        ATTESO.write_text(json.dumps(ora, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        print(f"\nAtteso riscritto: {ATTESO}")
        print("Guarda il diff prima di committarlo: se contiene un numero che")
        print("SCENDE e non te lo aspettavi, e' li' che si scopre.")
        return 0

    if not ATTESO.exists():
        print("\nNessun atteso congelato: --rigenera per crearlo.")
        return 2

    guasti = confronta(json.loads(ATTESO.read_text(encoding="utf-8")), ora)
    if guasti:
        print("\nGUASTI:")
        for g in guasti:
            print(f"  {g}")
        return 1
    print("\nOK: nessuna sostituzione sui moduli in bianco, e su prosa vera")
    print("il motore non prende meno di prima.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
