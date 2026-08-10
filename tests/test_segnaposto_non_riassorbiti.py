"""Un segnaposto gia' inserito non deve tornare in bocca al motore.

Trovato dal corpus di conformita', non da un test: `NINO` — il segnaposto
del National Insurance number britannico — e' anche un nome di battesimo
italiano. Quindi su

    National Insurance number AB123456C

il testo usciva **giusto** (`{{NINO}}`) e il rapporto portava un sospetto di
tipo «nome» in piu', con il campione mascherato di una parola che era gia'
un segnaposto.

**Perche' conta piu' di quanto sembri.** I sospetti sono la parte onesta del
rapporto: dicono «qui c'e' qualcosa che assomiglia a un dato personale e
**non** l'ho tolto, vallo a guardare». Un sospetto inventato manda a
guardare un punto dove non c'e' niente, e chi ne trova due o tre finti
smette di guardarli tutti. Rumore su quella lista costa piu' che altrove.

**La causa.** `_TOK_MISTO` e `_RE_NAME_PAIR_UPPER` avevano gia' la guardia
esplicita contro i segnaposto — `(?<![\\w{])` e `(?![\\w}])` — perche' le
graffe non sono caratteri di parola e senza di quelle il confine si apre
dentro `{{...}}`. `_RE_LONE_TOKEN` e `_RE_NAME_RUN` no.

**Perche' questo test enumera i segnaposto invece di provare NINO.** Oggi
il collo e' uno solo su trenta. Domani un riconoscitore nuovo puo' portare
un segnaposto che e' un altro nome italiano — e nessuno ci penserebbe. Il
test legge i segnaposto **dal sorgente del motore**, come fa
`scripts/check_docs.py`: cosi' un segnaposto nuovo entra nella prova da
solo, il giorno che viene scritto.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from mr_rao.privacy import apply_privacy_filter, options_from_dict

RADICE = Path(__file__).resolve().parent.parent


def segnaposto_emessi() -> list[str]:
    """Gli stessi che guarda il gate: quelli scritti nel motore."""
    sorgenti = "".join(
        (RADICE / "mr_rao" / f).read_text(encoding="utf-8")
        for f in ("privacy.py", "en_formats.py")
    )
    return sorted(set(re.findall(r'"(\{\{[A-Z_]+\}\})"', sorgenti)))


def test_ce_ne_sono_da_provare():
    """Se l'estrazione smette di trovarli, il test sotto passerebbe a vuoto.

    E' il caso in cui un controllo diventa verde per non aver guardato
    niente, che qui sarebbe particolarmente facile: basta che qualcuno
    cambi il modo di scrivere i segnaposto nel sorgente.
    """
    assert len(segnaposto_emessi()) >= 20


@pytest.mark.parametrize("segnaposto", segnaposto_emessi())
def test_un_segnaposto_non_diventa_un_sospetto(segnaposto: str):
    testo = f"Il valore {segnaposto} resta cosi'."
    uscita, rapporto = apply_privacy_filter(testo, options_from_dict({}))

    assert uscita == testo, (
        f"{segnaposto} e' stato riscritto: un segnaposto gia' inserito non "
        "deve passare una seconda volta dal motore"
    )
    assert rapporto.suspects == [], (
        f"{segnaposto} ha prodotto un sospetto: {rapporto.suspects}. "
        "I sospetti sono la parte del rapporto su cui si regge l'onesta' "
        "del prodotto, e uno inventato manda a guardare dove non c'e' niente"
    )


def test_il_caso_da_cui_e_nato():
    """Il giro completo, come lo incontra chi usa il programma."""
    uscita, rapporto = apply_privacy_filter(
        "National Insurance number AB123456C", options_from_dict({})
    )
    assert uscita == "National Insurance number {{NINO}}"
    assert rapporto.counts == {"nino": 1}
    assert rapporto.suspects == []
