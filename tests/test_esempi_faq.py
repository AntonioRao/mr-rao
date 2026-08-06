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


def test_i_segnaposto_non_sono_numerati():
    """La domanda 8 ci costruisce sopra due conclusioni: che l'uscita non si
    possa ricollegare, e che non esista nessuna mappa da custodire."""
    testo = "Scrivi a Mario Rossi <m.rossi@a.it> e a Luigi Bianchi <l.bianchi@b.it>"
    atteso = "Scrivi a {{NAME}} <{{EMAIL}}> e a {{NAME}} <{{EMAIL}}>"
    risultato, _ = apply_privacy_filter(testo, PrivacyOptions())
    assert risultato == atteso


def test_esempio_ancora_presente_nella_pagina(testo_faq):
    """Non basta che il codice si comporti così: l'esempio deve essere ancora
    sulla pagina. Toglierlo e lasciare la conclusione sarebbe l'overclaim."""
    assert "{{NAME}}> <{{EMAIL}}>" not in testo_faq  # forma sbagliata
    assert "Scrivi a {{NAME}} <{{EMAIL}}> e a {{NAME}} <{{EMAIL}}>" in testo_faq


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
