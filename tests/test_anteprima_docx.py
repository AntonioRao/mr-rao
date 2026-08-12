"""Anteprima del contenuto di un .docx: prima e dopo, non pagine.

Un .docx non ha pagine finche' qualcuno non lo impagina, e Word non e'
una dipendenza. Quindi due colonne di HTML (mammoth), e una riga che
dice che **non** e' l'impaginazione -- senza quella riga chi guarda
conclude che il documento consegnato sara' cosi'.
"""
from __future__ import annotations

import io
import zipfile

from mr_rao.docx_export import html_da_docx

BASE = "http://127.0.0.1:5000"


def _docx(testo: str) -> bytes:
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{testo}</w:t></w:r></w:p></w:body></w:document>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Target="word/document.xml" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"/>'
        "</Relationships>"
    )
    types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
        'officedocument.wordprocessingml.document.main+xml"/></Types>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
    return buf.getvalue()


def test_html_da_docx_rende_il_testo() -> None:
    html = html_da_docx(_docx("Mario Rossi ha firmato"))
    assert "Mario Rossi" in html


def test_html_da_docx_toglie_gli_script() -> None:
    """mammoth non emette script, ma la funzione e' l'ultimo cancello
    prima che l'HTML entri nella pagina: deve saperli togliere."""
    html = html_da_docx(_docx("ok"))
    assert "<script" not in html.lower()


def test_l_anteprima_da_le_due_versioni(client) -> None:
    dati = _docx("Contatta mario.rossi@example.it")
    r = client.post(
        "/api/docx/anteprima",
        base_url=BASE,
        data={"file": (io.BytesIO(dati), "lettera.docx")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200, r.data[:300]
    corpo = r.get_json()
    assert "mario.rossi@example.it" in corpo["prima"]
    assert "mario.rossi@example.it" not in corpo["dopo"]
    assert "EMAIL" in corpo["dopo"]
    assert corpo["sostituzioni"] >= 1


def test_l_anteprima_dice_che_non_e_impaginazione(client) -> None:
    """La riga che decide se la funzione serve o inganna."""
    dati = _docx("solo testo")
    r = client.post(
        "/api/docx/anteprima",
        base_url=BASE,
        data={"file": (io.BytesIO(dati), "nota.docx"), "lang": "it"},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200, r.data[:300]
    avviso = r.get_json()["avviso"]
    assert "contenuto" in avviso.lower()
    assert "impaginazione" in avviso.lower()


def test_un_pdf_non_passa(client) -> None:
    r = client.post(
        "/api/docx/anteprima",
        base_url=BASE,
        data={"file": (io.BytesIO(b"%PDF-1.4"), "atto.pdf")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 400
    assert "docx" in r.get_json()["error"].lower()


def test_senza_file_dice_di_no(client) -> None:
    r = client.post("/api/docx/anteprima", base_url=BASE, data={})
    assert r.status_code == 400


def test_il_pannello_e_nella_pagina(client) -> None:
    pagina = client.get("/", base_url=BASE).get_data(as_text=True)
    for pezzo in (
        'id="docx-pannello"',
        'id="docx-anteprima-btn"',
        'id="docx-html-prima"',
        'id="docx-html-dopo"',
        'id="docx-avviso"',
    ):
        assert pezzo in pagina, pezzo
