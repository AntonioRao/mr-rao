# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Le voci minori dell'audit del 6 settembre 2026.

Piccole per conto loro, e nessuna e' una fuga di dati. Stanno insieme perche'
hanno in comune il modo di sbagliare: **una risposta che non aiuta chi la
riceve**. Un 500 al posto di un «questo file non si legge», un errore che
finisce su una console che nel prodotto non c'e', un link protocollo-relativo
in un'anteprima, un file sovrascritto senza dirlo.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

BASE = "http://127.0.0.1:5000"


def _client():
    from mr_rao.app_factory import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


# ------------------------------------------------- un PDF che non si apre


def test_un_pdf_illeggibile_non_diventa_un_errore_del_server():
    """Un file storto e' colpa del file, e la risposta deve dirlo.

    `_pagina_in_png` sollevava su un PDF senza pagine, e il chiamante non lo
    prendeva: usciva un 500, cioe' «si e' rotto il programma», per un documento
    che semplicemente non si puo' aprire. Chi lo riceve non ha modo di capire
    che deve cambiare file.
    """
    finto = b"%PDF-1.4\n%%EOF\n"
    r = _client().post("/api/pdf/anteprima", base_url=BASE, data={
        "file": (io.BytesIO(finto), "rotto.pdf"),
        "lang": "it",
    }, content_type="multipart/form-data")
    assert r.status_code != 500, r.data[:300]
    assert 400 <= r.status_code < 500, r.status_code
    assert (r.get_json() or {}).get("error"), r.data[:200]


# ------------------------------------- gli errori del worker vanno nel registro


def test_il_lavoro_fallito_non_scrive_su_una_console_che_non_c_e():
    """`print()` in un programma senza finestra di console non arriva a nessuno.

    Nel portable e nell'eseguibile con icona nel vassoio non c'e' nessuno
    stdout: quel messaggio si perdeva, ed era l'unica traccia di un lavoro
    andato storto. Nel registro invece resta.
    """
    sorgente = Path("mr_rao/routes.py").read_text(encoding="utf-8")
    assert "print(f\"job" not in sorgente, (
        "l'errore del lavoro va nel registro, non su stdout"
    )
    assert "crashed" in sorgente, "il messaggio d'errore e' sparito del tutto"


# ------------------------------------------- i link dell'anteprima .docx


def test_un_indirizzo_senza_schema_non_passa_per_relativo():
    """`//host/x` non e' un percorso relativo: e' un altro sito.

    Si chiama protocollo-relativo, e un lettore lo apre con lo schema della
    pagina. Nel controllo cadeva nel ramo «comincia per /», quindi passava
    insieme a `/pagina` e `#ancora`, che invece non portano da nessuna parte.
    Non esegue codice — quindi non e' un buco di esecuzione — ma e' una
    navigazione fuori dal documento che l'utente non si aspetta da un'anteprima
    che gira in locale.
    """
    from mr_rao.docx_export import _indirizzo_innocuo

    assert not _indirizzo_innocuo("//esempio.invalido/pagina")
    assert not _indirizzo_innocuo("/\\/esempio.invalido")
    # E le tre forme che devono continuare a passare.
    assert _indirizzo_innocuo("#nota")
    assert _indirizzo_innocuo("/pagina/interna")
    assert _indirizzo_innocuo("https://esempio.invalido/x")


# --------------------------------------------- la riga di comando che sovrascrive


def test_la_riga_di_comando_non_sovrascrive_in_silenzio(tmp_path, capsys):
    """Un `.md` gia' li' viene sostituito senza una parola.

    E' il caso di chi converte due volte la stessa cartella con opzioni
    diverse: il secondo giro cancella il primo. La cartella sorvegliata non lo
    fa da versioni (`output_path_for` numera invece di sovrascrivere), la riga
    di comando si'.
    """
    from mr_rao.cli import main

    sorgente = tmp_path / "nota.txt"
    sorgente.write_text("Una riga qualunque.", encoding="utf-8")
    uscita = tmp_path / "nota.md"
    uscita.write_text("IL MIO LAVORO DI IERI", encoding="utf-8")

    codice = main(["convert", str(sorgente)])
    assert codice == 0
    detto = capsys.readouterr().out

    if uscita.read_text(encoding="utf-8") == "IL MIO LAVORO DI IERI":
        # Non sovrascritto: allora il file nuovo sta altrove e va detto dove.
        assert list(tmp_path.glob("nota-*.md")), "il documento non e' stato scritto"
    else:
        # Sovrascritto: dev'esserci un avviso che lo dice.
        assert "sovrascr" in detto.lower() or "esist" in detto.lower(), detto
