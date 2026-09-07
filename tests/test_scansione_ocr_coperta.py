# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Sopra una scansione con strato OCR: **coprire i pixel**, non arrendersi.

## Da dove arriva

Dalla 1.29.0 una pagina fatta di immagine piu' testo OCR invisibile veniva
**rifiutata**: togliere i glifi invisibili non e' una redazione, perche' il
dato resta nei pixel, e dichiararla trattata sarebbe stato falso. Il rifiuto
era la risposta onesta, e restava una risposta scarsa: l'utente aveva in mano
un documento e nessun modo di trattarlo.

Confrontando con `rizzo-pii` il 7 settembre 2026 e' saltata fuori la risposta
migliore, che loro danno gia': lo strato OCR **sa dove sono le parole** — e'
il suo mestiere, sta li' apposta perche' il testo si possa selezionare sopra
l'immagine. Quelle coordinate sono la mappa dei pixel da coprire. Si toglie il
testo invisibile **e** si dipinge il rettangolo sopra l'immagine.

## Il limite, che va dichiarato e non nascosto

Il rettangolo sta dove lo strato OCR dice che sta la parola. Se quello strato
e' disallineato rispetto all'immagine — capita, e non c'e' modo di accorgersene
dal file — il rettangolo copre i pixel sbagliati e il dato resta visibile
accanto. Per questo la pagina finisce in `pagine_coperte_sull_ocr`: **non e'
una pagina come le altre**, e chi consegna il documento deve guardarla.

E' la stessa forma di `pagine_riquadro_sopra`: si fa la cosa utile e si dice
a voce alta cosa non si e' potuto garantire.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import zlib

import pytest

pikepdf = pytest.importorskip("pikepdf")
pdfium = pytest.importorskip("pypdfium2")

from mr_rao.privacy import PrivacyOptions  # noqa: E402
from mr_rao.redazione_pdf import redigi_pdf  # noqa: E402

CF = "RSSMRA85M01H501Z"
#: Il grigio uniforme del finto foglio scansionato. Serve chiaro: dopo la
#: redazione i pixel dentro il riquadro devono essere di un altro colore, e
#: con un fondo bianco non si distinguerebbe da una pagina qualunque.
GRIGIO = 200


def _pagina(pdf, righe: list[str], invisibile: bool, con_immagine: bool):
    font = pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Font"), Subtype=pikepdf.Name("/Type1"),
        BaseFont=pikepdf.Name("/Helvetica"),
        Encoding=pikepdf.Name("/WinAnsiEncoding")))
    risorse = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
    comandi: list[str] = []
    if con_immagine:
        larghezza, altezza = 40, 56
        immagine = pdf.make_stream(zlib.compress(bytes([GRIGIO]) * (larghezza * altezza)))
        immagine.Type = pikepdf.Name("/XObject")
        immagine.Subtype = pikepdf.Name("/Image")
        immagine.Width, immagine.Height = larghezza, altezza
        immagine.ColorSpace = pikepdf.Name("/DeviceGray")
        immagine.BitsPerComponent = 8
        immagine.Filter = pikepdf.Name("/FlateDecode")
        risorse["/XObject"] = pikepdf.Dictionary(Im0=immagine)
        comandi += ["q", "595 0 0 842 0 0 cm", "/Im0 Do", "Q"]
    comandi += ["BT", "/F1 11 Tf"]
    if invisibile:
        comandi.append("3 Tr")     # come lo mette ogni motore OCR
    y = 760
    for riga in righe:
        comandi.append(f"1 0 0 1 60 {y} Tm ({riga}) Tj")
        y -= 18
    comandi.append("ET")
    pdf.pages.append(pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=risorse,
        Contents=pdf.make_stream("\n".join(comandi).encode("latin-1"))))))


def _scansione_con_ocr(percorso, righe):
    pdf = pikepdf.Pdf.new()
    _pagina(pdf, righe, invisibile=True, con_immagine=True)
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _pagina_digitale(percorso, righe):
    pdf = pikepdf.Pdf.new()
    _pagina(pdf, righe, invisibile=False, con_immagine=False)
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _colori_della_pagina(percorso) -> set[tuple[int, int, int]]:
    """I colori che si vedono davvero aprendo la pagina."""
    documento = pdfium.PdfDocument(str(percorso))
    try:
        immagine = documento[0].render(scale=1).to_pil().convert("RGB")
        return set(immagine.getdata())
    finally:
        documento.close()


def _dove_sta(percorso, valore: str) -> tuple[float, float, float, float]:
    """Il riquadro del valore secondo **pdfium**, non secondo Mr. Rao.

    Si chiede al motore PDF e non alla nostra `riquadri_dei_valori`: quella e'
    la funzione sotto esame, e usarla qui vorrebbe dire misurare la copertura
    con lo stesso righello che l'ha disegnata.
    """
    documento = pdfium.PdfDocument(str(percorso))
    try:
        testo = documento[0].get_textpage()
        try:
            contenuto = testo.get_text_range()
            inizio = contenuto.index(valore)
            riquadri = [testo.get_charbox(k) for k in range(inizio, inizio + len(valore))]
        finally:
            testo.close()
    finally:
        documento.close()
    return (min(r[0] for r in riquadri), min(r[1] for r in riquadri),
            max(r[2] for r in riquadri), max(r[3] for r in riquadri))


def _pixel(percorso, x: float, y: float, scala: float = 2.0):
    """Il colore del punto (x, y) dello **spazio pagina**, come si vede."""
    documento = pdfium.PdfDocument(str(percorso))
    try:
        pagina = documento[0]
        altezza = pagina.get_height()
        immagine = pagina.render(scale=scala).to_pil().convert("RGB")
        return immagine.getpixel((int(x * scala), int((altezza - y) * scala)))
    finally:
        documento.close()


def test_la_pagina_ocr_non_viene_piu_rifiutata(tmp_path):
    """Prima usciva `scansione=True` e nessun byte toccato."""
    dentro = _scansione_con_ocr(tmp_path / "dentro.pdf",
                                [f"Il contribuente C.F. {CF} dichiara."])
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    assert not esito.scansione, "la pagina si puo' trattare: non e' piu' un rifiuto"
    assert esito.pagine_in_ripiego == [], f"pagina non trattata: {esito.motivi_ripiego}"
    assert esito.glifi_rimossi > 0, "lo strato OCR invisibile va tolto lo stesso"


def test_i_pixel_sotto_il_dato_vengono_coperti(tmp_path):
    """**La prova che conta.** Non basta togliere il testo invisibile.

    Si guarda la pagina come la vede chi la apre, nel punto esatto in cui il
    motore PDF dice che stava il codice fiscale: li' non ci deve essere piu' il
    grigio del foglio scansionato.
    """
    dentro = _scansione_con_ocr(tmp_path / "dentro.pdf",
                                [f"Il contribuente C.F. {CF} dichiara."])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())

    assert _colori_della_pagina(dentro) == {(GRIGIO, GRIGIO, GRIGIO)}, (
        "il foglio di partenza doveva essere grigio uniforme")

    sinistra, basso, destra, alto = _dove_sta(dentro, CF)
    # Tre punti dentro il riquadro: l'inizio, il centro e la fine. Il solo
    # centro passerebbe anche con un rettangolo troppo corto, che e'
    # esattamente il modo in cui questa copertura puo' sbagliare.
    for quota, dove in ((0.1, "inizio"), (0.5, "centro"), (0.9, "fine")):
        x = sinistra + (destra - sinistra) * quota
        y = (basso + alto) / 2
        colore = _pixel(fuori, x, y)
        assert colore != (GRIGIO, GRIGIO, GRIGIO), (
            f"i pixel della scansione sono ancora scoperti all'{dove} del valore "
            f"({x:.1f}, {y:.1f}): {colore}")

    # E la riga che impedisce di «coprire» tutta la pagina: un punto lontano
    # dal dato deve restare il foglio di prima.
    assert _pixel(fuori, sinistra, basso - 60) == (GRIGIO, GRIGIO, GRIGIO), (
        "coperto anche dove non c'era niente: cosi' il documento e' illeggibile")


def test_un_valore_piu_lungo_del_segnaposto_resta_coperto_fino_in_fondo(tmp_path):
    """Il riquadro si misura sul **valore**, non sul segnaposto che lo sostituisce.

    Trovato da una mutazione: coprendo con il solo riquadro del segnaposto il
    banco restava verde, perche' `{{CODICE_FISCALE_1}}` e' piu' lungo di un
    codice fiscale e il riquadro finiva per avanzare. Con un nome lungo si
    capovolge — `{{NAME_1}}` sono dieci caratteri contro trentasei — e meta'
    del nome resterebbe leggibile nei pixel, sotto un rettangolo che sembra
    aver fatto il suo lavoro.
    """
    nome = "Massimiliano Bartolomeo Della Rovere"
    dentro = _scansione_con_ocr(tmp_path / "dentro.pdf",
                                [f"Il sottoscritto {nome} dichiara."])
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())
    assert esito.pagine_coperte_sull_ocr == [0], f"pagina non coperta: {esito}"

    sinistra, basso, destra, alto = _dove_sta(dentro, nome)
    y = (basso + alto) / 2
    for quota, dove in ((0.1, "inizio"), (0.5, "centro"), (0.95, "coda")):
        x = sinistra + (destra - sinistra) * quota
        colore = _pixel(fuori, x, y)
        assert colore != (GRIGIO, GRIGIO, GRIGIO), (
            f"pixel scoperti alla {dove} del nome ({x:.1f}, {y:.1f}): {colore}")


def test_la_pagina_coperta_sull_ocr_si_dichiara(tmp_path):
    """Il rettangolo sta dove lo dice lo strato OCR, non dove sono i pixel.

    Sono la stessa cosa quasi sempre e non per definizione: la pagina va
    nominata, o chi consegna il documento non sa che deve guardarla.
    """
    dentro = _scansione_con_ocr(tmp_path / "dentro.pdf",
                                [f"Il contribuente C.F. {CF} dichiara."])
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    assert esito.pagine_coperte_sull_ocr == [0], (
        f"la pagina non e' dichiarata coperta sull'OCR: {esito.pagine_coperte_sull_ocr}")


def test_una_pagina_digitale_non_finisce_fra_quelle_coperte(tmp_path):
    """La riga che impedisce di «correggere» dichiarando tutto sospetto.

    Se l'avviso comparisse su ogni pagina non direbbe piu' niente: e' un
    avviso proprio perche' riguarda poche pagine.
    """
    dentro = _pagina_digitale(tmp_path / "dentro.pdf",
                              [f"Il contribuente C.F. {CF} dichiara."])
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    assert esito.pagine_coperte_sull_ocr == []
    assert esito.glifi_rimossi > 0, "la pagina normale va comunque redatta"
