# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il banco del controllo che guarda il sito **come lo vede un visitatore**.

Non tocca la rete: il lettore e' iniettabile, ed e' questo che rende
verificabile un controllo che per natura parla con l'esterno.
"""
from __future__ import annotations

import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
for p in (RADICE, RADICE / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from check_sito_non_espone import ATTESI, VIETATI, controlla  # noqa: E402

HOST = "https://esempio.invalid"


def _tutto_a_posto(url: str) -> int:
    """Il sito sano: gli attesi rispondono, i vietati no."""
    return 200 if any(url.endswith(a) for a in ATTESI) else 404


def test_un_sito_sano_non_ha_niente_da_dire():
    esposti, spenti = controlla(HOST, _tutto_a_posto)
    assert esposti == []
    assert spenti == []


def test_un_file_che_non_dovrebbe_esserci_viene_nominato():
    def lettore(url: str) -> int:
        if url.endswith("/_rebuild.py"):
            return 200
        return _tutto_a_posto(url)

    esposti, spenti = controlla(HOST, lettore)
    assert esposti == ["/_rebuild.py"]
    assert spenti == []


def test_un_sito_spento_non_e_un_sito_pulito():
    """Il difetto che questa verifica impedisce e' il piu' insidioso: se tutto
    risponde 404 -- sito giu', dominio scaduto, deploy vuoto -- un controllo
    che cerca solo i 200 di troppo direbbe «tutto a posto» proprio nel momento
    peggiore. Per questo `ATTESI` esiste e i due esiti sono separati.
    """
    esposti, spenti = controlla(HOST, lambda url: 404)
    assert esposti == []
    assert spenti == list(ATTESI)


def test_l_elenco_dei_vietati_contiene_i_file_che_ci_sono_finiti_davvero():
    """Non e' un elenco di path «tipici» da scanner: sono i file che il
    22/08/2026 erano davvero online. Un elenco che dimentica proprio quelli
    sarebbe un controllo che guarda dall'altra parte.
    """
    for atteso in ("/_rebuild.py", "/test-results/.last-run.json", "/.assetsignore"):
        assert atteso in VIETATI, f"{atteso} deve restare nell'elenco"
    # E i classici, che servono a sorvegliare il ritorno del ripiego HTML.
    assert "/.git/HEAD" in VIETATI and "/.env" in VIETATI
