# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il ruolo scritto prima dell'indirizzo non e' il nome di una persona.

Due parole maiuscole subito prima di un'email diventano un nome anche se in
nessun elenco: e' la regola che prende i nomi stranieri e quelli rari, e sulle
firme funziona. In un curriculum o in una firma di lavoro pero' davanti
all'indirizzo c'e' **il mestiere**: «Enterprise Architect antonio@…» faceva
sparire «Enterprise» -- e, siccome i segnaposto sono numerati per valore, da
li' in poi spariva ogni «Enterprise» della pagina. Trovato su un curriculum
vero, non su un banco.

I test guardano nei due versi, perche' la correzione ha due modi di rompersi
e uno solo si vede a occhio:

* se la guardia si allarga, un nome vero smette di essere tolto -- ed e'
  molto peggio del difetto di partenza;
* se si stringe, il mestiere torna a sparire dal documento.

Il vincolo che tiene in piedi il primo verso e' che la guardia scatti solo
quando **nessuna** delle parole sta negli elenchi di nomi e cognomi.
"""
import pytest

from mr_rao.privacy import MESTIERI, PrivacyOptions, apply_privacy_filter


def _redigi(testo: str) -> tuple[str, dict]:
    fuori, rapporto = apply_privacy_filter(testo, PrivacyOptions())
    return fuori, dict(rapporto.counts)


# --- cio' che deve smettere di sparire --------------------------------------


@pytest.mark.parametrize(
    "testo, parole",
    [
        ("Enterprise Architect antonio.rao@example.com", "Enterprise Architect"),
        ("Project Manager giulia.verdi@example.com", "Project Manager"),
        ("CISO | Cybersecurity & Enterprise Architect a.rao@example.com",
         "Enterprise Architect"),
        ("Security Specialist info@example.com", "Security Specialist"),
    ],
)
def test_un_mestiere_prima_dell_indirizzo_resta(testo, parole):
    fuori, conteggi = _redigi(testo)
    assert parole in fuori, fuori
    assert "names" not in conteggi, conteggi
    # L'indirizzo invece esce, come sempre.
    assert "{{EMAIL_1}}" in fuori


# --- cio' che deve continuare a sparire -------------------------------------


@pytest.mark.parametrize(
    "testo",
    [
        # Nome e cognome italiani: stanno negli elenchi.
        "Mario Rossi mario.rossi@example.com",
        # Nome straniero, in nessun elenco: e' il caso per cui la regola
        # larga esiste, e deve continuare a funzionare.
        "Klaus Vogel klaus.vogel@example.com",
        # Il titolo davanti al nome vero: «Mario» sta negli elenchi, quindi
        # la guardia non scatta.
        "Direttore Mario Rossi mario.rossi@example.com",
        # Un cognome degli elenchi accanto a un mestiere: e' una persona.
        "Rossi Manager mario.rossi@example.com",
    ],
)
def test_un_nome_prima_dell_indirizzo_esce_sempre(testo):
    fuori, conteggi = _redigi(testo)
    assert conteggi.get("names") == 1, (fuori, conteggi)
    assert "{{NAME_1}}" in fuori


def test_la_guardia_non_tocca_il_nome_dopo_l_indirizzo():
    fuori, conteggi = _redigi("scrivi a mario.rossi@example.com (Mario Rossi)")
    assert conteggi.get("names") == 1, (fuori, conteggi)


def test_l_elenco_dei_mestieri_non_contiene_titoli_di_cortesia():
    """«Dottore Mario Rossi» non deve poter far saltare il nome.

    I titoli di cortesia stanno davanti ai nomi veri tutti i giorni: metterli
    qui dentro trasformerebbe una guardia contro i falsi positivi in una
    perdita di dati. Questo test esiste perche' aggiungerli sembra comodo.
    """
    for titolo in ("dottore", "dott", "avvocato", "ingegner", "signor",
                   "signora", "professore", "geometra"):
        assert titolo not in MESTIERI, titolo


def test_i_mestieri_sono_scritti_in_minuscolo():
    """Il confronto avviene su parole gia' minuscolizzate: una voce con la
    maiuscola dentro l'elenco non verrebbe mai trovata, e la guardia
    smetterebbe di funzionare **in silenzio** per quella parola."""
    assert all(voce == voce.lower() for voce in MESTIERI)
