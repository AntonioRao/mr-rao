# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il richiamo non deve poter scendere in silenzio.

Tutti gli altri banchi contano gli **errori** su documenti che non
contengono niente. E' la meta' giusta da guardare per prima, ma e' una
meta': se domani una modifica facesse smettere il motore di vedere
«piazza G. Verdi, 1», quei banchi resterebbero tutti verdi. Zero errori su
un documento vuoto e' anche il risultato di un motore spento.

Qui si guarda l'altra meta', sui documenti **che non abbiamo scritto noi** —
Gazzette Ufficiali e moduli scaricati dagli enti che li pubblicano. Sono
loro ad aver trovato i 41 indirizzi della 1.16.0 e i 107 cognomi della
1.17.0, e nessun banco fatto in casa li avrebbe trovati: un corpus scritto
da noi contiene solo le trappole a cui abbiamo pensato.

Il corpus non sta nel repository — decine di megabyte, e non sono nostri da
ridistribuire. Il primo test si salta dicendolo. Gli altri tre no: provano
il **meccanismo**, cioe' che il banco sappia dire di no in tutt'e tre i modi
in cui deve saperlo. Un controllo che gira solo sulla macchina di chi
sviluppa non e' un controllo, e uno che non puo' fallire non e' una
verifica.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
for percorso in (RADICE, RADICE / "scripts"):
    if str(percorso) not in sys.path:
        sys.path.insert(0, str(percorso))

import json  # noqa: E402

from bench_corpus_pubblico import (  # noqa: E402
    ATTESO,
    confronta,
    misura,
    trova_corpus,
)


def _atteso() -> dict:
    return json.loads(ATTESO.read_text(encoding="utf-8"))


def test_sui_documenti_veri_il_motore_non_prende_meno_di_prima():
    """Il banco vero, quando il corpus c'e'."""
    cartella = trova_corpus(None)
    if cartella is None:
        pytest.skip(
            "corpus pubblico assente: MRRAO_CORPUS=CARTELLA per esercitarlo "
            "(i documenti non stanno nel repository, vedi il docstring di "
            "scripts/bench_corpus_pubblico.py)"
        )
    guasti = confronta(_atteso(), misura(cartella))
    assert not guasti, "\n  ".join(["il corpus pubblico segnala:"] + guasti)


def test_si_accorge_quando_il_motore_prende_meno():
    """La direzione che nessun altro banco guarda."""
    atteso = _atteso()
    peggiorato = json.loads(json.dumps(atteso))
    peggiorato["conteggi"]["gu"]["addresses"] = 0
    guasti = confronta(atteso, peggiorato)
    assert any("MENO" in g for g in guasti), guasti


def test_si_accorge_di_una_sostituzione_in_piu_sui_moduli_in_bianco():
    """La soglia sui moduli in bianco non e' piu' «zero» ma «non piu' di
    prima», e va provata nel verso giusto: una in piu' e' un guasto.

    Perche' non e' piu' zero lo spiega `bench_corpus_pubblico.py`: un modulo
    ufficiale porta i recapiti dell'ente che lo pubblica, e alcuni sono
    firmati da una persona vera.
    """
    atteso = _atteso()
    peggiorato = json.loads(json.dumps(atteso))
    categoria = peggiorato["conteggi"]["itmod"]
    categoria["names"] = categoria.get("names", 0) + 1
    guasti = confronta(atteso, peggiorato)
    assert any("PIU'" in g for g in guasti), guasti


def test_una_sostituzione_in_meno_sui_moduli_in_bianco_non_e_un_guasto():
    """Il verso opposto, ed e' quello che rende utile il ratchet: togliere
    un falso positivo deve poter passare senza rigenerare niente,
    altrimenti ogni correzione richiede prima di aggiornare l'atteso e la
    tentazione e' di aggiornarlo senza guardarlo."""
    atteso = _atteso()
    migliorato = json.loads(json.dumps(atteso))
    migliorato["conteggi"]["itmod"] = {}
    assert confronta(atteso, migliorato) == []


def test_un_corpus_diverso_non_viene_scambiato_per_una_regressione():
    """Il modo piu' probabile di leggere male questo banco.

    Puntato a una cartella diversa da quella con cui i numeri sono stati
    congelati, ogni conteggio sarebbe diverso — e sembrerebbe una
    regressione grossa invece che un errore di puntamento. L'impronta
    dell'elenco dei file distingue le due cose e lo dice.
    """
    atteso = _atteso()
    altro = json.loads(json.dumps(atteso))
    altro["impronta"] = "0000000000000000"
    guasti = confronta(atteso, altro)
    assert len(guasti) == 1 and "corpus diverso" in guasti[0], guasti
