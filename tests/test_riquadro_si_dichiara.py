# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il segno che il dato c'era: quando manca, e quando compare due volte.

Il dato tolto lascia un rettangolo colorato con dentro il segnaposto, e serve
a una cosa sola: **far vedere che li' c'era qualcosa**. Un documento in cui il
dato sparisce senza lasciare traccia si legge come se non fosse mai esistito, e
chi lo riceve non ha modo di chiedere «cosa c'era qui?».

Su certe pagine quel rettangolo non si vede — un fondo che ci finisce sopra, un
ritaglio — e `redazione_pdf.py` fa un secondo passaggio per rimediare. L'esito
di quel rimedio finiva in due campi che **nessuna rotta esponeva**:

* `pagine_riquadro_sopra`: rimediato, ma il segnaposto compare **due volte**
  nel testo copiato, una nella frase e una in fondo alla pagina;
* `pagine_senza_riquadro`: non rimediato. Il dato e' tolto lo stesso, ma sulla
  pagina non resta **nessun segno** che li' ci fosse qualcosa.

Il commento nel modulo diceva gia' «dirlo e' meglio che lasciarlo scoprire», e
il codice li calcolava con cura — compreso un secondo sguardo per non dichiarare
rimedi che non avevano funzionato. Poi si fermavano dentro un oggetto Python.

Un rapporto che calcola una cosa e non la dice non e' meglio di uno che non la
calcola: e' peggio, perche' sembra di averla guardata.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

pikepdf = pytest.importorskip("pikepdf")
pytest.importorskip("pypdfium2")

BASE = "http://127.0.0.1:5000"


def _client():
    from mr_rao.app_factory import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _pdf_con_fondo(righe: list[str]) -> bytes:
    """Testo su un fondo pieno: e' il caso in cui il rettangolo sparisce sotto.

    Lo stesso disegno usato da `tests/test_redazione_pdf.py` per provare il
    secondo passaggio; qui serve a farlo scattare dalla rotta.
    """
    pdf = pikepdf.Pdf.new()
    font = pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Font"), Subtype=pikepdf.Name("/Type1"),
        BaseFont=pikepdf.Name("/Helvetica"),
        Encoding=pikepdf.Name("/WinAnsiEncoding")))
    comandi = ["BT", "/F1 11 Tf"]
    y = 760
    for riga in righe:
        comandi.append(f"1 0 0 1 60 {y} Tm ({riga}) Tj")
        y -= 18
    comandi.append("ET")
    # Il fondo **dopo** il testo: copre tutto, compreso quello che disegneremo.
    comandi.append("0.9 0.9 0.9 rg 0 0 595 842 re f")
    pdf.pages.append(pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)),
        Contents=pdf.make_stream("\n".join(comandi).encode("latin-1"))))))
    fuori = io.BytesIO()
    pdf.save(fuori)
    pdf.close()
    return fuori.getvalue()


def _anteprima(dati: bytes) -> dict:
    r = _client().post("/api/pdf/anteprima", base_url=BASE, data={
        "file": (io.BytesIO(dati), "atto.pdf"),
        "lang": "it",
    }, content_type="multipart/form-data")
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def test_l_anteprima_dichiara_sempre_i_due_campi():
    """**Sempre**, anche a zero, come le pagine non trattate.

    Un campo che compare solo quando c'e' un problema insegna a leggerne
    l'assenza come «tutto bene», ed e' vero fino al giorno in cui il campo
    manca per un altro motivo.
    """
    dati = _anteprima(_pdf_con_fondo(["Il cliente Mario Rossi."]))
    assert "pagine_riquadro_doppio" in dati, dati.keys()
    assert "pagine_senza_segno" in dati, dati.keys()
    assert isinstance(dati["pagine_riquadro_doppio"], list)
    assert isinstance(dati["pagine_senza_segno"], list)


def test_su_un_fondo_pieno_il_rimedio_si_dichiara():
    """Il caso vero: il rettangolo finisce sotto e il rimedio lo ridisegna
    sopra. Chi copia il testo trova il segnaposto due volte, e va detto."""
    dati = _anteprima(_pdf_con_fondo(["Il cliente Mario Rossi."]))
    doppio = dati["pagine_riquadro_doppio"]
    senza = dati["pagine_senza_segno"]
    assert doppio or senza, (
        "su un fondo pieno o si rimedia o non si vede: entrambe le liste "
        f"vuote vuol dire che nessuno sta guardando (doppio={doppio}, senza={senza})"
    )


def test_su_una_pagina_normale_le_due_liste_sono_vuote():
    """La riga che impedisce di «correggere» dichiarando sempre qualcosa.

    Senza, i due casi qui sopra sarebbero verdi anche con due liste riempite a
    caso, e il pannello direbbe un avviso a ogni documento — cioe' nessuno.
    """
    pdf = pikepdf.Pdf.new()
    font = pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Font"), Subtype=pikepdf.Name("/Type1"),
        BaseFont=pikepdf.Name("/Helvetica"),
        Encoding=pikepdf.Name("/WinAnsiEncoding")))
    comandi = ["BT", "/F1 11 Tf", "1 0 0 1 60 760 Tm (Il cliente Mario Rossi.) Tj", "ET"]
    pdf.pages.append(pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)),
        Contents=pdf.make_stream("\n".join(comandi).encode("latin-1"))))))
    fuori = io.BytesIO()
    pdf.save(fuori)
    pdf.close()

    dati = _anteprima(fuori.getvalue())
    assert dati["pagine_riquadro_doppio"] == [], dati
    assert dati["pagine_senza_segno"] == [], dati


def test_il_pannello_mostra_le_due_cose():
    """Parita' GUI: un campo che l'interfaccia non legge non esiste per chi
    usa il programma. E' il difetto che questi test esistono per non ripetere."""
    js = Path("static/js/app.js").read_text(encoding="utf-8")
    for chiave in ("pagine_riquadro_doppio", "pagine_senza_segno"):
        assert chiave in js, f"il pannello non legge {chiave}"

    from mr_rao.i18n import TESTI

    for chiave in ("pdf_riquadro_doppio", "pdf_senza_segno"):
        voce = TESTI.get(chiave)
        assert voce, f"manca la frase {chiave}"
        for lingua in ("it", "en"):
            assert len(voce.get(lingua, "")) > 30, (chiave, lingua)
        assert chiave in js, f"il pannello non mostra {chiave}"
