# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il motore, tutto insieme, confrontato con un risultato congelato.

I test per singolo riconoscitore dicono che ognuno funziona. Non dicono che
**la sequenza** funziona: l'ordine conta — i segreti per primi, gli URL prima
delle email, i codici prima dei telefoni, i nomi per ultimi — e un
riconoscitore puo' rovinare il lavoro di quello dopo senza che nessun test
per-riconoscitore se ne accorga.

Serve alla fase 1 di #1: separare il nucleo universale dai riconoscitori
italiani **senza cambiare un solo comportamento**. Un test che conta le
sostituzioni non basterebbe — si arriva allo stesso numero sostituendo cose
diverse. Qui si confronta il testo prodotto carattere per carattere.

**Questo file congela il comportamento, non lo approva.** L'atteso contiene
anche i difetti noti: per esempio l'email offuscata che si mangia la parola
dopo il ritorno a capo (#3). E' giusto cosi': un golden serve a dire «e'
cambiato qualcosa», non «e' tutto corretto». Quando #3 verra' corretto,
l'atteso si rigenera e il diff mostrera' esattamente cosa e' cambiato.

Per rigenerare: `venv\\Scripts\\python scripts\\rigenera_golden.py`
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter

DATI = Path(__file__).resolve().parent / "dati"
CORPUS = DATI / "corpus_privacy.txt"
ATTESO = DATI / "golden_privacy.json"


@pytest.fixture(scope="module")
def atteso() -> dict:
    return json.loads(ATTESO.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ottenuto() -> dict:
    testo = CORPUS.read_text(encoding="utf-8")
    out, rep = apply_privacy_filter(testo, PrivacyOptions(dates=True, amounts=True))
    return {
        "uscita": out,
        "totale": rep.total,
        "conteggi": dict(sorted(rep.counts.items())),
        "sospetti": [dict(sorted(s.items())) for s in rep.suspects],
    }


def test_i_file_del_banco_esistono():
    """Senza corpus o senza atteso gli altri test passerebbero a vuoto."""
    assert CORPUS.is_file(), f"manca {CORPUS}"
    assert ATTESO.is_file(), f"manca {ATTESO}: rigenera con scripts/rigenera_golden.py"


def test_il_corpus_esercita_tutti_i_riconoscitori(atteso):
    """Un golden su un corpus povero congela il nulla.

    Se domani si aggiunge un riconoscitore e non entra nel corpus, questo
    test non se ne accorge da solo -- ma almeno garantisce che quelli di
    oggi ci siano tutti.
    """
    attesi = {
        "addresses", "amounts", "bban", "cards", "codice_fiscale", "dates",
        "emails", "iban", "names", "partita_iva", "phones", "secrets", "urls",
    }
    mancanti = attesi - set(atteso["conteggi"])
    assert not mancanti, f"il corpus non esercita piu': {sorted(mancanti)}"
    assert atteso["sospetti"], "il corpus deve produrre almeno un sospetto"


def test_il_testo_prodotto_e_identico(ottenuto, atteso):
    """Il confronto che conta: carattere per carattere."""
    if ottenuto["uscita"] != atteso["uscita"]:
        # Il diff riga per riga: un assert su duemila caratteri non si legge.
        import difflib

        differenze = "\n".join(
            difflib.unified_diff(
                atteso["uscita"].splitlines(),
                ottenuto["uscita"].splitlines(),
                fromfile="atteso",
                tofile="ottenuto",
                lineterm="",
            )
        )
        pytest.fail(
            "il motore produce un testo diverso da quello congelato.\n"
            "Se il cambiamento e' voluto: scripts/rigenera_golden.py, e "
            "guarda il diff prima di committarlo.\n\n" + differenze
        )


def test_i_conteggi_sono_identici(ottenuto, atteso):
    assert ottenuto["conteggi"] == atteso["conteggi"]
    assert ottenuto["totale"] == atteso["totale"]


def test_i_sospetti_sono_identici(ottenuto, atteso):
    """Anche i sospetti fanno parte del comportamento: un riconoscitore che
    smette di segnalare e' un peggioramento silenzioso."""
    assert ottenuto["sospetti"] == atteso["sospetti"]
