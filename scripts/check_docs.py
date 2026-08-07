"""Controlla che i documenti pubblicati dicano ancora la verita'.

Nasce da un errore preciso, che vale la pena tenere scritto qui. Mi era
stato chiesto di verificare che tutta la documentazione fosse aggiornata,
avevo risposto di si', e non era vero: `docs/BACKLOG.md` portava in cima
«Ultimo aggiornamento: UI Design System 2.0», fermo a quindici release
prima, e i due README dichiaravano un quality gate da «161 test» quando i
test erano piu' del doppio.

Il motivo per cui erano sfuggiti non e' distrazione, ed e' il punto:
**avevo controllato i documenti che stavo modificando**, non tutti quelli
che esistono. Un controllo che parte dall'elenco delle cose che ho in mano
trova solo quello che ho gia' guardato. Questo parte da `git ls-files`,
che non sa cosa ho toccato oggi.

Quattro invarianti, tutte verificabili senza leggere il testo:

1. nessun identificativo duplicato nel backlog — «P2.7» ha significato due
   cose per qualche ora, in due stati diversi;
2. i link relativi puntano a file che esistono;
3. le versioni citate come corrente coincidono con APP_VERSION;
4. i conteggi di test dichiarati coincidono con quelli veri.

Il changelog e' escluso da (3) e (4) apposta: e' una cronologia, e ogni
voce cita giustamente i numeri del suo momento.

Uso:  python scripts/check_docs.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import APP_VERSION  # noqa: E402

# La cronologia cita i numeri di quando e' stata scritta: e' il suo mestiere.
CRONOLOGIE = {"docs/CHANGELOG.md"}

_RE_ID = re.compile(r"^\| ([PSA]\d*\.\d+[a-z]?) \|", re.MULTILINE)
_RE_VERSIONE = re.compile(r"(?:versione|version)[-\s:]+(\d+\.\d+\.\d+)", re.I)
_RE_CONTEGGIO = re.compile(r"(\d{3})(?:%20)?[\s-]*(?:test|tests|passing|passati)", re.I)
_RE_LINK = re.compile(r"\]\(([^)#:]+\.(?:md|py|txt|ico|png|yml|bat|ps1))[^)]*\)")


def documenti() -> list[Path]:
    """Tutti i .md tracciati da git, non quelli che mi ricordo di avere."""
    uscita = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    return [ROOT / p for p in uscita]


def _relativo(f: Path) -> str:
    return f.relative_to(ROOT).as_posix()


def id_duplicati() -> list[str]:
    """Un elenco in cui non si puo' citare un identificativo non serve."""
    problemi = []
    for f in documenti():
        ids = _RE_ID.findall(f.read_text(encoding="utf-8"))
        visti: dict[str, int] = {}
        for i in ids:
            visti[i] = visti.get(i, 0) + 1
        for i, n in sorted(visti.items()):
            if n > 1:
                problemi.append(f"{_relativo(f)}: '{i}' compare {n} volte")
    return problemi


def link_rotti() -> list[str]:
    problemi = []
    for f in documenti():
        for m in _RE_LINK.finditer(f.read_text(encoding="utf-8")):
            if not (f.parent / m.group(1)).resolve().exists():
                problemi.append(f"{_relativo(f)}: link a '{m.group(1)}' che non esiste")
    return problemi


def versioni_incoerenti() -> list[str]:
    problemi = []
    for f in documenti():
        if _relativo(f) in CRONOLOGIE:
            continue
        for m in _RE_VERSIONE.finditer(f.read_text(encoding="utf-8")):
            if m.group(1) != APP_VERSION:
                problemi.append(
                    f"{_relativo(f)}: dice versione {m.group(1)}, ma e' la {APP_VERSION}"
                )
    return problemi


def conteggi_incoerenti(reale: int) -> list[str]:
    problemi = []
    for f in documenti():
        if _relativo(f) in CRONOLOGIE:
            continue
        for m in _RE_CONTEGGIO.finditer(f.read_text(encoding="utf-8")):
            if m.group(1) != str(reale):
                problemi.append(
                    f"{_relativo(f)}: dice {m.group(1)} test, ma sono {reale}"
                )
    return problemi


def test_raccolti() -> int:
    """Quanti test esistono davvero, chiesto a pytest invece che contati a mano."""
    py = ROOT / "venv" / "Scripts" / "python.exe"
    eseguibile = str(py) if py.is_file() else sys.executable
    uscita = subprocess.run(
        [eseguibile, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip().splitlines()
    for riga in reversed(uscita):
        m = re.match(r"(\d+) tests? collected", riga.strip())
        if m:
            return int(m.group(1))
    raise RuntimeError("non riesco a contare i test: " + "\n".join(uscita[-3:]))


def main() -> int:
    reale = test_raccolti()
    problemi = (
        id_duplicati()
        + link_rotti()
        + versioni_incoerenti()
        + conteggi_incoerenti(reale)
    )
    if problemi:
        print(f"DOCUMENTI DISALLINEATI ({len(problemi)}):", file=sys.stderr)
        for p in problemi:
            print(f"  {p}", file=sys.stderr)
        print(
            "\nSono affermazioni che chi legge il repository puo' verificare in "
            "trenta secondi. Se non tornano, non torna nemmeno il resto.",
            file=sys.stderr,
        )
        return 1
    print(f"  documenti allineati: {len(documenti())} file, {reale} test, v{APP_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
