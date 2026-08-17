# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Gli esempi della FAQ per reviewer devono restare veri.

`docs/PRIVACY_FAQ.md` è scritta per chi apre il repository con l'intenzione
di trovarci un overclaim. Un esempio che non corrisponde più al codice è
esattamente ciò che quella persona cerca — e la pagina dice di sé «se il
codice cambia e questa pagina no, vince il codice». Questo file è il modo di
accorgersene prima che se ne accorga qualcun altro.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter

FAQ = Path(__file__).resolve().parents[1] / "docs" / "PRIVACY_FAQ.md"


@pytest.fixture(scope="module")
def testo_faq() -> str:
    return FAQ.read_text(encoding="utf-8")


TESTO_8 = "Scrivi a Mario Rossi <m.rossi@a.it> e a Luigi Bianchi <l.bianchi@b.it>"
ATTESO_8 = "Scrivi a {{NAME_1}} <{{EMAIL_1}}> e a {{NAME_2}} <{{EMAIL_2}}>"


def test_i_segnaposto_sono_numerati():
    """Fino alla 1.19 questo test diceva l'opposto, e aveva ragione allora.

    La domanda 8 costruiva su «i segnaposto non sono numerati» due
    conclusioni: che in uscita non si potesse ricollegare chi era chi, e che
    non esistesse nessuna mappa da custodire. La numerazione (1.20.0) toglie
    la **prima** e lascia intatta la seconda, e la pagina e' stata riscritta
    per dirlo invece di lasciare in piedi una promessa piu' larga del vero.
    """
    risultato, _ = apply_privacy_filter(TESTO_8, PrivacyOptions())
    assert risultato == ATTESO_8


def test_la_numerazione_non_e_stabile_fra_documenti():
    """La proprieta' su cui la pagina *continua* a costruire.

    Se `Mario Rossi` fosse `{{NAME_1}}` in ogni documento, il numero sarebbe
    un identificatore persistente -- un dato personale nuovo, creato da noi.
    Non lo e' perche' dipende dall'ordine di comparsa, e questo test lo
    mostra invertendo l'ordine: la stessa persona cambia numero.
    """
    dritto, _ = apply_privacy_filter("Mario Rossi e Luigi Bianchi", PrivacyOptions())
    rovescio, _ = apply_privacy_filter("Luigi Bianchi e Mario Rossi", PrivacyOptions())
    assert dritto == "{{NAME_1}} e {{NAME_2}}"
    assert rovescio == "{{NAME_1}} e {{NAME_2}}"
    # Cioe': in uno «{{NAME_1}}» e' Mario, nell'altro e' Luigi. Il numero non
    # e' una chiave su cui si possa fare un join fra due documenti.


def test_spegnere_la_numerazione_riporta_la_forma_di_prima():
    """La pagina lo promette a chi preferiva l'uscita della 1.19."""
    risultato, _ = apply_privacy_filter(TESTO_8, PrivacyOptions(numerati=False))
    assert risultato == "Scrivi a {{NAME}} <{{EMAIL}}> e a {{NAME}} <{{EMAIL}}>"


def test_esempio_ancora_presente_nella_pagina(testo_faq):
    """Non basta che il codice si comporti così: l'esempio deve essere ancora
    sulla pagina. Toglierlo e lasciare la conclusione sarebbe l'overclaim."""
    assert "{{NAME_1}}> <{{EMAIL_1}}>" not in testo_faq  # forma sbagliata
    assert ATTESO_8 in testo_faq


def test_la_pagina_dice_cosa_si_e_perso(testo_faq):
    """Il pezzo che e' facile dimenticare di scrivere.

    La numerazione fa uscire una cosa che prima non usciva: quante persone
    distinte ci sono e dove compare ciascuna. Se un domani qualcuno
    accorcia la domanda 8 e lascia solo la parte comoda -- «non esiste
    nessuna mappa» -- la pagina torna a promettere piu' del vero.
    """
    for pezzo in ("Cosa si è perso", "dentro un documento*, si può"):
        assert pezzo in testo_faq, pezzo


def test_due_passaggi_stesso_risultato():
    """La stessa domanda 8 promette che due conversioni dello stesso file
    danno lo stesso risultato: nessuno stato che si accumula."""
    testo = "Dott. Nazzareno Sbrolli, IBAN IT60X0542811101000000123456"
    primo, r1 = apply_privacy_filter(testo, PrivacyOptions())
    secondo, r2 = apply_privacy_filter(testo, PrivacyOptions())
    assert primo == secondo
    assert r1.total == r2.total


def test_il_verbale_resta_a_zero_esatto(testo_faq):
    """La domanda 6 dice «zero», non «quasi zero», e cita l'asserzione dei
    test. Se un giorno quel test si ammorbidisse, questa pagina mentirebbe."""
    assert "report.total == 0" in testo_faq
    banco = Path(__file__).with_name("test_privacy.py").read_text(encoding="utf-8")
    assert "assert report.total == 0" in banco


def test_numerazione_senza_buchi(testo_faq):
    """Rinumerare a mano dopo un inserimento è il modo classico di lasciare
    due domande con lo stesso numero."""
    numeri = [int(n) for n in re.findall(r"^## (\d+)\.", testo_faq, re.MULTILINE)]
    assert numeri == list(range(1, len(numeri) + 1))
    assert len(numeri) >= 11


def test_conteggio_dichiarato_corrisponde(testo_faq):
    """«Undici domande» in cima, e undici domande sotto."""
    numeri = re.findall(r"^## (\d+)\.", testo_faq, re.MULTILINE)
    parole = {10: "Dieci", 11: "Undici", 12: "Dodici", 13: "Tredici"}
    assert parole[len(numeri)].lower() in testo_faq[:400].lower()


@pytest.mark.parametrize(
    "simbolo",
    ["apply_privacy_filter", "find_suspects", "cf_ocr_recover", "iban_ocr_recover"],
)
def test_la_mappa_per_reviewer_punta_a_codice_esistente(testo_faq, simbolo):
    """La domanda 10 è una mappa. Una mappa che nomina una funzione che non
    esiste scredita tutto il resto della pagina."""
    assert simbolo in testo_faq
    sorgente = Path(__file__).resolve().parents[1] / "mr_rao" / "privacy.py"
    assert f"def {simbolo}" in sorgente.read_text(encoding="utf-8")
