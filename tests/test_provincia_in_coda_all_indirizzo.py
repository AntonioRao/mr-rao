# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""La sigla di provincia chiude l'indirizzo, e prima restava fuori.

Perche' esiste
--------------

Il riconoscitore degli indirizzi prendeva gia' la coda `CAP + comune` --
questa parte non mancava, contrariamente a quanto sembrava a una lettura
veloce. Restava fuori **solo la sigla della provincia**, e l'uscita era:

    Residente in {{ADDRESS}} (MI)

Non e' un dato che identifica da solo: le province italiane sono 107 e in
quella di Milano vivono tre milioni di persone. Il motivo per cui va tolta
e' un altro, ed e' di leggibilita' della redazione: il documento presenta
l'indirizzo come **un blocco unico**, e un blocco redatto a meta' fa
dubitare del resto. Chi rilegge non sa se il pezzo rimasto e' rimasto
apposta.

Lo schema propone, l'elenco decide
----------------------------------

Due lettere maiuscole dopo un comune non sono una provincia. La prima
versione di questa regola si mangiava la `IT` di «Milano IT», e il giorno
dopo si sarebbe mangiata «Milano IL GIORNO 5» -- portandosi via due parole
della frase successiva.

Le province sono un **insieme chiuso**, quindi qui non c'e' niente da
indovinare: e' lo stesso criterio del mod-97 per gli IBAN, applicato a un
elenco invece che a un conto. E quando la sigla non passa, torna al testo
**senza far fallire l'indirizzo**: si redige la via e le due lettere
restano dov'erano.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import pytest

from mr_rao.privacy import (
    _SIGLE_PROVINCIA,
    PrivacyOptions,
    apply_privacy_filter,
    senza_numeri,
)


def redigi(testo: str) -> str:
    return senza_numeri(apply_privacy_filter(testo, PrivacyOptions())[0])


# --------------------------------------------------- la guardia della guardia


def test_l_elenco_delle_province_e_completo() -> None:
    """107 province, non 106 ne' 108.

    Un elenco che perde una voce non da' errore: da' una fuga silenziosa
    proprio sulla provincia che manca. E uno che ne guadagna una inventata
    si mangia una parola vera della frase.
    """
    assert len(_SIGLE_PROVINCIA) == 107, sorted(_SIGLE_PROVINCIA)
    # Qualche estremo dell'alfabeto e le due piu' recenti (Sud Sardegna,
    # Barletta-Andria-Trani), che sono quelle che un elenco vecchio non ha.
    for sigla in ("AG", "MI", "RM", "TO", "VV", "SU", "BT", "MB"):
        assert sigla in _SIGLE_PROVINCIA, sigla
    assert all(len(s) == 2 and s.isupper() for s in _SIGLE_PROVINCIA)


# ------------------------------------------------------------ viene presa


@pytest.mark.parametrize(
    "frase",
    [
        "Residente in Via Roma 12, 20121 Milano (MI)",
        "domicilio: via Giuseppe Verdi 44, 00147 Roma RM",
        "Sede in Corso Italia 8 - 10121 Torino (TO), scala B",
        "recapito: piazza Dante 3, 09121 Cagliari SU",
    ],
)
def test_la_provincia_entra_nel_segnaposto(frase: str) -> None:
    fuori = redigi(frase)
    assert "{{ADDRESS}}" in fuori, fuori
    # Nessuna sigla rimasta a penzolare dopo il segnaposto.
    coda = fuori.split("{{ADDRESS}}")[1]
    assert not coda.strip().startswith(("(", "MI", "RM", "TO", "SU")), fuori


def test_l_indirizzo_senza_provincia_funziona_come_prima() -> None:
    """La riga aggiunta e' facoltativa: non deve pretendere la provincia."""
    assert redigi("Sede legale in Corso Italia 8 - 10121 Torino") == (
        "Sede legale in {{ADDRESS}}"
    )


# ------------------------------------------------- e quando NON e' una provincia


@pytest.mark.parametrize(
    "frase,resta",
    [
        # Il caso che ha fatto scrivere l'elenco: due parole della frase
        # successiva che finivano dentro il segnaposto.
        ("Via Roma 12, 20121 Milano IL GIORNO 5 si presenta", "IL GIORNO 5"),
        # La sigla della nazione, che sembra una provincia e non lo e'.
        ("Via Roma 12, 20121 Milano IT ha sede qui", "IT"),
        # Fra parentesi: qui non e' una parola della frase, ma resta
        # comunque fuori perche' non e' una provincia.
        ("Via Roma 12, 20121 Milano (XX) altro", "(XX)"),
    ],
)
def test_una_sigla_che_non_e_provincia_torna_al_testo(frase: str, resta: str) -> None:
    """**Torna al testo, e l'indirizzo resta riconosciuto.**

    Far fallire tutta la corrispondenza sarebbe il modo sbagliato di essere
    prudenti: si perderebbe la via per non prendere due lettere.
    """
    fuori = redigi(frase)
    assert "{{ADDRESS}}" in fuori, f"l'indirizzo dev'essere riconosciuto: {fuori}"
    assert resta in fuori, f"«{resta}» doveva restare nel testo: {fuori}"


def test_due_maiuscole_da_sole_non_sono_un_indirizzo() -> None:
    """Fuori dalla coda di un indirizzo, `MI` e' una nota musicale.

    La sigla e' ammessa **solo** attaccata a `CAP + comune`, che a sua volta
    esiste solo dopo una parola-chiave stradale. Senza questa catena il
    riconoscitore diventerebbe un cercatore di maiuscole.
    """
    for frase in ("Il tono era MI bemolle", "La sigla RM non significa niente qui"):
        assert "{{ADDRESS}}" not in redigi(frase), frase
