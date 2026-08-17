# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Le immagini che il Microsoft Store pretende dentro il pacchetto MSIX.

Stessa convenzione delle altre icone del progetto: **si generano qui, si
versionano, e il build si limita a controllare che ci siano**. Rigenerarle a
ogni build ha gia' prodotto due guai — la build si rompe su una macchina che
non ha gli strumenti di disegno, e su una macchina con librerie diverse il
pacchetto esce con un marchio leggermente diverso da quello nel repository.

La sorgente e' `static/img/logo.png` (512x512), non l'SVG: rasterizzare
richiede svglib/rlPyCairo, che di proposito non stanno in requirements.txt
perche' il prodotto non le usa. Dove esiste gia' un favicon della misura
esatta lo si **copia** invece di ricalcolarlo: e' stato generato dall'SVG
con gli strumenti giusti, quindi e' migliore di qualunque riduzione fatta
qui.

Uso:  python scripts/generate_msix_assets.py [--check]
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SORGENTE = ROOT / "static" / "img" / "logo.png"
FAVICON = ROOT / "static" / "img"
USCITA = ROOT / "packaging" / "Assets"

# nome -> (larghezza, altezza). I nomi non sono liberi: li cerca Windows
# esattamente cosi', e il manifesto li nomina uno per uno.
QUADRATE: dict[str, int] = {
    "StoreLogo.png": 50,
    "StoreLogo.scale-200.png": 100,
    "Square150x150Logo.png": 150,
    "Square150x150Logo.scale-200.png": 300,
    "Square44x44Logo.png": 44,
    "Square44x44Logo.scale-200.png": 88,
    # Le «targetsize» sono quelle che Windows usa nella barra delle
    # applicazioni e in Esplora file. Senza, l'icona viene ridotta al volo
    # e si impasta proprio alle misure piccole, dove si vede di piu'.
    "Square44x44Logo.targetsize-16.png": 16,
    "Square44x44Logo.targetsize-24.png": 24,
    "Square44x44Logo.targetsize-32.png": 32,
    "Square44x44Logo.targetsize-48.png": 48,
    "Square44x44Logo.targetsize-256.png": 256,
}

# Il riquadro largo non e' quadrato: il marchio ci va centrato, non stirato.
LARGHE: dict[str, tuple[int, int]] = {
    "Wide310x150Logo.png": (310, 150),
    "Wide310x150Logo.scale-200.png": (620, 300),
}


def _quadrata(sorgente: Image.Image, lato: int) -> Image.Image:
    """Preferisce un favicon gia' pronto della misura esatta."""
    pronto = FAVICON / f"favicon-{lato}.png"
    if pronto.is_file():
        with Image.open(pronto) as im:
            return im.convert("RGBA").copy()
    return sorgente.resize((lato, lato), Image.LANCZOS)


def _larga(sorgente: Image.Image, larghezza: int, altezza: int) -> Image.Image:
    # Sfondo trasparente e non bianco: il manifesto dichiara
    # BackgroundColor="transparent", quindi dietro ci va il colore di
    # evidenziazione scelto dall'utente. Un fondo bianco qui darebbe un
    # rettangolo bianco su un riquadro colorato.
    tela = Image.new("RGBA", (larghezza, altezza), (0, 0, 0, 0))
    lato = int(altezza * 0.72)  # aria attorno: le linee guida la chiedono
    marchio = sorgente.resize((lato, lato), Image.LANCZOS)
    tela.paste(marchio, ((larghezza - lato) // 2, (altezza - lato) // 2), marchio)
    return tela


def genera(controlla_soltanto: bool = False) -> int:
    if not SORGENTE.is_file():
        print(f"ERRORE: manca la sorgente {SORGENTE}", file=sys.stderr)
        return 1

    USCITA.mkdir(parents=True, exist_ok=True)
    with Image.open(SORGENTE) as im:
        base = im.convert("RGBA")

        mancanti: list[str] = []
        for nome, lato in QUADRATE.items():
            destinazione = USCITA / nome
            if controlla_soltanto:
                if not destinazione.is_file():
                    mancanti.append(nome)
                continue
            _quadrata(base, lato).save(destinazione, "PNG")

        for nome, (w, h) in LARGHE.items():
            destinazione = USCITA / nome
            if controlla_soltanto:
                if not destinazione.is_file():
                    mancanti.append(nome)
                continue
            _larga(base, w, h).save(destinazione, "PNG")

    if controlla_soltanto:
        if mancanti:
            print("ERRORE: immagini MSIX mancanti:", file=sys.stderr)
            for m in mancanti:
                print(f"  {m}", file=sys.stderr)
            print("  rigenerale con: python scripts/generate_msix_assets.py",
                  file=sys.stderr)
            return 1
        print(f"  immagini MSIX: {len(QUADRATE) + len(LARGHE)} presenti")
        return 0

    print(f"  scritte {len(QUADRATE) + len(LARGHE)} immagini in {USCITA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(genera("--check" in sys.argv))
