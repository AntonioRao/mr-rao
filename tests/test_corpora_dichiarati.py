# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Ogni corpus che scarichiamo deve essere dichiarato in NOTICE.md.

Perche' esiste
--------------

I numeri che questo progetto pubblica — falsi positivi, richiamo, copertura
per categoria — poggiano su documenti e corpora che non sono nostri. La
sezione 6 di `NOTICE.md` li elenca con la loro licenza, e non e' un
adempimento formale: e' cio' che rende le misure **ricontrollabili** invece
che da credere sulla parola.

Un elenco del genere pero' invecchia da solo. Basta che qualcuno aggiunga
uno script che scarica un corpus nuovo e non tocchi `NOTICE.md`, e da quel
momento il documento dice il falso per omissione — con l'aggravante che
sembra completo. Non e' un caso di scuola: gli script di scaricamento sono
gia' tre, e sono nati tutti nella stessa settimana.

Come lo controlla
-----------------

Non guarda un elenco scritto a mano: cerca gli script che scaricano un
corpus — quelli il cui nome comincia per `scarica_corpus_` — e pretende che
ognuno sia **nominato** nella sezione. Cosi' uno script nuovo entra nella
prova il giorno che nasce.

Il secondo test e' quello che tiene onesto il primo: se l'estrazione
smettesse di trovare script, questo file diventerebbe verde per non aver
guardato niente.
"""

from __future__ import annotations

from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
NOTICE = RADICE / "NOTICE.md"
SCRIPTS = RADICE / "scripts"


def scaricatori() -> list[str]:
    return sorted(p.name for p in SCRIPTS.glob("scarica_corpus_*.py"))


def test_ce_ne_sono_da_provare() -> None:
    """La guardia della guardia.

    Se un domani gli script di scaricamento cambiassero convenzione di nome,
    l'estrazione tornerebbe una lista vuota e il test sotto passerebbe
    sempre — verde, e cieco.
    """
    assert len(scaricatori()) >= 3, scaricatori()


@pytest.mark.parametrize("script", scaricatori())
def test_ogni_scaricatore_e_dichiarato_nel_notice(script: str) -> None:
    testo = NOTICE.read_text(encoding="utf-8")
    assert script in testo, (
        f"{script} scarica un corpus che non e' dichiarato in NOTICE.md. "
        "I numeri che pubblichiamo si appoggiano a materiale di qualcun "
        "altro: senza il credito e la licenza, la misura non e' "
        "ricontrollabile — e l'elenco sembra completo proprio mentre non lo e'"
    )


def test_il_notice_dice_anche_che_non_li_ridistribuiamo() -> None:
    """La frase che evita un fraintendimento sgradevole.

    Un elenco di corpora dentro un repository si legge come «questa roba sta
    qui dentro». Non ci sta: gli script la scaricano sulla macchina di chi
    misura. Se quella precisazione sparisse, il documento suggerirebbe una
    ridistribuzione che non avviene — e per uno dei tre corpora la licenza
    non e' banale.
    """
    testo = NOTICE.read_text(encoding="utf-8")
    for pezzo in ("non distribuiti", "not redistributed"):
        assert pezzo in testo, pezzo


def test_le_licenze_sono_nominate() -> None:
    """Senza la licenza, il credito e' incompleto — e una delle tre e' un
    caso in cui l'errore costerebbe: quel corpus non e' semplicemente
    CC-BY, e chi lo legasse a un prodotto commerciale credendolo tale
    erediterebbe condizioni che non ha guardato."""
    testo = NOTICE.read_text(encoding="utf-8")
    assert "Llama" in testo, "la catena di licenze ereditata non e' dichiarata"
    assert "MIT" in testo
