"""Le invarianti dei documenti che si possono controllare sempre.

Il controllo completo sta in `scripts/check_docs.py` e lo esegue il quality
gate, perche' una delle quattro invarianti — il conteggio dei test — la
conosce solo chi ha appena eseguito l'intera suite, e `pytest` si lancia
spesso su un file solo.

Le altre tre non dipendono da come e' stato invocato pytest, quindi vale la
pena che scattino anche qui: chi lancia i test e basta si accorge lo stesso
di aver rotto un link o duplicato un identificativo.

L'elenco dei file lo da' `git ls-files`, non una lista scritta a mano. E' il
punto dell'intera faccenda: alla domanda «i documenti sono aggiornati?»
avevo risposto di si' guardando quelli che stavo modificando, e due erano
fermi da quindici release. Un controllo che parte da cio' che ho in mano
trova solo cio' che ho gia' guardato.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE / "scripts") not in sys.path:
    sys.path.insert(0, str(RADICE / "scripts"))

from check_docs import (  # noqa: E402
    documenti,
    id_duplicati,
    link_rotti,
    versioni_incoerenti,
)


def test_ci_sono_documenti_da_controllare():
    """Se `git ls-files` smettesse di trovarli, gli altri test passerebbero
    tutti per il motivo sbagliato: zero file, zero problemi."""
    trovati = documenti()
    assert len(trovati) >= 10
    nomi = {f.name for f in trovati}
    for atteso in ("README.md", "SECURITY.md", "BACKLOG.md", "PRIVACY.md"):
        assert atteso in nomi, f"{atteso} non e' fra i documenti tracciati"


def test_nessun_identificativo_duplicato():
    problemi = id_duplicati()
    assert not problemi, "\n".join(problemi)


def test_nessun_link_rotto():
    problemi = link_rotti()
    assert not problemi, "\n".join(problemi)


def test_nessuna_versione_vecchia():
    problemi = versioni_incoerenti()
    assert not problemi, "\n".join(problemi)


@pytest.mark.parametrize(
    "controllo", [id_duplicati, link_rotti, versioni_incoerenti]
)
def test_i_controlli_restituiscono_una_lista(controllo):
    """Un controllo che tornasse None passerebbe ogni assert `not problemi`
    senza guardare niente. E' il modo in cui questi presidi muoiono zitti."""
    assert isinstance(controllo(), list)
