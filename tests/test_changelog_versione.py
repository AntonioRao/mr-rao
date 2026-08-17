# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""La versione dichiarata deve avere la sua voce nel changelog.

Il controllo vero sta in `scripts/check_docs.py` e lo esegue il quality gate.
Qui si verificano due cose diverse fra loro:

1. che sul repository vero il controllo sia verde;
2. che su un changelog inventato **sappia diventare rosso**.

Il secondo non e' un doppione del primo. Un controllo che sul repository dice
sempre di si' e' indistinguibile da un controllo rotto, e questo presidio
nasce proprio da una versione rilasciata senza la sua voce: se si spegnesse in
silenzio, l'errore tornerebbe identico e nessuno lo saprebbe.

L'import segue la strada gia' battuta da `test_documenti_pubblicati.py`:
`scripts/` non e' un pacchetto, quindi si aggiunge a `sys.path`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE / "scripts") not in sys.path:
    sys.path.insert(0, str(RADICE / "scripts"))

from check_docs import (  # noqa: E402
    _RE_VOCE_CHANGELOG,
    APP_VERSION,
    versione_senza_changelog,
)

CHANGELOG_FINTO = """# Changelog

## 1.10.0 — Un titolo qualsiasi

Testo della voce, che nomina di sfuggita la 1.11.0 come prossima tappa.

## 1.9.0 — La voce prima

Altro testo.
"""


def test_la_versione_corrente_ha_la_sua_voce():
    """Il repository vero, com'e' adesso."""
    problemi = versione_senza_changelog()
    assert not problemi, "\n".join(problemi)


def test_restituisce_una_lista():
    """Un controllo che tornasse None passerebbe ogni `assert not problemi`."""
    assert isinstance(versione_senza_changelog(), list)


def test_una_versione_mai_documentata_e_un_errore():
    problemi = versione_senza_changelog("1.11.0", CHANGELOG_FINTO)
    assert len(problemi) == 1
    assert "1.11.0" in problemi[0]


def test_il_messaggio_dice_cosa_fare():
    """Segnalare il buco senza dire come si chiude costringe chi legge a
    ricostruire la convenzione dal changelog. Il testo deve contenere il
    rimedio, non solo la diagnosi."""
    (problema,) = versione_senza_changelog("1.11.0", CHANGELOG_FINTO)
    assert "## 1.11.0" in problema, "manca l'intestazione da scrivere"
    assert "APP_VERSION" in problema, "manca l'alternativa: non bumpare"


def test_il_numero_citato_dentro_una_voce_non_basta():
    """La 1.11.0 e' nominata nel testo della voce 1.10.0 del changelog finto.

    E' il falso negativo che un banale `if versione in testo` non vedrebbe: il
    numero c'e', la voce no. Il controllo guarda le intestazioni.
    """
    assert "1.11.0" in CHANGELOG_FINTO
    assert versione_senza_changelog("1.11.0", CHANGELOG_FINTO)


@pytest.mark.parametrize(
    "intestazione",
    [
        "## 1.11.0 — con lo spazio normale",
        "##1.11.0 — senza spazio",
        "##   1.11.0 - con tre spazi",
        "# 1.11.0 — un livello solo",
        "### v1.11.0 — con la v",
        "## [1.11.0] — stile Keep a Changelog",
    ],
)
def test_tollerante_sulla_formattazione(intestazione):
    """Spazi, livello di `#`, `v` e parentesi quadre sono formattazione: una
    voce che esiste non deve risultare mancante per come e' scritto il titolo."""
    assert not versione_senza_changelog("1.11.0", f"# Changelog\n\n{intestazione}\n")


def test_un_changelog_senza_intestazioni_e_un_errore():
    """Zero intestazioni riconosciute non e' «tutto a posto»: e' il caso in cui
    la regex ha smesso di combaciare, e da li' in poi il controllo direbbe
    verde qualunque cosa succeda."""
    (problema,) = versione_senza_changelog("1.11.0", "# Changelog\n\nsolo prosa.\n")
    assert "_RE_VOCE_CHANGELOG" in problema


def test_la_regex_riconosce_il_changelog_vero():
    """Se il formato del file cambiasse, i test sui changelog inventati
    resterebbero verdi mentre il controllo vero non vede piu' niente."""
    testo = (RADICE / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
    versioni = _RE_VOCE_CHANGELOG.findall(testo)
    assert len(versioni) >= 5, "poche voci riconosciute: formato cambiato?"
    assert APP_VERSION in versioni, "la versione corrente non e' fra quelle lette"
