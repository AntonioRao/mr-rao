"""Le pagine pubblicate devono venire dai sorgenti, e gli hash CSP da loro.

Il sito e' due file HTML con `<style>` e `<script>` scritti dentro la
pagina, e una CSP che li ammette **per impronta**. Basta cambiare uno spazio
nel blocco inline e l'impronta in `_headers` non corrisponde piu': il
browser blocca lo stile e il codice, e il sito va online **bianco**. Nessun
errore, nessun log, nessuno se ne accorge finche' non ci passa qualcuno.

Il rigeneratore (`docs/landing/publish/_rebuild.py`) e' scritto con cura e
si ferma su ogni passaggio che non trova niente. Il buco non era li': era
che **nessuno lo obbligava a girare**. Si modificava il sorgente, si faceva
commit, e la pagina pubblicata restava quella di prima con le sue impronte
di prima -- coerenti fra loro, e diverse da cio' che si era scritto.

Questo test non ricalcola le impronte per conto suo: **rilancia il
rigeneratore** su una copia di lavoro e pretende che non cambi niente. Cosi'
copre in un colpo i tre modi di sbagliare, che sono tre e non uno:

* sorgente modificato e rigeneratore mai lanciato;
* pagina pubblicata modificata a mano;
* impronte in `_headers` rimaste indietro.

Un test che si limitasse a ricalcolare gli hash dai file pubblicati direbbe
«tutto a posto» in tutti e tre i casi: i file pubblicati sarebbero coerenti
con se stessi. E' esattamente un controllo che non puo' fallire.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
LANDING = RADICE / "docs" / "landing"
PUBBLICA = LANDING / "publish"

SORGENTI = ("01-protocollo-zero.html", "01-protocollo-zero.en.html")
GENERATI = ("index.html", "en/index.html", "_headers")

pytestmark = pytest.mark.skipif(
    not (PUBBLICA / "_rebuild.py").exists(),
    reason="la landing non fa parte di questa copia",
)


@pytest.fixture(scope="module")
def rigenerata(tmp_path_factory) -> Path:
    """Una copia di lavoro con il rigeneratore appena lanciato.

    Si copia solo cio' che serve -- i due sorgenti, gli asset, `_headers` --
    e non i font: un megabyte di woff2 non entra nel calcolo delle impronte,
    e copiarlo a ogni giro renderebbe questo test abbastanza lento da
    invogliare a spegnerlo.
    """
    lavoro = tmp_path_factory.mktemp("landing")
    (lavoro / "publish" / "assets").mkdir(parents=True)
    for nome in SORGENTI:
        shutil.copyfile(LANDING / nome, lavoro / nome)
    shutil.copyfile(PUBBLICA / "_rebuild.py", lavoro / "publish" / "_rebuild.py")
    shutil.copyfile(PUBBLICA / "_headers", lavoro / "publish" / "_headers")
    for asset in (PUBBLICA / "assets").iterdir():
        if asset.is_file():
            shutil.copyfile(asset, lavoro / "publish" / "assets" / asset.name)

    esito = subprocess.run(
        [sys.executable, str(lavoro / "publish" / "_rebuild.py")],
        capture_output=True,
        text=True,
    )
    assert esito.returncode == 0, esito.stdout + esito.stderr
    return lavoro / "publish"


@pytest.mark.parametrize("nome", GENERATI)
def test_il_file_pubblicato_e_quello_che_il_rigeneratore_produce(rigenerata, nome):
    atteso = (rigenerata / nome).read_text(encoding="utf-8")
    reale = (PUBBLICA / nome).read_text(encoding="utf-8")
    assert reale == atteso, (
        f"{nome} non corrisponde ai sorgenti.\n"
        "Rilancia:  python docs/landing/publish/_rebuild.py"
    )


def test_le_impronte_csp_coprono_i_blocchi_inline_delle_due_pagine():
    """La riga che spiega *perche'* il confronto qui sopra e' quello giusto.

    Non ricalcola: legge `_headers` e conta. Due pagine, un blocco `<style>`
    e uno `<script>` ciascuna, una CSP sola per tutto il sito: se le
    impronte per direttiva non sono due, una delle due pagine e' scoperta e
    andra' online bianca -- e il confronto file-per-file qui sopra non se ne
    accorgerebbe, perche' `_rebuild.py` produrrebbe lo stesso `_headers`
    monco che c'e' gia'.
    """
    import re

    hdr = (PUBBLICA / "_headers").read_text(encoding="utf-8")
    for direttiva in ("script-src", "style-src"):
        trovate = re.search(rf"{direttiva} 'self'((?: 'sha256-[^']+')+)", hdr)
        assert trovate, f"nessuna impronta per {direttiva}"
        assert len(re.findall(r"sha256-", trovate.group(1))) == 2, (
            f"{direttiva}: attese 2 impronte, una per pagina"
        )
