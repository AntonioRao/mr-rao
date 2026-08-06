"""Il tetto di tempo sull'OCR di un PDF.

Un thread Python non si uccide dall'esterno: l'unico punto interrompibile è
il confine fra una pagina e l'altra, dove già si legge il flag di annullamento.
Il limite di tempo si appoggia lì.

Due cose vanno verificate insieme, e la seconda conta quanto la prima:
1. che si fermi;
2. che **lo dica**. Un testo troncato in silenzio è peggio di nessun testo,
   perché la schermatura dei dati personali ha visto solo le pagine lette e
   nessuno se ne accorge guardando il risultato.
"""
from __future__ import annotations

import sys

import pytest

from mr_rao import ocr_service


class _PaginaFinta:
    def to_image(self, resolution=0):
        return type("Img", (), {"original": _ImmagineFinta()})()


class _ImmagineFinta:
    def save(self, path, format="PNG"):
        path.write_bytes(b"finta")


class _PdfFinto:
    def __init__(self, pagine: int):
        self.pages = [_PaginaFinta() for _ in range(pagine)]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class _OrologioFinto:
    """Ogni lettura avanza di 10 secondi: nessuna attesa vera nei test."""

    def __init__(self, passo: float = 10.0):
        self.adesso = 0.0
        self.passo = passo

    def monotonic(self) -> float:
        self.adesso += self.passo
        return self.adesso


@pytest.fixture()
def pdf_finto(monkeypatch):
    def _installa(pagine: int = 10):
        modulo = type("pdfplumber", (), {"open": staticmethod(lambda _p: _PdfFinto(pagine))})
        monkeypatch.setitem(sys.modules, "pdfplumber", modulo)
        monkeypatch.setattr(ocr_service, "extract_pdf_tables", lambda _p: "")
        monkeypatch.setattr(
            ocr_service, "ocr_image", lambda p, language="it": "testo della pagina"
        )
        return modulo

    return _installa


def test_senza_limite_legge_tutte_le_pagine(pdf_finto, tmp_path):
    pdf_finto(pagine=5)
    testo = ocr_service.ocr_pdf_fallback(tmp_path / "x.pdf", max_seconds=0)
    assert testo is not None
    assert testo.count("<!-- Pagina") == 5
    assert "interrotto" not in testo.lower()


def test_scaduto_il_tempo_si_ferma(pdf_finto, monkeypatch, tmp_path):
    pdf_finto(pagine=50)
    monkeypatch.setattr(ocr_service, "time", _OrologioFinto())
    testo = ocr_service.ocr_pdf_fallback(tmp_path / "x.pdf", max_seconds=25)
    assert testo is not None
    # scadenza fissata a 10+25=35; i controlli cadono a 20, 30, 40 → due pagine
    assert testo.count("<!-- Pagina") == 2


def test_il_troncamento_e_dichiarato(pdf_finto, monkeypatch, tmp_path):
    pdf_finto(pagine=50)
    monkeypatch.setattr(ocr_service, "time", _OrologioFinto())
    testo = ocr_service.ocr_pdf_fallback(tmp_path / "x.pdf", max_seconds=25)
    assert "OCR interrotto" in testo
    assert "parziale" in testo
    # In cima: chi legge deve saperlo prima di fidarsi del testo, non dopo.
    assert testo.index("OCR interrotto") < testo.index("Testo OCR")


def test_scaduto_subito_non_dice_documento_vuoto(pdf_finto, monkeypatch, tmp_path):
    """Zero pagine lette non è "nessun testo riconoscibile": è un timeout.

    Il primo messaggio manderebbe a cercare il problema nel documento, che
    invece era solo lento.
    """
    pdf_finto(pagine=50)
    monkeypatch.setattr(ocr_service, "time", _OrologioFinto(passo=1000.0))
    testo = ocr_service.ocr_pdf_fallback(tmp_path / "x.pdf", max_seconds=1)
    assert testo is not None
    assert "OCR interrotto" in testo


def test_annullamento_ha_ancora_la_precedenza(pdf_finto, tmp_path):
    """Il limite di tempo si è messo accanto al flag di cancel, non al suo posto."""
    pdf_finto(pagine=5)
    testo = ocr_service.ocr_pdf_fallback(
        tmp_path / "x.pdf", should_cancel=lambda: True, max_seconds=0
    )
    assert testo is None
