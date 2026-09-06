# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Cio' che restava dentro un file chiamato «-redatto.pdf».

Tre buchi trovati dall'audit del 6 settembre 2026, tutti misurati eseguendo il
codice prima di scrivere una riga di correzione. Hanno in comune la forma
peggiore che un difetto possa avere qui: **il rapporto diceva di si' e il
documento diceva di no**.

1. I metadati
-------------

`/Author`, `/Title`, `/Subject` e il blocco XMP non stanno nel flusso di
contenuto, quindi la chirurgia dei glifi non li vedeva. Un PDF con
`/Subject: CF RSSMRA85M01H501Z` usciva con il codice fiscale intero, leggibile
nelle proprieta' del documento in ogni lettore. E' la stessa classe del difetto
delle annotazioni chiuso nella 1.24.0: testo che non e' nel flusso.

`verifica_redazione` non poteva dire di no, perche' guardava dove il dato non
era.

2. La scansione con lo strato OCR sopra
---------------------------------------

Una pagina scansionata a cui qualcuno ha gia' passato un OCR ha **due** copie
del testo: i pixel, che si vedono, e uno strato di glifi in modo di rendering
invisibile (`3 Tr`), che si seleziona e si cerca. La redazione toglieva i
glifi invisibili — cioe' l'unica delle due copie che non si vede — e dichiarava
la pagina trattata. Il dato restava a schermo, dentro l'immagine.

`_pagina_e_una_scansione` non scattava per costruzione: guarda se la pagina e'
senza testo, e questa il testo ce l'ha. Misurato prima della correzione: due
segnaposto inseriti, `pagine_in_ripiego` vuoto, `/Im0` ancora nel file.

3. La verifica che il prodotto non chiamava
-------------------------------------------

`verifica_redazione` esisteva, era buona ed era chiamata **solo dai test**. Le
rotte spedivano il file appena `redigi_pdf` non sollevava. Un controllo che gira
solo in CI non protegge nessun documento vero: qui viene chiamato prima di
consegnare, e se trova un valore ancora presente il file **non parte**.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import io
import zlib

import pytest

pikepdf = pytest.importorskip("pikepdf")
pytest.importorskip("pypdfium2")

from mr_rao.privacy import PrivacyOptions  # noqa: E402
from mr_rao.redazione_pdf import (  # noqa: E402
    redigi_pdf,
    testo_per_pagina as _testo_per_pagina,
    verifica_redazione,
)

BASE = "http://127.0.0.1:5000"

CF = "RSSMRA85M01H501Z"


def _pagina_di_testo(pdf, righe: list[str], invisibile: bool = False,
                     con_immagine: bool = False):
    """Una pagina in Helvetica, opzionalmente sopra un'immagine e invisibile."""
    font = pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Font"), Subtype=pikepdf.Name("/Type1"),
        BaseFont=pikepdf.Name("/Helvetica"),
        Encoding=pikepdf.Name("/WinAnsiEncoding")))
    risorse = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))

    comandi: list[str] = []
    if con_immagine:
        # Il foglio scansionato: un'immagine a tutta pagina. Grigia e piccola,
        # perche' qui conta che ci sia, non cosa rappresenti.
        larghezza, altezza = 40, 56
        immagine = pdf.make_stream(zlib.compress(bytes([200]) * (larghezza * altezza)))
        immagine.Type = pikepdf.Name("/XObject")
        immagine.Subtype = pikepdf.Name("/Image")
        immagine.Width = larghezza
        immagine.Height = altezza
        immagine.ColorSpace = pikepdf.Name("/DeviceGray")
        immagine.BitsPerComponent = 8
        immagine.Filter = pikepdf.Name("/FlateDecode")
        risorse["/XObject"] = pikepdf.Dictionary(Im0=immagine)
        comandi += ["q", "595 0 0 842 0 0 cm", "/Im0 Do", "Q"]

    comandi += ["BT", "/F1 11 Tf"]
    if invisibile:
        # Modo di rendering 3: i glifi non si disegnano. E' cosi' che ogni
        # motore OCR mette il testo riconosciuto sopra la scansione.
        comandi.append("3 Tr")
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


def _pdf_con_metadati(percorso, righe: list[str], **metadati: str):
    """Un PDF normale, con i metadati del documento pieni."""
    pdf = pikepdf.Pdf.new()
    _pagina_di_testo(pdf, righe)
    with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
        for chiave, valore in metadati.items():
            meta["dc:" + chiave if chiave != "creator" else "dc:creator"] = valore
    for chiave, valore in metadati.items():
        pdf.docinfo["/" + chiave.capitalize()] = valore
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _pdf_scansione_con_ocr(percorso, righe: list[str]):
    pdf = pikepdf.Pdf.new()
    _pagina_di_testo(pdf, righe, invisibile=True, con_immagine=True)
    pdf.save(str(percorso))
    pdf.close()
    return percorso


# ------------------------------------------------------------- 1. i metadati


def test_i_metadati_del_documento_non_escono_col_dato_dentro(tmp_path):
    """Le proprieta' del documento sono testo come gli altri.

    Si aprono con due click in qualunque lettore, e prima uscivano intere.
    """
    dentro = _pdf_con_metadati(
        tmp_path / "dentro.pdf",
        ["Una riga qualunque senza niente dentro."],
        title=f"Pratica di Mario Rossi",
        author="Mario Rossi",
        subject=f"Codice fiscale {CF}",
    )
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())

    con = pikepdf.open(str(fuori))
    try:
        docinfo = " ".join(str(v) for v in con.docinfo.values())
        xmp = str(con.Root.get("/Metadata", ""))
        if "/Metadata" in con.Root:
            xmp = bytes(con.Root["/Metadata"].read_bytes()).decode("utf-8", "replace")
    finally:
        con.close()

    assert CF not in docinfo, f"codice fiscale ancora nei metadati: {docinfo}"
    assert "Mario Rossi" not in docinfo, f"nome ancora nei metadati: {docinfo}"
    assert CF not in xmp, "codice fiscale ancora nell'XMP"
    assert "Mario Rossi" not in xmp, "nome ancora nell'XMP"


def test_la_verifica_guarda_anche_i_metadati(tmp_path):
    """Un controllo che non puo' dire di no non e' una verifica.

    Prima della correzione questo passava **verde** su un file con il codice
    fiscale nelle proprieta': la verifica leggeva flusso e annotazioni, e i
    metadati non sono ne' l'uno ne' le altre. Si prova con un file redatto a
    mano — cioe' il testo tolto dalla pagina e i metadati lasciati — perche' e'
    esattamente lo stato che la verifica deve saper bocciare.
    """
    dentro = _pdf_con_metadati(
        tmp_path / "dentro.pdf",
        [f"Il cliente Mario Rossi, codice fiscale {CF}."],
        subject=f"Codice fiscale {CF}",
    )
    # Il documento «redatto male»: pagina pulita, metadati intatti.
    fuori = tmp_path / "fuori.pdf"
    pdf = pikepdf.Pdf.new()
    _pagina_di_testo(pdf, ["Il cliente [NOME_1], codice fiscale [CF_1]."])
    pdf.docinfo["/Subject"] = f"Codice fiscale {CF}"
    pdf.save(str(fuori))
    pdf.close()

    esito = verifica_redazione(dentro, fuori, PrivacyOptions())
    assert esito["sopravvissuti"] >= 1, esito
    assert any(CF in e for e in esito["esempi"]), esito


# --------------------------------------------- 2. la scansione con l'OCR sopra


def test_una_scansione_gia_passata_dall_ocr_non_e_una_pagina_trattata(tmp_path):
    """I glifi invisibili si tolgono, i pixel restano: non e' una redazione.

    La pagina deve finire fra quelle **non trattate**, col motivo scritto.
    Dichiararla redatta e' il modo peggiore di sbagliare in questo prodotto:
    chi la consegna crede che il dato non ci sia, e il dato si legge a schermo.
    """
    dentro = _pdf_scansione_con_ocr(
        tmp_path / "scan.pdf",
        [f"Il cliente Mario Rossi, codice fiscale {CF}."],
    )
    fuori = tmp_path / "scan-redatto.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    assert esito.pagine_in_ripiego == [0], (
        f"pagina dichiarata trattata: ripiego={esito.pagine_in_ripiego} "
        f"segnaposto={esito.segnaposto_inseriti}"
    )
    assert any("ocr" in m.lower() or "scansion" in m.lower()
               for m in esito.motivi_ripiego), esito.motivi_ripiego


def test_una_pagina_digitale_con_un_logo_resta_trattata(tmp_path):
    """La riga che impedisce di «correggere» rifiutando ogni pagina con
    un'immagine dentro. Il testo qui si **vede**: e' una pagina normale con un
    logo, ed e' la forma di meta' della carta intestata.
    """
    pdf = pikepdf.Pdf.new()
    _pagina_di_testo(pdf, [f"Il cliente Mario Rossi, codice fiscale {CF}."],
                     invisibile=False, con_immagine=True)
    dentro = tmp_path / "carta.pdf"
    pdf.save(str(dentro))
    pdf.close()

    fuori = tmp_path / "carta-redatta.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    assert esito.pagine_in_ripiego == [], esito.motivi_ripiego
    testo = "\n".join(_testo_per_pagina(fuori))
    assert CF not in testo, testo


# ------------------------------------- 3. la verifica, chiamata dal prodotto


def _client():
    from mr_rao.app_factory import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _bytes_con_metadati(righe: list[str], **metadati: str) -> bytes:
    pdf = pikepdf.Pdf.new()
    _pagina_di_testo(pdf, righe)
    for chiave, valore in metadati.items():
        pdf.docinfo["/" + chiave.capitalize()] = valore
    fuori = io.BytesIO()
    pdf.save(fuori)
    pdf.close()
    return fuori.getvalue()


def test_lo_scaricamento_non_consegna_un_file_con_un_superstite(tmp_path):
    """La verifica gira **prima** di consegnare, non solo in CI.

    Si prova sul percorso vero — la rotta che l'utente usa — con un file la cui
    scansione OCR non e' redigibile: la pagina finisce in ripiego, il dato resta
    a schermo, e il file non deve partire come se fosse a posto.
    """
    pdf = pikepdf.Pdf.new()
    _pagina_di_testo(pdf, [f"Il cliente Mario Rossi, codice fiscale {CF}."],
                     invisibile=True, con_immagine=True)
    dati = io.BytesIO()
    pdf.save(dati)
    pdf.close()

    r = _client().post("/api/export/pdf", base_url=BASE, data={
        "file": (io.BytesIO(dati.getvalue()), "scansione.pdf"),
        "lang": "it",
    }, content_type="multipart/form-data")

    assert r.status_code != 200, (
        "un PDF la cui unica copia leggibile del dato resta nell'immagine "
        "e' stato consegnato come redatto"
    )


def test_la_verifica_gira_davvero_prima_di_consegnare(monkeypatch, tmp_path):
    """Il gate esiste e ferma il file, non solo il modulo che sa cercare.

    **Perche' con un finto e non con un PDF vero.** Un documento in cui la
    redazione dichiara la pagina trattata e lascia il dato dentro sarebbe un
    difetto aperto: costruirne uno vorrebbe dire tenerne uno in casa. Qui si
    sostituisce la verifica con una che dice «e' rimasto qualcosa a pagina 0»,
    e si guarda cosa fa la rotta. Quello che questo test prova e' l'unica cosa
    che serve provare: che il verdetto della verifica **comanda**. Che la
    verifica sappia dire di no lo provano gli altri test di questo file.
    """
    import mr_rao.redazione_pdf as modulo

    def finta(sorgente, destinazione, opzioni=None):
        return {
            "dichiarati_dal_motore": 1,
            "individuati_nel_testo": 1,
            "persi_prima_di_tagliare": 0,
            "sopravvissuti": 1,
            "esempi": ["Mario Rossi"],
            "pagine_con_superstiti": [0],
        }

    monkeypatch.setattr(modulo, "verifica_redazione", finta)

    dati = _bytes_con_metadati([f"Il cliente Mario Rossi, codice fiscale {CF}."])
    r = _client().post("/api/export/pdf", base_url=BASE, data={
        "file": (io.BytesIO(dati), "atto.pdf"),
        "lang": "it",
    }, content_type="multipart/form-data")

    assert r.status_code == 500, (
        "la verifica ha trovato un superstite su una pagina dichiarata "
        f"trattata e il file e' partito lo stesso (stato {r.status_code})"
    )


def test_una_pagina_dichiarata_non_trattata_non_blocca_la_consegna(monkeypatch,
                                                                   tmp_path):
    """La riga che impedisce di «correggere» bloccando ogni ripiego.

    Un valore rimasto su una pagina che il rapporto dichiara non trattata e'
    gia' detto all'utente, ed e' il comportamento di sempre: il file si
    consegna, con l'elenco accanto. Bloccarlo qui vorrebbe dire rifiutare ogni
    documento con una pagina in ripiego — una regressione grossa, e nella
    direzione che sembra prudente.
    """
    import mr_rao.redazione_pdf as modulo

    vera = modulo.redigi_pdf

    def redigi_con_ripiego(sorgente, destinazione, opzioni=None):
        esito = vera(sorgente, destinazione, opzioni)
        esito.pagine_in_ripiego = [0]
        esito.motivi_ripiego = ["finto, per la prova"]
        return esito

    def finta(sorgente, destinazione, opzioni=None):
        return {
            "dichiarati_dal_motore": 1,
            "individuati_nel_testo": 1,
            "persi_prima_di_tagliare": 0,
            "sopravvissuti": 1,
            "esempi": ["Mario Rossi"],
            "pagine_con_superstiti": [0],
        }

    monkeypatch.setattr(modulo, "verifica_redazione", finta)
    monkeypatch.setattr(modulo, "redigi_pdf", redigi_con_ripiego)

    dati = _bytes_con_metadati([f"Il cliente Mario Rossi, codice fiscale {CF}."])
    r = _client().post("/api/export/pdf", base_url=BASE, data={
        "file": (io.BytesIO(dati), "atto.pdf"),
        "lang": "it",
    }, content_type="multipart/form-data")

    assert r.status_code == 200, r.data[:300]


def test_lo_scaricamento_normale_continua_a_funzionare(tmp_path):
    """La riga che impedisce di «correggere» bloccando tutto.

    Un PDF digitale ordinario deve continuare a uscire, redatto, con 200.
    """
    dati = _bytes_con_metadati(
        [f"Il cliente Mario Rossi, codice fiscale {CF}.",
         "e questa riga non contiene nessun dato personale."],
        subject=f"Pratica di Mario Rossi",
    )
    r = _client().post("/api/export/pdf", base_url=BASE, data={
        "file": (io.BytesIO(dati), "atto.pdf"),
        "lang": "it",
    }, content_type="multipart/form-data")

    assert r.status_code == 200, r.data[:300]
    uscita = tmp_path / "uscita.pdf"
    uscita.write_bytes(r.data)
    testo = "\n".join(_testo_per_pagina(uscita))
    assert CF not in testo, testo
    assert "nessun dato personale" in testo, "il resto del documento e' sparito"
