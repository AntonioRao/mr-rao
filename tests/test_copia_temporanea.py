# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""La copia di lavoro, quando la cancellazione non riesce.

`convert_bytes` scrive i byte caricati in un file temporaneo, converte, e
cancella. Il documento in chiaro sta su disco per il tempo della conversione, e
non c'e' modo di evitarlo: le librerie di conversione vogliono un percorso.

Il difetto stava nella riga dopo. La rimozione era avvolta in un `try/except`
che **non diceva niente**: file aperto da un antivirus, cartella temporanea
piena, permessi cambiati — e il documento in chiaro restava li' per sempre,
in una cartella condivisa da ogni programma dell'utente, senza che nessuno lo
sapesse.

Cosa si promette, e cosa no
---------------------------

Non si promette la cancellazione sicura: sovrascrivere un file non garantisce
che i byte spariscano da un disco a stato solido, dove il livellamento
dell'usura decide per conto suo, ne' da un filesystem che tiene un giornale.
Promettere il contrario sarebbe la bugia peggiore in questo programma.

Si promette due cose piu' piccole e vere:

* se la cancellazione fallisce, il file che resta **non contiene piu' il
  documento**: viene sovrascritto prima;
* il fallimento **si dice**, invece di essere ingoiato.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import os
from pathlib import Path

from mr_rao.converter import ConvertOptions, convert_bytes

DENTRO = "Il cliente Mario Rossi, codice fiscale RSSMRA85M01H501Z.".encode("utf-8")


def test_quando_non_si_riesce_a_cancellare_il_file_resta_ma_e_vuoto(monkeypatch, caplog):
    """Il caso vero: `os.remove` fallisce e il documento non deve restare."""
    import mr_rao.converter as modulo

    visti: list[str] = []
    remove_vero = os.remove

    def remove_che_fallisce(percorso, *a, **kw):
        visti.append(str(percorso))
        raise OSError(13, "in uso da un altro processo")

    monkeypatch.setattr(modulo.os, "remove", remove_che_fallisce)

    esito = convert_bytes(DENTRO, "nota.txt", options=ConvertOptions())
    assert not esito.error, esito.error
    assert visti, "il codice non ha nemmeno provato a cancellare"

    rimasto = Path(visti[0])
    try:
        assert rimasto.exists(), "il banco non prova niente se il file non c'e'"
        contenuto = rimasto.read_bytes()
        assert b"Mario Rossi" not in contenuto, contenuto[:120]
        assert b"RSSMRA85M01H501Z" not in contenuto, contenuto[:120]
    finally:
        try:
            remove_vero(rimasto)
        except OSError:
            pass


def test_il_fallimento_finisce_nel_registro(monkeypatch, caplog):
    """Ingoiato in silenzio, non sarebbe successo per nessuno."""
    import logging

    import mr_rao.converter as modulo

    percorsi: list[str] = []
    remove_vero = os.remove

    def remove_che_fallisce(percorso, *a, **kw):
        percorsi.append(str(percorso))
        raise OSError(13, "in uso da un altro processo")

    monkeypatch.setattr(modulo.os, "remove", remove_che_fallisce)

    with caplog.at_level(logging.WARNING):
        convert_bytes(DENTRO, "nota.txt", options=ConvertOptions())

    assert caplog.records, "il fallimento non e' stato registrato"
    for p in percorsi:
        try:
            remove_vero(p)
        except OSError:
            pass


def test_nel_caso_normale_il_file_sparisce():
    """La riga che tiene: quando si puo' cancellare, si cancella.

    Senza, i due casi qui sopra sarebbero verdi anche con una funzione che si
    limita a svuotare i file e li lascia tutti sul disco.
    """
    visti: list[str] = []
    import mr_rao.converter as modulo

    remove_vero = modulo.os.remove

    def remove_che_annota(percorso, *a, **kw):
        visti.append(str(percorso))
        return remove_vero(percorso, *a, **kw)

    modulo.os.remove = remove_che_annota
    try:
        convert_bytes(DENTRO, "nota.txt", options=ConvertOptions())
    finally:
        modulo.os.remove = remove_vero

    assert visti, "nessuna cancellazione tentata"
    for p in visti:
        assert not Path(p).exists(), f"il file di lavoro e' rimasto: {p}"
