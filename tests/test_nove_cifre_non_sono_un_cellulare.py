# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Nove cifre che cominciano per 3, in una tabella, non sono un recapito.

I cellulari italiani assegnati oggi sono a dieci cifre. A nove ci sono i
numeri vecchi: esistono ancora, e vanno protetti. Ma «3## ### ###» e' anche
la forma di una colonna di valori, e un recapito non ha nessuna aritmetica
che possa smentirne la forma -- a differenza di un IBAN o di una carta, che
il mod-97 e Luhn bocciano.

Misurato su una Certificazione Unica vera: quattro gruppi cosi', **nessuno**
dei quali era un recapito, e uno veniva davvero cancellato da dentro una
tabella. Cioe' un numero tolto da un modulo fiscale.

Da qui la stretta: i nove cifre chiedono una parola di contatto («tel.»,
«cell.», «fax»…) o un prefisso internazionale; i dieci restano come prima.

Il verso pericoloso e' il secondo -- un recapito vero che smette di uscire --
e per questo i test qui sotto pretendono che il numero a nove cifre **esca
comunque** appena il testo dice che e' un recapito.
"""
import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter


def _conta(testo: str) -> tuple[str, int]:
    fuori, rapporto = apply_privacy_filter(testo, PrivacyOptions())
    return fuori, rapporto.counts.get("phones", 0)


# --- cio' che deve smettere di sparire --------------------------------------


@pytest.mark.parametrize(
    "testo",
    [
        "Imponibile 312 456 789 nella colonna A",
        "Valori: 345 678 901 - 356 789 012",
        "MaxFullFrameLuminance = 321.123456",
    ],
)
def test_nove_cifre_senza_contesto_restano(testo):
    fuori, quanti = _conta(testo)
    assert quanti == 0, (fuori, quanti)


# --- cio' che deve continuare a sparire -------------------------------------


@pytest.mark.parametrize(
    "testo",
    [
        # La parola di contatto basta e avanza.
        "Cell. 333 123 456",
        "Tel. 333 123 456",
        "telefono: 333123456",
        # Il prefisso internazionale si dichiara da solo.
        "+39 333 123 456",
        # Dieci cifre: e' un cellulare di oggi, e non serve nient'altro.
        "Chiamami al 333 1234567 domani",
        "3331234567",
    ],
)
def test_un_recapito_vero_esce_lo_stesso(testo):
    fuori, quanti = _conta(testo)
    assert quanti == 1, (fuori, quanti)
    assert "{{PHONE_1}}" in fuori


def test_la_stretta_riguarda_solo_i_nove_cifre():
    """Dieci cifre senza contesto: prima uscivano, e devono continuare.

    E' la meta' della regola che non e' stata toccata, e un test che guarda
    solo cio' che e' cambiato non se ne accorgerebbe.
    """
    fuori, quanti = _conta("Il numero e 3391234567, scrivimi")
    assert quanti == 1, (fuori, quanti)
