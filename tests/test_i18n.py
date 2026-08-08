"""Le due lingue: il meccanismo, non le traduzioni.

I test sulle singole stringhe non servono -- una traduzione sbagliata la
vede una persona, non un assert. Servono invece i tre controlli che una
persona **non** vede rileggendo: una chiave presente in una lingua e non
nell'altra, un segnaposto scritto diverso fra le due, e la lingua scelta
male dal browser.

Il secondo e' quello che rompe davvero: `{host}` tradotto `{ospite}` alza
un KeyError a tempo di esecuzione, e solo per la pagina che ci passa.
"""
from __future__ import annotations

import pytest

from mr_rao.i18n import LINGUE, TESTI, lingua_da, plurale, t

RE_SEGNAPOSTO = __import__("re").compile(r"\{([a-z_]+)\}")


def test_ogni_chiave_esiste_in_tutte_le_lingue():
    for chiave, voce in TESTI.items():
        mancanti = set(LINGUE) - set(voce)
        assert not mancanti, f"«{chiave}» manca in {sorted(mancanti)}"


def test_i_segnaposto_coincidono_fra_le_lingue():
    """Il difetto che non si vede rileggendo, e che alza un errore solo
    sulla pagina che passa di li'."""
    for chiave, voce in TESTI.items():
        attesi = None
        for lingua in LINGUE:
            trovati = set(RE_SEGNAPOSTO.findall(voce[lingua]))
            if attesi is None:
                attesi = trovati
            else:
                assert trovati == attesi, (
                    f"«{chiave}»: {lingua} ha {sorted(trovati)}, "
                    f"le altre {sorted(attesi)}"
                )


def test_nessuna_traduzione_vuota():
    for chiave, voce in TESTI.items():
        for lingua in LINGUE:
            assert voce[lingua].strip(), f"«{chiave}» vuota in {lingua}"


def test_una_chiave_assente_non_alza():
    """Una stringa mancante deve produrre un'interfaccia brutta, non una
    pagina di errore: il test sulle chiavi la trova prima dell'utente."""
    assert t("chiave_che_non_esiste") == "chiave_che_non_esiste"


def test_i_segnaposto_vengono_sostituiti():
    assert "Mr. Rao" in t("titolo_pagina", "it", app="Mr. Rao")
    assert "Mr. Rao" in t("titolo_pagina", "en", app="Mr. Rao")


@pytest.mark.parametrize(
    "n,it_atteso,en_atteso",
    [(1, "1 redazione", "1 redaction"), (3, "3 redazioni", "3 redactions")],
)
def test_il_plurale_e_giusto_in_entrambe(n, it_atteso, en_atteso):
    """«1 redazioni» e' sbagliato in italiano quanto «1 redactions» in
    inglese, e oggi lo scriviamo in tre punti diversi del JavaScript."""
    assert plurale("redazioni", n, "it") == it_atteso
    assert plurale("redazioni", n, "en") == en_atteso


@pytest.mark.parametrize(
    "accept,atteso,perche",
    [
        ("it-IT,it;q=0.9", "it", "browser italiano"),
        ("en-GB,en;q=0.9", "en", "browser inglese"),
        ("de-DE,de;q=0.9", "en", "tutto il resto del mondo vede inglese"),
        ("fr-FR", "en", "idem"),
        (None, "it", "nessuna intestazione: resta il predefinito"),
    ],
)
def test_la_lingua_si_deduce_dal_browser(accept, atteso, perche):
    assert lingua_da(accept) == atteso, perche


def test_la_scelta_esplicita_vince_sul_browser():
    """Chi ha cliccato il selettore ha detto qualcosa di piu' preciso di
    quanto dica la configurazione del suo browser."""
    assert lingua_da("it-IT", cookie="en") == "en"
    assert lingua_da("en-GB", cookie="it") == "it"
    assert lingua_da("it-IT", cookie="it", query="en") == "en"


def test_una_lingua_inventata_viene_ignorata():
    assert lingua_da("it-IT", cookie="klingon") == "it"
