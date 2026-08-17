# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Un numero di telefono italiano non e' un SSN americano.

`078-05-1120` ha la forma 3-2-4 dell'SSN ed e' anche un numero di Oristano.
Il pacchetto inglese e' **acceso di serie**, quindi il caso non e' teorico:
succedeva sulla carta intestata di chiunque, con le impostazioni di serie.

Il dato spariva lo stesso -- non e' mai stata una perdita di riservatezza --
ma il rapporto lo contava fra gli SSN. E il rapporto e' la cosa che si
consegna a chi chiede *cosa* c'era nel documento: se sbaglia il tipo, non
risponde a quella domanda.

I test qui sotto guardano nei **due versi**, perche' la correzione ha due
modi di rompersi e uno solo si vede a occhio:

* se il passo SSN ricomincia a prendersi i numeri etichettati, torna il
  difetto (categoria sbagliata);
* se il passo dei telefoni smette di raccoglierli, il numero **resta in
  chiaro** -- che e' molto peggio del difetto di partenza, ed e' il motivo
  per cui la correzione non toglie e basta, ma lascia il candidato a chi
  viene dopo.
"""
import pytest

from mr_rao.privacy import CORE, IT, PrivacyOptions, apply_privacy_filter


def redigi(testo: str, opzioni: PrivacyOptions | None = None):
    uscita, rapporto = apply_privacy_filter(testo, opzioni or PrivacyOptions())
    return uscita, rapporto.to_dict()["counts"]


# --- il verso «categoria sbagliata» ---------------------------------------

@pytest.mark.parametrize(
    "testo",
    [
        "Tel. 078-05-1120",
        "Fax: 090-12-3456",
        "Telefono 078-05-1120",
        "Cell. 078-05-1120",
        "recapito: 078-05-1120",
        "Phone: 078-05-1120",
    ],
)
def test_un_numero_etichettato_e_un_telefono(testo):
    uscita, conti = redigi(testo)
    assert conti.get("phones") == 1, f"contato come {conti}"
    assert "ssn" not in conti and "itin" not in conti, conti
    # E il verso che conta di piu': il numero **non deve restare li'**.
    # Senza questa riga il test passerebbe anche se la correzione si
    # limitasse a non sostituire nulla.
    assert "078-05-1120" not in uscita and "090-12-3456" not in uscita, uscita


# --- il verso «non ho rotto l'SSN» ----------------------------------------

@pytest.mark.parametrize(
    ("testo", "categoria"),
    [
        ("SSN 078-05-1120", "ssn"),
        ("Social Security Number: 078-05-1120", "ssn"),
        ("078-05-1120", "ssn"),          # senza etichetta resta un SSN
        ("ITIN 912-78-1234", "itin"),
    ],
)
def test_un_ssn_vero_resta_un_ssn(testo, categoria):
    uscita, conti = redigi(testo)
    assert conti.get(categoria) == 1, f"{testo!r} contato come {conti}"
    assert "phones" not in conti, conti


def test_l_etichetta_deve_essere_attaccata_al_numero():
    """La finestra e' corta apposta.

    «Tel. 011 22 33 44 — SSN 078-05-1120» ha la parola «Tel» nella riga, ma
    non davanti a *questo* numero. Se la guardia guardasse tutta la riga
    invece dei caratteri immediatamente precedenti, un SSN vero accanto a un
    recapito diventerebbe invisibile al passo che deve prenderlo.
    """
    uscita, conti = redigi("Tel. 011 22 33 44 e poi SSN 078-05-1120")
    assert conti.get("ssn") == 1, conti
    assert conti.get("phones") == 1, conti


def test_col_pacchetto_inglese_spento_il_numero_sparisce_lo_stesso():
    """Il caso che l'audit segnalava, e che **non** e' un difetto.

    Con `pacchetti=(core, it)` chi converte ha detto «qui dati americani non
    ce ne sono». `SSN 078-05-1120` diventa allora `{{PHONE}}`: e' l'unico
    riconoscitore rimasto acceso che quel numero lo sa leggere, e il dato
    sparisce. Chiamarlo telefono e' il nome piu' preciso che si possa dare
    con gli strumenti che l'utente ha lasciato accesi -- l'alternativa
    sarebbe lasciarlo in chiaro, che protegge meno e informa uguale.
    """
    uscita, conti = redigi(
        "SSN 078-05-1120", PrivacyOptions(pacchetti=frozenset({CORE, IT}))
    )
    assert "078-05-1120" not in uscita, uscita
    assert conti.get("phones") == 1, conti
