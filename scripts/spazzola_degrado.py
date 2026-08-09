"""Dove crolla la copertura, e dove cade una scansione vera rispetto al crollo.

Il problema che risolve
-----------------------

`bench_scansioni.py` misura la copertura su **tre punti fissi** — ufficio,
fotocopia, illeggibile. Tre punti dicono poco: non si sa se fra il primo e il
secondo la copertura scenda piano o cada da un dirupo, ne' dove sia il bordo.

E i tre punti sono tarati su numeri scelti a mano. `misura_degrado_reale.py`
ha misurato su scansioni **vere** che quei numeri sono lontani dal vero in
due direzioni opposte: il rumore simulato e' circa dieci volte troppo, il
contrasto e' troppo alto (una scansione vera e' piu' spenta della nostra
«fotocopia»).

Questo script spazzola **un parametro alla volta** e, per ogni gradino,
misura la pagina generata **con lo stesso strumento** usato sulle scansioni
vere. Cosi' i due assi diventano confrontabili per costruzione, invece che
per assunzione: si puo' dire «il dirupo e' qui, e una scansione vera cade
la'» senza scambiare due grandezze che si chiamano allo stesso modo.

Perche' misurare invece di fidarsi del parametro
------------------------------------------------

Il `contrasto` del profilo e' un moltiplicatore applicato a una pagina che
parte da carta 255 e inchiostro 0. Il contrasto che si misura su una
scansione vera e' la distanza fra due percentili di un'immagine che parte
da carta 184 e inchiostro 99. **Non sono la stessa grandezza**, e trattarle
come tali sarebbe l'errore piu' facile da fare qui dentro. L'unico modo
onesto e' passare entrambe dallo stesso strumento.

Uso:
    venv\\Scripts\\python scripts\\spazzola_degrado.py --parametro contrasto
    venv\\Scripts\\python scripts\\spazzola_degrado.py --parametro rumore --documenti 3
"""
from __future__ import annotations

import argparse
import shutil
import statistics
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image

RADICE = Path(__file__).resolve().parent
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from bench_scansioni import (  # noqa: E402
    UFFICIO,
    Profilo,
    costruisci_documenti,
    esegui,
    trova_font,
    verifica_generatori,
)
from misura_degrado_reale import misura  # noqa: E402

# I gradini di ciascun parametro. Scelti per **attraversare** il valore
# misurato sulle scansioni vere, non per circondare quello che usiamo oggi:
# lo scopo e' vedere da che parte del dirupo cade la realta'.
GRADINI = {
    "contrasto": [1.0, 0.85, 0.70, 0.55, 0.45, 0.35, 0.28, 0.22, 0.16],
    "rumore": [0.0, 1.5, 4.0, 8.0, 14.0, 22.0, 32.0, 45.0],
    "sfocatura": [0.0, 0.4, 0.8, 1.3, 1.8, 2.4, 3.2, 4.0],
}

# Cosa dicono le scansioni vere, da misura_degrado_reale.py su carta grezza.
# Campione piccolo (quattro pagine, una sola fonte): serve a collocare la
# realta' sull'asse, non a fissare una costante.
REALE = {"contrasto": 0.337, "rumore": 1.40, "sfocatura": 0.89}
REALE_NOTA = "4 pagine, una sola fonte: colloca, non taratura"

DPI_SPAZZOLAMENTO = 200


def profilo_variato(base: Profilo, parametro: str, valore: float) -> Profilo:
    """Una copia del profilo con un solo parametro cambiato.

    Il **nome dev'essere unico**: `esegui` mette in cache il foglio stampato
    per nome del profilo, e due varianti che si chiamassero uguale si
    scambierebbero il foglio. Su un parametro di stampa il banco misurerebbe
    la variante sbagliata senza dirlo.
    """
    nome = f"{parametro}={valore:g}"
    return replace(base, nome=nome, **{parametro: valore})


def misura_livello(cartella: Path, nome_livello: str) -> dict[str, float]:
    """Le grandezze misurate sulle pagine generate per un gradino."""
    pagine = sorted(cartella.glob(f"*_{nome_livello}.jpg"))
    if not pagine:
        return {}
    ms = [misura(Image.open(p)) for p in pagine]
    return {
        "contrasto": statistics.median(m.contrasto for m in ms),
        "rumore": statistics.median(m.rumore for m in ms),
        "acutanza": statistics.median(m.acutanza for m in ms),
        "carta": statistics.median(m.livello_carta for m in ms),
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--parametro", choices=sorted(GRADINI), default="contrasto",
        help="quale manopola girare",
    )
    ap.add_argument("--documenti", type=int, default=3)
    ap.add_argument("--dpi", type=int, default=DPI_SPAZZOLAMENTO)
    args = ap.parse_args(argv)

    # `verifica_generatori` restituisce TUTTE le righe, quelle superate col
    # prefisso «OK » e quelle fallite con «NO ». Trattare la lista non vuota
    # come un guasto — come faceva la prima stesura di questo script — vuol
    # dire fermarsi sempre, anche quando va tutto bene.
    esiti = verifica_generatori()
    guasti = [e for e in esiti if e.startswith("NO ")]
    if guasti:
        print("i generatori di cifre di controllo non passano i vettori:", file=sys.stderr)
        for g in guasti:
            print("  " + g, file=sys.stderr)
        print(
            "  Il banco si ferma qui: campioni non validi misurerebbero un'altra cosa.",
            file=sys.stderr,
        )
        return 1

    documenti = costruisci_documenti(max(1, args.documenti))
    con_dati = [d for d in documenti if not d.controllo]
    attesi = sum(len(d.attesi) for d in con_dati)

    valori = GRADINI[args.parametro]
    livelli = []
    for v in valori:
        p = profilo_variato(UFFICIO, args.parametro, v)
        livelli.append((p.nome, p, args.dpi))

    print(f"  spazzolamento di «{args.parametro}» a {args.dpi} DPI")
    print(f"  {len(con_dati)} documenti con dati ({attesi} dati attesi per gradino), "
          f"{sum(1 for d in documenti if d.controllo)} di controllo a verita' zero")
    print(f"  gradini: {', '.join(f'{v:g}' for v in valori)}\n")

    cartella = Path(tempfile.mkdtemp(prefix="spazzola_"))
    try:
        righe = esegui(documenti, livelli, trova_font(), cartella)

        intestazione = (
            f"  {args.parametro:>10s} | {'misurato':>9s} | {'rumore mis.':>11s} | "
            f"{'redatte':>8s} | {'perse':>6s} | {'non lette':>9s} | {'falsi pos.':>10s}"
        )
        print(intestazione)
        print("  " + "-" * (len(intestazione) - 2))

        for (nome, profilo, _), riga in zip(livelli, righe):
            m = misura_livello(cartella, nome)
            red = riga.esiti.get("redatta", 0)
            perse = riga.esiti.get("persa", 0)
            nl = riga.esiti.get("non letta", 0)
            tot = max(1, riga.totale)
            mis_par = m.get(args.parametro if args.parametro != "sfocatura" else "acutanza")
            mis_txt = f"{mis_par:.3f}" if mis_par is not None else "  -  "
            print(
                f"  {getattr(profilo, args.parametro):10g} | {mis_txt:>9s} | "
                f"{m.get('rumore', float('nan')):11.2f} | "
                f"{red:4d} {100*red/tot:3.0f}% | {perse:6d} | {nl:9d} | "
                f"{riga.falsi_positivi:10d}"
            )
    finally:
        shutil.rmtree(cartella, ignore_errors=True)

    reale = REALE.get(args.parametro)
    print(
        f"\n  Dove cade una scansione vera su questo asse: "
        f"{args.parametro} misurato ~ {reale:.3f}"
        if reale is not None else ""
    )
    print(f"  ({REALE_NOTA})")
    print(
        "\n  Come si legge: la colonna «misurato» e la riga qui sopra escono\n"
        "  dallo STESSO strumento (misura_degrado_reale.misura), quindi si\n"
        "  possono confrontare. La colonna del parametro no: e' la manopola\n"
        "  del banco, e non ha le stesse unita' di niente."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
