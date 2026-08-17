# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il motore OCR vero, non una sua imitazione.

Tutti gli altri test sostituiscono `ocr_image` con una funzione che
restituisce testo finto: servono a provare cosa fa il convertitore *dato* un
testo, e per quello vanno benissimo. Ma vuol dire che la suite intera resta
verde anche se il motore OCR non funziona affatto.

Non e' teoria. Passando da `rapidocr_onnxruntime` 1.2.3 a `rapidocr` 3.x il
valore restituito ha cambiato forma -- da tupla ``(result, elapse)`` a
oggetto ``RapidOCROutput`` -- e le due righe che lo usavano alzavano
``TypeError``. I 693 test passavano lo stesso.

Questo file costa un paio di secondi e copre quel buco: fa leggere al motore
vero un'immagine costruita qui, con testo noto.
"""
from __future__ import annotations

import pytest

pytest.importorskip("rapidocr", reason="motore OCR non installato")
pytest.importorskip("onnxruntime", reason="onnxruntime non installato")
PIL = pytest.importorskip("PIL")


def _immagine_con_testo(percorso, righe: list[str]) -> None:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1100, 60 + 55 * len(righe)), (252, 252, 250))
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("arial.ttf", 30)
    except OSError:  # pragma: no cover — su Linux il carattere e' un altro
        f = ImageFont.load_default()
    for i, riga in enumerate(righe):
        d.text((20, 20 + 55 * i), riga, font=f, fill=(0, 0, 0))
    img.save(str(percorso))


def test_il_motore_ocr_legge_davvero(tmp_path):
    """Prova di vita del motore, senza sostituti."""
    from mr_rao.ocr_service import ocr_image

    p = tmp_path / "scansione.png"
    _immagine_con_testo(p, ["Codice fiscale RSSMRA80A01H501U"])

    testo = ocr_image(str(p))

    assert testo, "il motore OCR non ha restituito niente"
    # Non si pretende la lettura perfetta -- e' pur sempre OCR -- ma la parola
    # piu' facile della riga dev'esserci, altrimenti non ha letto l'immagine.
    assert "fiscale" in testo.lower()


def test_gli_spazi_fra_le_parole_sopravvivono(tmp_path):
    """Il motore deve separare le parole, non incollarle.

    E' il difetto che ha motivato il passaggio alla 3.x: la 1.2.3 leggeva
    `PartitaIVA12345678903-tel.+390951234567` tutto attaccato, e su quel
    testo i riconoscitori trovavano **un** dato personale invece di tre --
    partita IVA e telefono restavano in chiaro nel documento consegnato.
    """
    from mr_rao.ocr_service import ocr_image

    p = tmp_path / "fattura.png"
    _immagine_con_testo(p, ["Partita IVA 12345678903 - tel. 095 123 4567"])

    testo = (ocr_image(str(p)) or "").lower()

    assert "partita iva" in testo, f"parole incollate fra loro: {testo!r}"


def test_il_motore_non_stampa_il_percorso_dei_modelli(tmp_path, capfd):
    """Nessun rumore in console, e soprattutto nessun percorso utente.

    La 3.x, appena costruita, scriveva nove righe di INFO col percorso
    completo dei modelli -- che su Windows contiene il nome dell'utente. Su
    uno strumento che esiste per non far uscire i dati, l'output di console
    incollato in una segnalazione non deve dire chi sei.
    """
    from mr_rao import ocr_service

    ocr_service._ocr = None  # forza la costruzione, che e' quando parlava
    p = tmp_path / "x.png"
    _immagine_con_testo(p, ["prova"])
    ocr_service.ocr_image(str(p))

    fuori, errori = capfd.readouterr()
    assert "models" not in (fuori + errori).lower(), (
        "il motore sta ancora stampando i percorsi dei modelli"
    )
