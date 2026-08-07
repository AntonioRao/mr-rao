"""Rigenera l'atteso del test golden sul motore di anonimizzazione.

Il test `tests/test_golden_privacy.py` confronta l'uscita del motore su un
corpus che esercita **tutti** i riconoscitori insieme con un risultato
congelato. Serve a una cosa sola: accorgersi che qualcosa e' cambiato quando
non doveva.

E' la rete della fase 1 di #1 -- separare il nucleo universale dai
riconoscitori nazionali senza toccare il comportamento. Un test che dice
«29 sostituzioni» non basta: si puo' arrivare a 29 sostituendo cose diverse.
Qui si confronta il testo prodotto **carattere per carattere**.

Quando il comportamento cambia **di proposito**, si rigenera:

    venv\\Scripts\\python scripts\\rigenera_golden.py

e si guarda il diff del .json prima di committarlo. Se il diff contiene
qualcosa che non si era voluto cambiare, e' li' che si scopre.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter  # noqa: E402

CORPUS = RADICE / "tests" / "dati" / "corpus_privacy.txt"
ATTESO = RADICE / "tests" / "dati" / "golden_privacy.json"


def calcola() -> dict:
    testo = CORPUS.read_text(encoding="utf-8")
    # Tutto acceso, comprese date e importi che di serie sono spenti: il
    # golden deve coprire anche i riconoscitori che di norma non girano.
    out, rep = apply_privacy_filter(testo, PrivacyOptions(dates=True, amounts=True))
    return {
        "uscita": out,
        "totale": rep.total,
        "conteggi": dict(sorted(rep.counts.items())),
        "sospetti": [dict(sorted(s.items())) for s in rep.suspects],
    }


def main() -> int:
    if not CORPUS.is_file():
        print(f"ERRORE: manca il corpus {CORPUS}", file=sys.stderr)
        return 1
    dati = calcola()
    ATTESO.write_text(
        json.dumps(dati, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"  scritto {ATTESO.relative_to(RADICE)}")
    print(f"  {dati['totale']} sostituzioni, {len(dati['conteggi'])} categorie, "
          f"{len(dati['sospetti'])} sospetti")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
