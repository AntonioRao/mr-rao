# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Genera tutte le icone di Mr. Rao a partire dai due SVG sorgente.

    static/img/logo.svg      il marchio intero
    static/img/favicon.svg   la riduzione a un elemento, per le misure piccole

Da qui escono `logo.png`, i `favicon-*.png`, `favicon.ico` e `mr-rao.ico`,
che sono l'icona del systray, quella dell'eseguibile, quella del
collegamento sul desktop e quella della scheda del browser.

**I raster si rasterizzano dagli SVG, non si ridisegnano.** La versione
precedente ridisegnava il marchio in Pillow: due rappresentazioni dello
stesso disegno che sono puntualmente divergute -- il PNG aveva la stellina
impastata e la R fuori dal cerchio mentre il vettoriale era corretto, e non
c'era modo di accorgersene se non affiancandoli.

Le misure piccole (<= 48) vengono dalla riduzione, le grandi dal marchio
intero: rimpicciolire il marchio intero a 16 px da' un puntino verde.

Le icone sono **artefatti versionati**: questo script si lancia solo quando
cambia il disegno, non a ogni build. Per questo `svglib` e `rlPyCairo` non
stanno in requirements.txt e vanno installati apposta, e disinstallati
dopo -- il gate confronta THIRD_PARTY.md con il venv, e lasciarli dentro
farebbe risultare come dipendenze del prodotto due librerie che il prodotto
non usa:

    venv\\Scripts\\python -m pip install svglib rlPyCairo
    venv\\Scripts\\python scripts/generate_icons.py
    venv\\Scripts\\python -m pip uninstall -y svglib rlPyCairo reportlab

Per rifare i tracciati delle lettere (solo se cambia il carattere) serve
anche `fonttools`, con lo stesso trattamento.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "img"
OUT.mkdir(parents=True, exist_ok=True)

# Sotto questa misura il marchio intero non si legge piu': si usa la
# riduzione. Non e' una soglia estetica, e' dove «Mr.» smette di avere
# abbastanza pixel per esistere.
SOGLIA_RIDOTTA = 48
MISURE = [16, 24, 32, 48, 64, 128, 256]


def _rendi(svg: Path, lato: int, fondo: int) -> Image.Image:
    import io

    from reportlab.graphics import renderPM
    from svglib.svglib import svg2rlg

    disegno = svg2rlg(str(svg))
    if disegno is None:
        raise SystemExit(f"non riesco a leggere {svg}")
    k = lato / disegno.width
    disegno.scale(k, k)
    disegno.width *= k
    disegno.height *= k
    png = renderPM.drawToString(disegno, fmt="PNG", bg=fondo)
    return Image.open(io.BytesIO(png)).convert("RGB")


def rasterizza(svg: Path, lato: int) -> Image.Image:
    """SVG -> immagine RGBA, con la trasparenza ricostruita.

    renderPM rasterizza sempre su un fondo opaco: senza questo passaggio le
    icone escono col rettangolo bianco dietro, che nella barra delle
    applicazioni si vede benissimo.

    Si rende due volte, su bianco e su nero, e l'alfa si ricava dalla
    differenza. Per ogni canale vale Cb = C*a e Cw = C*a + 255*(1-a), quindi
    a = 1 - (Cw - Cb)/255 e il colore vero e' Cb/a. Non e' una stima: e'
    l'inversa esatta della composizione.
    """
    SS = 2  # si rende al doppio e si riduce: bordi tondi senza scaletta
    su_nero = _rendi(svg, lato * SS, 0x000000)
    su_bianco = _rendi(svg, lato * SS, 0xFFFFFF)

    n, b = su_nero.load(), su_bianco.load()
    fuori = Image.new("RGBA", su_nero.size)
    px = fuori.load()
    for y in range(su_nero.size[1]):
        for x in range(su_nero.size[0]):
            rn, gn, bn = n[x, y]
            rw, gw, bw = b[x, y]
            # l'alfa e' uguale sui tre canali: si media per smorzare il rumore
            a = 255 - round(((rw - rn) + (gw - gn) + (bw - bn)) / 3)
            a = max(0, min(255, a))
            if a == 0:
                px[x, y] = (0, 0, 0, 0)
            else:
                px[x, y] = (min(255, rn * 255 // a), min(255, gn * 255 // a),
                            min(255, bn * 255 // a), a)
    return fuori.resize((lato, lato), Image.LANCZOS)


def main() -> None:
    logo, ridotto = OUT / "logo.svg", OUT / "favicon.svg"
    for f in (logo, ridotto):
        if not f.exists():
            raise SystemExit(f"manca {f}")

    print("Rasterizzo dagli SVG…")
    grande = rasterizza(logo, 512)
    grande.save(OUT / "logo.png", format="PNG", optimize=True)
    print(f"  {OUT / 'logo.png'}")

    frames: list[Image.Image] = []
    for s in MISURE:
        sorgente = ridotto if s <= SOGLIA_RIDOTTA else logo
        im = rasterizza(sorgente, s)
        frames.append(im)
        im.save(OUT / f"favicon-{s}.png", format="PNG", optimize=True)
        print(f"  favicon-{s}.png  da {sorgente.name}")

    # Il systray legge favicon-64.png e logo.png (vedi mr_rao/tray.py).
    frames[MISURE.index(64)].save(OUT / "favicon.png", format="PNG", optimize=True)

    # L'ICO tiene dentro tutte le misure, e Windows sceglie la piu' adatta:
    # e' per questo che la riduzione entra nello stesso file del marchio
    # intero, invece di essere un file a parte.
    def scrivi_ico(nome: str, misure: list[int]) -> None:
        scelte = [frames[MISURE.index(m)] for m in misure]
        scelte[-1].save(OUT / nome, format="ICO", sizes=[(m, m) for m in misure],
                        append_images=scelte[:-1])

    scrivi_ico("mr-rao.ico", MISURE)
    scrivi_ico("favicon.ico", [16, 32, 48])

    print("Fatto:")
    for nome in ("logo.png", "mr-rao.ico", "favicon.ico", "favicon.png"):
        p = OUT / nome
        print(f"  {nome:16} {p.stat().st_size:7d} B")


if __name__ == "__main__":
    main()
