"""La pulizia del testo per l'incolla-in-chat, e il suo costo.

`_strip_noise` toglie i commenti HTML e le note che l'applicazione stessa
scrive. Lo faceva con `re.sub(r"<!--.*?-->")`: su un documento pieno di
`<!--` mai chiusi il motore riparte da ogni apertura e arriva ogni volta in
fondo — tempo quadratico sulla lunghezza, con un tetto d'invio di 50 MB e un
documento che sceglie chi lo carica.

Segnalato da CodeQL come py/polynomial-redos. Qui si verificano due cose:
che il risultato non sia cambiato, e che il costo sia sceso davvero.
"""
from __future__ import annotations

import time

import pytest

from mr_rao.converter import _strip_noise, _togli_commenti_html


@pytest.mark.parametrize(
    ("grezzo", "atteso"),
    [
        ("testo\n<!-- Pagina 1 -->\nancora", "testo\nancora"),
        ("<!-- uno --><!-- due -->fine", "fine"),
        ("a\n\n> 🛡️ *3 dati rimossi.*\nb", "a\n\nb"),
        ("> ℹ️ *Testo estratto tramite OCR.*\n\ntesto vero", "testo vero"),
        ("niente da togliere", "niente da togliere"),
        # Multiriga: il commento che l'OCR mette fra una pagina e l'altra
        ("prima\n<!--\nPagina 2\n-->\ndopo", "prima\ndopo"),
    ],
)
def test_pulizia(grezzo, atteso):
    assert _strip_noise(grezzo) == atteso


def test_commento_aperto_e_mai_chiuso_resta():
    """Non è compito nostro indovinare dove finiva."""
    assert _togli_commenti_html("testo <!-- aperto") == "testo <!-- aperto"


def test_marcatore_a_meta_riga_non_viene_toccato():
    """Le note dell'app stanno a inizio riga: ancorare a ^ evita di mangiare
    una citazione che capiti di contenere gli stessi caratteri."""
    testo = "vedi la nota > 🛡️ *cosa* nel documento"
    assert _strip_noise(testo) == testo


def test_costo_lineare_su_input_patologico():
    """La versione con `.*?` impiegava ~3 secondi su questo input, e cresceva
    col quadrato: a 50 MB non sarebbe tornata. Questa sta sotto il millisecondo.

    La soglia è larghissima di proposito — quattro ordini di grandezza sopra
    la misura reale — perché un test che dipende dal carico della macchina
    non serve a nessuno: qui deve distinguere lineare da quadratico, non
    misurare la performance.
    """
    cattivo = "<!--" * 20_000  # 80 mila caratteri, nessuna chiusura
    inizio = time.perf_counter()
    risultato = _togli_commenti_html(cattivo)
    durata = time.perf_counter() - inizio
    assert risultato == cattivo  # niente da chiudere, niente da togliere
    assert durata < 1.0, f"{durata:.2f}s: il costo è tornato quadratico"


def test_costo_lineare_anche_coi_commenti_chiusi():
    cattivo = "<!-- x -->" * 20_000
    inizio = time.perf_counter()
    assert _togli_commenti_html(cattivo) == ""
    assert time.perf_counter() - inizio < 1.0
