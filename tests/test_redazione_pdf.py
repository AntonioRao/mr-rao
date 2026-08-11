"""Redazione di un PDF senza trasformarlo in immagine.

Il PDF di prova si costruisce qui
---------------------------------

Nessun file di appoggio: le pagine si scrivono nel test, riga per riga, in
Helvetica. Costa qualche riga in piu' e in cambio i test girano su qualunque
macchina — e soprattutto **si vede cosa c'e' dentro il documento**, che quando
un controllo fallisce è la metà del lavoro.

I documenti veri restano indispensabili e stanno altrove: sono loro ad aver
prodotto ognuna delle trappole verificate qui sotto, e nessuna di esse sarebbe
venuta in mente scrivendo un file di prova.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import re

import pytest

pikepdf = pytest.importorskip("pikepdf")
pdfium = pytest.importorskip("pypdfium2")

from mr_rao.privacy import PrivacyOptions  # noqa: E402
from mr_rao.redazione_pdf import (  # noqa: E402
    IGNOTI,
    intervalli_da_togliere,
    leggi_tounicode,
    redigi_pdf,
    testo_per_pagina as _testo_per_pagina,
    valore_ancora_presente,
    verifica_redazione,
)


def _pdf_con_righe(percorso, righe: list[str], dentro_un_form: bool = False):
    """Un PDF di una pagina, una riga per elemento, in Helvetica.

    `dentro_un_form` mette il testo dentro un **Form XObject** invece che nel
    flusso della pagina: e' com'e' fatta meta' dei PDF veri, ed e' la forma su
    cui l'API a oggetti del motore PDF non arriva.
    """
    pdf = pikepdf.Pdf.new()
    font = pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Font"), Subtype=pikepdf.Name("/Type1"),
        BaseFont=pikepdf.Name("/Helvetica"),
        Encoding=pikepdf.Name("/WinAnsiEncoding")))

    comandi = ["BT", "/F1 11 Tf"]
    y = 760
    for riga in righe:
        testo = riga.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        comandi.append(f"1 0 0 1 60 {y} Tm ({testo}) Tj")
        y -= 18
    comandi.append("ET")
    grezzo = "\n".join(comandi).encode("latin-1")
    risorse = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))

    if dentro_un_form:
        forma = pdf.make_stream(grezzo)
        forma.Type = pikepdf.Name("/XObject")
        forma.Subtype = pikepdf.Name("/Form")
        forma.BBox = pikepdf.Array([0, 0, 595, 842])
        forma.Resources = risorse
        contenuto = b"/Fm0 Do"
        risorse_pagina = pikepdf.Dictionary(
            XObject=pikepdf.Dictionary(Fm0=forma))
    else:
        contenuto = grezzo
        risorse_pagina = risorse

    pdf.pages.append(pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=risorse_pagina,
        Contents=pdf.make_stream(contenuto)))))
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _testo(percorso) -> str:
    return "\n".join(_testo_per_pagina(percorso))


# --------------------------------------------------- il dato sparisce davvero


def test_il_dato_non_e_piu_nel_file(tmp_path):
    """La riga che tiene tutto.

    Non «e' coperto da un rettangolo»: **non c'e'**. Un rettangolo nero si
    toglie in un minuto, e uno strumento che lo chiamasse redazione sarebbe
    peggio di uno che non fa niente, perche' chi lo usa smetterebbe di stare
    attento.
    """
    dentro = _pdf_con_righe(tmp_path / "dentro.pdf", [
        "Il cliente Mario Rossi ha scritto a mario.rossi@example.it",
        "e abita in via Giuseppe Verdi 12, Pisa.",
    ])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori)

    uscita = _testo(fuori)
    for sparito in ("Mario Rossi", "mario.rossi@example.it", "Giuseppe Verdi"):
        assert sparito not in uscita, uscita


def test_il_documento_resta_un_documento(tmp_path):
    """Testo ancora estraibile e peso invariato: e' la differenza fra questa
    strada e la rasterizzazione, che protegge altrettanto e restituisce un
    documento con cui non si puo' piu' fare niente."""
    dentro = _pdf_con_righe(tmp_path / "dentro.pdf", [
        "Il cliente Mario Rossi ha firmato il contratto.",
        "Questa riga non contiene nessun dato personale.",
    ])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori)

    uscita = _testo(fuori)
    assert "Questa riga non contiene nessun dato personale." in uscita
    assert "{{NAME" in uscita
    assert fuori.stat().st_size < dentro.stat().st_size * 3


def test_il_segnaposto_tiene_il_numero(tmp_path):
    """Due persone diverse restano due persone diverse.

    Senza, il documento redatto perde il senso — ed e' la ragione per cui la
    numerazione esiste nel motore.
    """
    dentro = _pdf_con_righe(tmp_path / "dentro.pdf", [
        "Il cliente Mario Rossi ha citato Luigi Bianchi.",
        "Poi Mario Rossi ha firmato.",
    ])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori)

    uscita = _testo(fuori)
    etichette = re.findall(r"\{\{NAME_(\d+)\}\}", uscita)
    assert len(set(etichette)) == 2, uscita
    # Lo stesso nome due volte prende lo stesso numero.
    assert etichette.count(etichette[0]) == 2, etichette


def test_arriva_dentro_i_form_xobject(tmp_path):
    """**La trappola che ha bocciato la strada precedente.**

    Su una Gazzetta Ufficiale il testo sta dentro un Form XObject: l'API a
    oggetti del motore PDF non lo raggiunge, e la redazione usciva con zero
    sostituzioni su settantatre. Qui si scende nel form, e questo test e'
    l'unico che se ne accorgerebbe.
    """
    dentro = _pdf_con_righe(tmp_path / "dentro.pdf", [
        "Il cliente Mario Rossi ha firmato.",
    ], dentro_un_form=True)
    assert "Mario Rossi" in _testo(dentro), "il documento di prova e' sbagliato"

    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori)

    assert esito.pagine_in_ripiego == []
    assert "Mario Rossi" not in _testo(fuori)


def test_due_valori_sulla_stessa_riga(tmp_path):
    """Una riga e' un operando solo, e contiene spesso due dati.

    Finche' i tagli multipli nello stesso operando venivano rifiutati, un
    quarto delle pagine di una Gazzetta finiva nel ripiego.
    """
    dentro = _pdf_con_righe(tmp_path / "dentro.pdf", [
        "Presenti Mario Rossi e Luigi Bianchi, entrambi convocati.",
    ])
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori)

    uscita = _testo(fuori)
    assert esito.pagine_in_ripiego == []
    assert "Mario Rossi" not in uscita and "Luigi Bianchi" not in uscita
    assert "entrambi convocati" in uscita


def test_la_firma_degli_atti_pubblici(tmp_path):
    """Ruolo, due punti, cognome maiuscolo — su una riga sola.

    Nel flusso quella riga e' spesso spezzata in due pezzi posizionati, e
    finche' ogni spostamento valeva un a capo il motore non vedeva piu' la
    forma: undici cognomi su settantatre sopravvivevano tutti per questo.
    """
    dentro = _pdf_con_righe(tmp_path / "dentro.pdf", [
        "Roma, 6 dicembre 2023",
        "Il Ministro: GIORGETTI",
    ])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori)

    uscita = _testo(fuori)
    assert "GIORGETTI" not in uscita, uscita
    assert "Il Ministro" in uscita, "l'etichetta del ruolo non e' un dato personale"


# ------------------------------------------------------ quello che non si fa


def test_una_scansione_non_si_tocca(tmp_path):
    """Nessun testo estraibile = nessun glifo da togliere.

    Dirlo e' l'unica cosa onesta: disegnarci sopra dei rettangoli sarebbe
    esattamente la redazione finta che questo modulo esiste per evitare.
    """
    pdf = pikepdf.Pdf.new()
    pdf.pages.append(pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=pikepdf.Dictionary(),
        Contents=pdf.make_stream(b"0 0 0 rg 100 100 200 200 re f")))))
    dentro = tmp_path / "scansione.pdf"
    pdf.save(str(dentro))
    pdf.close()

    esito = redigi_pdf(dentro, tmp_path / "fuori.pdf")
    assert esito.scansione is True
    assert not (tmp_path / "fuori.pdf").exists(), \
        "un documento non redatto non deve uscire come se lo fosse"


def test_un_documento_pulito_non_si_riscrive(tmp_path):
    dentro = _pdf_con_righe(tmp_path / "dentro.pdf", [
        "Verbale della riunione tecnica del comitato.",
        "Nessun dato personale in questa pagina.",
    ])
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori)

    assert esito.valori_da_togliere == 0
    assert esito.glifi_rimossi == 0
    assert "Verbale della riunione tecnica" in _testo(fuori)


# ------------------------------------------- i pezzi, presi uno per uno


def test_i_valori_si_ricavano_dai_segnaposto_non_da_un_diff():
    """`CAFIERO` contro `{{NAME_1}}` condivide la «A» e la «E».

    Allineando con `difflib` uscivano tre tratti — «C», «FI», «RO» — invece di
    uno: tre frammenti troppo corti per essere cercati, quindi scartati, e il
    cognome restava intero nel documento **senza che nessun conteggio se ne
    accorgesse**. E' la classe di difetto peggiore che ci sia qui dentro.
    """
    testo = "Roma, 6 marzo 2024\nIl dirigente: CAFIERO\n24A01347"
    tratti = intervalli_da_togliere(testo, PrivacyOptions())
    assert [testo[a:b] for a, b, _ in tratti] == ["CAFIERO"]


def test_i_valori_escono_interi_anche_in_fila():
    testo = "Scrivere a mario.rossi@example.it oppure a Mario Rossi, via Verdi 12."
    tratti = intervalli_da_togliere(testo, PrivacyOptions())
    valori = [testo[a:b] for a, b, _ in tratti]
    assert "mario.rossi@example.it" in valori
    assert "Mario Rossi" in valori


def test_il_controllo_di_sopravvivenza_sa_dire_di_no():
    """Un controllo che non puo' fallire non e' una verifica.

    Il primo confronto cercava il valore a spazi tolti, e trovava «URSO»
    dentro «concorso»: dichiarava sopravvissuti che non erano mai stati la'.
    """
    assert valore_ancora_presente("URSO", "Il Ministro: URSO firma")
    assert not valore_ancora_presente("URSO", "bandito un concorso pubblico")
    # Lo stesso valore spezzato dal PDF va comunque riconosciuto.
    assert valore_ancora_presente("GIORGETTI", "Il Ministro: G IORGETTI")


def test_la_verifica_porta_un_numero_che_non_calcola_lei(tmp_path):
    """`dichiarati_dal_motore` viene dal motore, non da questo modulo.

    Senza, la verifica userebbe la stessa funzione con cui si taglia: se quella
    individuasse meta' dei valori, taglierebbe meta' e ne cercherebbe meta', e
    uscirebbe verde senza guardare niente.
    """
    dentro = _pdf_con_righe(tmp_path / "dentro.pdf", [
        "Il cliente Mario Rossi ha scritto a mario.rossi@example.it.",
    ])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori)

    esito = verifica_redazione(dentro, fuori)
    assert esito["dichiarati_dal_motore"] >= 2
    assert esito["persi_prima_di_tagliare"] == 0
    assert esito["sopravvissuti"] == 0, esito["esempi"]


def test_il_cmap_tounicode_legge_le_due_forme_vere():
    flusso = b"""
    begincmap
    1 beginbfchar <0041> <004D> endbfchar
    2 beginbfrange <0050> <0052> <0061> endbfrange
    1 beginbfrange <0060> <0061> [<0058> <0059>] endbfrange
    endcmap
    """
    mappa = leggi_tounicode(flusso)
    assert mappa[0x41] == "M"
    assert mappa[0x50] == "a" and mappa[0x52] == "c"
    assert mappa[0x60] == "X" and mappa[0x61] == "Y"


def test_un_cmap_illeggibile_non_inventa_niente():
    """Sbaglia dalla parte giusta: meno mappature, non di piu'.

    Un carattere non decodificato porta al ripiego, che e' un esito onesto.
    Una mappatura inventata porterebbe a tagliare i glifi sbagliati.
    """
    assert leggi_tounicode(b"niente di riconoscibile qui dentro") == {}
    assert IGNOTI, "serve almeno un carattere per dire «non lo so»"
