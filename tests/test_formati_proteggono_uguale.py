# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Un `.xlsx` deve proteggere quanto un `.docx`.

Perche' questo file esiste
--------------------------

Fino al 2026-08 niente lo verificava. `scripts/verify_build.py` converte un
`.docx`, un `.xlsx` e un `.pptx` e controlla che la conversione **riesca**:
riuscire non vuol dire proteggere. Fra un formato e l'altro cambia
l'estrattore, e se un estrattore manda a capo dentro un IBAN o perde uno
spazio, il dato arriva al motore in una forma che i pattern non
riconoscono. Nessun test guardava.

Il banco vero e' `scripts/bench_formati.py`, che stampa la tabella completa
e ha la sua controprova. Qui si esegue la parte veloce, quella che deve
restare verde a ogni commit.

Il `.png` resta fuori: passa dall'OCR e costa un giro di riconoscimento
immagine. Chi vuole misurarlo lancia lo script con `--con-ocr`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
for percorso in (RADICE, RADICE / "scripts"):
    if str(percorso) not in sys.path:
        sys.path.insert(0, str(percorso))

from bench_formati import (  # noqa: E402
    AGHI,
    ATTESI,
    ATTESO_CONTROLLO,
    RIGHE_CON_DATI,
    RIGHE_DI_CONTROLLO,
    SENZA_OCR,
    misura,
)


@pytest.fixture(scope="module")
def con_dati():
    return misura(RIGHE_CON_DATI, SENZA_OCR)


@pytest.fixture(scope="module")
def di_controllo():
    return misura(RIGHE_DI_CONTROLLO, SENZA_OCR)


def test_nessun_formato_lascia_un_dato_leggibile(con_dati):
    """La domanda che conta: quel valore e' ancora nel documento?

    Si guarda il **testo**, non il conteggio: un formato potrebbe contare
    otto redazioni e avercene lasciato uno diverso in chiaro.
    """
    guasti = {ext: rimasti for ext, _, rimasti in con_dati if rimasti}
    assert not guasti, (
        "questi formati lasciano dati personali leggibili: "
        + "; ".join(f"{e}: {', '.join(r)}" for e, r in guasti.items())
    )


def test_tutti_i_formati_tolgono_lo_stesso_numero(con_dati):
    """Una differenza fra due formati non e' rumore: e' l'estrattore.

    L'`.eml` fa storia a se': porta `From:` e `To:` per costruzione, che
    sono indirizzi veri.
    """
    for ext, totale, _ in con_dati:
        atteso = ATTESI + ATTESO_CONTROLLO.get(ext, 0)
        assert totale == atteso, (
            f"{ext}: {totale} redazioni invece di {atteso}. Se il numero e' "
            f"piu' basso l'estrattore ha rotto un dato; se e' piu' alto ne "
            f"ha inventato uno"
        )


def test_sui_documenti_senza_dati_non_tocca_niente(di_controllo):
    """Il testo di controllo contiene le parole che facevano scattare
    l'euristica ritirata nella 1.13.0: se qualcosa riappare, la regressione
    ha un nome preciso."""
    for ext, totale, _ in di_controllo:
        atteso = ATTESO_CONTROLLO.get(ext, 0)
        assert totale == atteso, (
            f"{ext}: {totale} sostituzioni su un documento che non contiene "
            f"nessun dato personale (attese {atteso})"
        )


def test_il_banco_puo_dire_di_no():
    """Con i riconoscitori spenti tutti gli aghi devono restare leggibili.

    Senza questo, un banco che non applicasse affatto le opzioni resterebbe
    verde per sempre — ed e' successo davvero, perche' `convert_file` prende
    le opzioni come **terzo** argomento e passarle come secondo le fa
    finire nel nome del file, in silenzio.
    """
    spenti = misura(RIGHE_CON_DATI, [".txt", ".docx"], privacy_accesa=False)
    for ext, totale, rimasti in spenti:
        assert totale == 0, f"{ext}: redige {totale} volte col filtro spento"
        assert len(rimasti) == len(AGHI), (
            f"{ext}: col filtro spento restano solo {len(rimasti)} aghi su "
            f"{len(AGHI)} — il banco non li sta cercando tutti"
        )
