# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""La cartella sorvegliata non puo' essere anche la cartella di uscita.

Il difetto
----------

`.md` e' un formato **d'ingresso** ammesso: si converte un Markdown in un
Markdown redatto, ed e' un caso vero. Ma la cartella sorvegliata produce `.md`,
e se le due cartelle coincidono ogni file prodotto e' un file nuovo da
convertire: si converte, produce `nota-md.md`, che viene visto, convertito,
e via cosi'.

Il freno esiste — `output_path_for` non sovrascrive mai e aggiunge un suffisso
— ma frena il **danno**, non il ciclo: la cartella si riempie di documenti
generati finche' qualcuno non se ne accorge. E ogni giro passa il testo dal
motore un'altra volta, su un testo gia' redatto.

Non e' una configurazione da difendere con un avviso: e' una configurazione che
non ha nessun uso sensato, e va rifiutata quando la si chiede — con un
messaggio che dice **cosa fare**, non solo che c'e' un errore.

Vale anche per una cartella di uscita **dentro** quella sorvegliata: il ciclo e'
lo stesso, e la si scrive senza accorgersene («documenti» e
«documenti/redatti»).

Tutti i valori sono inventati.
"""

from __future__ import annotations

import pytest

from mr_rao.watch_service import start_watch, stop_watch


@pytest.fixture(autouse=True)
def _spegni():
    yield
    stop_watch()


def test_stessa_cartella_viene_rifiutata(tmp_path):
    cartella = tmp_path / "documenti"
    cartella.mkdir()
    with pytest.raises(ValueError) as errore:
        start_watch(cartella, cartella)
    # Il messaggio deve dire cosa fare: «errore» da solo non e' un messaggio.
    assert "cartella" in str(errore.value).lower(), errore.value


def test_uscita_dentro_la_sorvegliata_viene_rifiutata(tmp_path):
    """Il caso che si scrive senza accorgersene, ed e' lo stesso ciclo."""
    dentro = tmp_path / "documenti"
    fuori = dentro / "redatti"
    fuori.mkdir(parents=True)
    with pytest.raises(ValueError):
        start_watch(dentro, fuori)


def test_due_cartelle_diverse_partono_come_sempre(tmp_path):
    """La riga che impedisce di «correggere» rifiutando tutto.

    E' la configurazione normale, ed e' quella che il prodotto serve.
    """
    dentro = tmp_path / "in"
    fuori = tmp_path / "out"
    dentro.mkdir()
    fuori.mkdir()
    stato = start_watch(dentro, fuori)
    assert stato.get("running") or stato.get("attiva") or stato, stato


def test_dalla_rotta_e_un_400_con_il_motivo(tmp_path):
    """Non un guasto del programma: una scelta da correggere, e si dice come.

    Un 500 la farebbe sembrare colpa nostra e non direbbe niente a chi la deve
    cambiare.
    """
    from mr_rao.app_factory import create_app

    app = create_app()
    app.config["TESTING"] = True
    cartella = tmp_path / "documenti"
    cartella.mkdir()

    base = "http://127.0.0.1:5000"
    r = app.test_client().post(
        "/api/watch",
        base_url=base,
        headers={"Origin": base},
        json={"inbox": str(cartella), "outbox": str(cartella), "lang": "it"},
    )
    assert r.status_code == 400, (r.status_code, r.data[:200])
    assert "cartella" in (r.get_json() or {}).get("error", "").lower()


def test_la_sorvegliata_dentro_l_uscita_va_bene(tmp_path):
    """Il verso opposto **non** e' un ciclo, e non va rifiutato.

    L'uscita che contiene l'ingresso produce `.md` **fuori** dalla cartella
    guardata: nessun file prodotto viene riletto. Rifiutarlo sarebbe prudenza
    a spese di una configurazione legittima, ed e' il modo in cui una guardia
    diventa un fastidio da aggirare.
    """
    fuori = tmp_path / "tutto"
    dentro = fuori / "da-convertire"
    dentro.mkdir(parents=True)
    stato = start_watch(dentro, fuori)
    assert stato
