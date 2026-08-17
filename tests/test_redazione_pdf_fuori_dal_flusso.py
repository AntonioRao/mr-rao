# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il testo di un PDF che **non sta nel flusso della pagina**.

La chirurgia sui glifi taglia il contenuto della pagina, ed era tutto quello
che il modulo faceva. In un PDF vero i dati personali stanno anche altrove:

* nel testo di una **nota** e nel valore di un **campo modulo**, che sono
  stringhe appese all'annotazione — il file usciva chiamandosi `-redatto.pdf`
  con dentro un codice fiscale leggibile aprendolo con un editor di testo;
* in una **pagina scansionata** infilata fra pagine digitali, che non ha
  glifi da tagliare e prendeva la stessa strada di una pagina senza niente da
  togliere: usciva contata fra quelle trattate.

Erano limiti dichiarati nel docstring del modulo, e finche' la redazione si
faceva da riga di comando potevano bastare. Da quando c'e' un pulsante
nell'interfaccia non bastano piu': li' l'unica frase che si legge e' «Tutte
le pagine sono state trattate».

Tutti i valori sono inventati.
"""

from __future__ import annotations

import pytest

pikepdf = pytest.importorskip("pikepdf")
pytest.importorskip("pypdfium2")

from mr_rao import redazione_pdf as motore_pdf  # noqa: E402
from mr_rao.privacy import PrivacyOptions  # noqa: E402
from mr_rao.redazione_pdf import redigi_pdf, verifica_redazione  # noqa: E402

ELVETICO = pikepdf.Dictionary(
    Type=pikepdf.Name("/Font"), Subtype=pikepdf.Name("/Type1"),
    BaseFont=pikepdf.Name("/Helvetica"),
    Encoding=pikepdf.Name("/WinAnsiEncoding"))


def _pagina_con_testo(pdf, riga: str):
    font = pdf.make_indirect(pikepdf.Dictionary(ELVETICO))
    comandi = f"BT /F1 11 Tf 1 0 0 1 60 760 Tm ({riga}) Tj ET"
    return pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)),
        Contents=pdf.make_stream(comandi.encode("latin-1")))))


def _pagina_vuota(pdf, con_immagine: bool):
    risorse = pikepdf.Dictionary()
    if con_immagine:
        immagine = pdf.make_stream(bytes([255, 0, 0] * 4))
        immagine.Type = pikepdf.Name("/XObject")
        immagine.Subtype = pikepdf.Name("/Image")
        immagine.Width, immagine.Height = 2, 2
        immagine.ColorSpace = pikepdf.Name("/DeviceRGB")
        immagine.BitsPerComponent = 8
        risorse.XObject = pikepdf.Dictionary(Im0=pdf.make_indirect(immagine))
    return pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=risorse,
        Contents=pdf.make_stream(b""))))


# ------------------------------------------------- note e campi modulo


def _pdf_con_annotazioni(percorso, nota: str, valore_campo: str,
                         aspetto: str | None = None):
    """Una pagina con una nota gialla e un campo modulo compilato.

    E' il PDF che esce da chiunque abbia annotato un atto, o da qualunque
    modulo compilato a schermo invece che stampato.
    """
    pdf = pikepdf.Pdf.new()
    # La pagina porta anche del testo suo, come qualunque modulo vero: senza,
    # il documento non avrebbe nessun testo estraibile e verrebbe respinto
    # come scansione — che e' la risposta giusta per quel caso e la domanda
    # sbagliata per questo.
    pdf.pages.append(_pagina_con_testo(pdf, "Modulo di richiesta - riservato"))
    pagina = pdf.pages[0]

    annotazioni = [pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Annot"), Subtype=pikepdf.Name("/Text"),
        Rect=pikepdf.Array([300, 700, 320, 720]),
        Contents=pikepdf.String(nota)))]

    campo = pikepdf.Dictionary(
        Type=pikepdf.Name("/Annot"), Subtype=pikepdf.Name("/Widget"),
        FT=pikepdf.Name("/Tx"), T=pikepdf.String("nome"),
        Rect=pikepdf.Array([60, 600, 300, 620]),
        V=pikepdf.String(valore_campo))
    if aspetto is not None:
        # Il disegno gia' pronto di come il campo si vede. E' la parte che
        # rende il difetto invisibile: si cambia il valore e sullo schermo
        # resta scritto quello di prima.
        forma = pdf.make_stream(
            f"BT /Helv 10 Tf ({aspetto}) Tj ET".encode("latin-1"))
        forma.Type = pikepdf.Name("/XObject")
        forma.Subtype = pikepdf.Name("/Form")
        forma.BBox = pikepdf.Array([0, 0, 240, 20])
        campo.AP = pikepdf.Dictionary(N=pdf.make_indirect(forma))
    campo = pdf.make_indirect(campo)
    annotazioni.append(campo)

    pagina.Annots = pikepdf.Array(annotazioni)
    pdf.Root.AcroForm = pdf.make_indirect(
        pikepdf.Dictionary(Fields=pikepdf.Array([campo])))
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def test_il_dato_sparisce_anche_dalle_note_e_dai_campi(tmp_path):
    """Si guardano i **byte del file**, non il testo estratto.

    E' l'unico controllo che vede un dato che nessun lettore mostra e
    chiunque trova.
    """
    dentro = _pdf_con_annotazioni(
        tmp_path / "dentro.pdf",
        nota="Nota interna: chiamare Ludovica Sbrancagnoli, "
             "cod. fisc. RSSMRA85T10A562S",
        valore_campo="Mario Rossi")
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    byte = fuori.read_bytes()
    for valore in (b"Sbrancagnoli", b"RSSMRA85T10A562S", b"Mario Rossi"):
        assert valore not in byte, valore
    # E il conto deve dirlo: un dato tolto e non contato e' un rapporto che
    # mente al ribasso, cioe' fa credere il documento piu' pulito di com'era.
    assert esito.valori_da_togliere >= 3, esito


def test_l_aspetto_memorizzato_del_campo_non_resta_indietro(tmp_path):
    """La meta' che rende vera l'altra.

    Il dato e' nel file **due volte** — il valore e il disegno di come si
    vede — e ripulirne una sola produce un documento che sembra redatto e non
    lo e': la forma peggiore di questo difetto, perche' passa qualunque
    controllo fatto sul valore.
    """
    dentro = _pdf_con_annotazioni(
        tmp_path / "dentro.pdf", nota="niente di personale qui",
        valore_campo="Mario Rossi", aspetto="Mario Rossi")
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())

    assert b"Mario Rossi" not in fuori.read_bytes()
    with pikepdf.open(str(fuori)) as pdf:
        campi = [a for a in pdf.pages[0].Annots
                 if a.get("/Subtype") == pikepdf.Name("/Widget")]
        assert campi, "il campo e' sparito del tutto: non e' questo il rimedio"
        assert "/AP" not in campi[0], "l'aspetto di prima e' ancora li'"
        assert pdf.Root.AcroForm.get("/NeedAppearances"), (
            "senza questo il campo resta vuoto invece del segnaposto"
        )


def test_una_nota_senza_dati_personali_non_viene_toccata(tmp_path):
    """Il verso opposto: non si rovina un documento che non ne ha bisogno.

    Senza questo, «togli l'aspetto memorizzato» diventerebbe «toglilo
    sempre», e ogni modulo compilato uscirebbe visivamente vuoto anche quando
    non c'era niente da nascondere.
    """
    dentro = _pdf_con_annotazioni(
        tmp_path / "dentro.pdf", nota="Verificare la marca da bollo.",
        valore_campo="approvato", aspetto="approvato")
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())

    with pikepdf.open(str(fuori)) as pdf:
        campi = [a for a in pdf.pages[0].Annots
                 if a.get("/Subtype") == pikepdf.Name("/Widget")]
        assert "/AP" in campi[0], "l'aspetto e' stato buttato senza motivo"
        assert str(campi[0].V) == "approvato"


def test_la_verifica_sa_dire_di_no_sulle_annotazioni(tmp_path, monkeypatch):
    """La verifica leggeva **solo** il flusso della pagina.

    Cioe' per questa meta' del documento era un controllo che non poteva
    fallire: qualunque cosa fosse successa alle note e ai campi, sarebbe
    uscita verde. Qui la correzione si spegne di proposito e si pretende che
    la verifica se ne accorga — perche' una verifica che non sa dire di no
    non e' una verifica, e' una rassicurazione.
    """
    dentro = _pdf_con_annotazioni(
        tmp_path / "dentro.pdf", nota="niente di personale qui",
        valore_campo="Mario Rossi")

    redigi_pdf(dentro, tmp_path / "ok.pdf", PrivacyOptions())
    assert verifica_redazione(dentro, tmp_path / "ok.pdf")["sopravvissuti"] == 0

    monkeypatch.setattr(motore_pdf, "_redigi_annotazioni", lambda *a, **k: 0)
    redigi_pdf(dentro, tmp_path / "ko.pdf", PrivacyOptions())
    esito = verifica_redazione(dentro, tmp_path / "ko.pdf")
    assert esito["sopravvissuti"] == 1, esito
    assert esito["esempi"] == ["Mario Rossi"], esito


# ------------------------------------- una scansione fra pagine digitali


def _pdf_misto(percorso, seconda_con_immagine: bool):
    pdf = pikepdf.Pdf.new()
    pdf.pages.append(_pagina_con_testo(pdf, "Il cliente e' Giuseppe Verdi."))
    pdf.pages.append(_pagina_vuota(pdf, con_immagine=seconda_con_immagine))
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def test_una_pagina_scansionata_in_mezzo_viene_dichiarata(tmp_path):
    """Il rifiuto delle scansioni guardava il **documento**, non la pagina.

    Un PDF fatto tutto di immagini viene respinto dicendolo. Un PDF digitale
    con dentro un allegato firmato a mano — cioe' l'atto normale — no.
    """
    dentro = _pdf_misto(tmp_path / "misto.pdf", seconda_con_immagine=True)
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    assert esito.scansione is False, "il documento ha testo: non e' una scansione"
    assert esito.pagine_in_ripiego == [1], esito.pagine_in_ripiego
    assert "scansionata" in esito.motivi_ripiego[0], esito.motivi_ripiego
    # E la pagina digitale dev'essere stata trattata davvero: senza questa
    # riga il test passerebbe anche se il rimedio fosse smettere di redigere.
    assert b"Giuseppe Verdi" not in fuori.read_bytes()


def test_una_pagina_bianca_non_e_una_scansione(tmp_path):
    """Senza distinguerle, ogni pagina separatrice diventerebbe un allarme.

    Una pagina bianca non ha niente da togliere: chiamarla «non trattata»
    sarebbe vero alla lettera e falso nel senso, e un allarme che si impara a
    ignorare e' peggio di nessun allarme.
    """
    dentro = _pdf_misto(tmp_path / "con-bianca.pdf", seconda_con_immagine=False)
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())
    assert esito.pagine_in_ripiego == [], esito.motivi_ripiego
