# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
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


def _pdf_con_spazio_colore(percorso, righe: list[str]):
    """Come `_pdf_con_righe`, ma il colore si imposta con `cs`+`scn`.

    E' come lo scrivono i produttori veri — una Gazzetta Ufficiale lo fa — e
    senza questa variante il test del colore **non puo' fallire**: su un file
    che il colore lo imposta con `rg` non c'e' nessuno spazio colore da
    dimenticare.
    """
    pdf = pikepdf.Pdf.new()
    font = pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Font"), Subtype=pikepdf.Name("/Type1"),
        BaseFont=pikepdf.Name("/Helvetica"),
        Encoding=pikepdf.Name("/WinAnsiEncoding")))
    comandi = ["/DeviceGray cs", "0 scn", "BT", "/F1 12 Tf"]
    y = 760
    for riga in righe:
        comandi.append(f"1 0 0 1 60 {y} Tm ({riga}) Tj")
        y -= 30
    comandi.append("ET")
    pdf.pages.append(pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)),
        Contents=pdf.make_stream("\n".join(comandi).encode("latin-1"))))))
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _pixel_scuri(percorso, dall_alto: float, all_alto: float) -> int:
    """Quanti pixel scuri in una fascia orizzontale della prima pagina."""
    documento = pdfium.PdfDocument(str(percorso))
    try:
        immagine = documento[0].render(scale=1.5).to_pil().convert("L")
    finally:
        documento.close()
    larghezza, altezza = immagine.size
    fascia = immagine.crop((0, int(altezza * dall_alto), larghezza,
                            int(altezza * all_alto)))
    return sum(1 for p in fascia.getdata() if p < 128)


def test_il_testo_dopo_il_segnaposto_si_vede_ancora(tmp_path):
    """**Il difetto piu' brutto uscito da questa funzione, e si vede solo qui.**

    Il segnaposto si scrive in bianco perche' dietro ci va un rettangolo verde
    scuro, e il colore di prima va rimesso subito dopo. Rimetterlo vuol dire
    ricordarsi anche lo **spazio colore**: `scn` prende il significato da li',
    e riemettere `0 scn` dopo un `1 1 1 rg` — che nel frattempo ha portato lo
    spazio a DeviceRGB — vuol dire un'altra cosa.

    Su una Gazzetta il risultato era mezza pagina **bianca su bianco**: il
    testo c'era ancora, si estraeva, si copiava, e non si vedeva. Nessun
    controllo sul testo puo' accorgersene — per questo qui si contano i pixel.
    """
    dentro = _pdf_con_spazio_colore(tmp_path / "dentro.pdf", [
        "Il cliente Mario Rossi ha firmato.",
        "Questa riga viene dopo e deve restare visibile.",
        "E anche questa, piu' sotto.",
    ])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori)

    prima = _pixel_scuri(dentro, 0.10, 0.18)
    dopo = _pixel_scuri(fuori, 0.10, 0.18)
    assert prima > 200, "il documento di prova non ha testo dove il test guarda"
    assert dopo > prima * 0.6, (
        f"il testo sotto il segnaposto e' quasi sparito: {prima} pixel scuri "
        f"prima, {dopo} dopo. Probabile colore non rimesso."
    )


def test_il_rettangolo_non_si_mangia_il_resto_della_pagina(tmp_path):
    """**Il difetto piu' brutto che sia uscito da questa funzione.**

    Il segnaposto si scrive in bianco, perche' dietro ci va un rettangolo
    verde scuro. Il colore di prima va rimesso subito dopo — e rimetterlo
    voleva dire ricordarsi anche lo **spazio colore**: `scn` prende il suo
    significato da li', e riemettere `1 scn` dopo un `1 1 1 rg` — che nel
    frattempo ha portato lo spazio a DeviceRGB — vuol dire un'altra cosa.

    Su una Gazzetta il risultato era mezza pagina **bianca su bianco**: il
    testo c'era ancora, si copiava, e non si vedeva. Nessun controllo sui
    conteggi se ne sarebbe accorto, perche' non manca niente: e' invisibile.
    """
    dentro = _pdf_con_righe(tmp_path / "dentro.pdf", [
        "Il cliente Mario Rossi ha firmato il contratto.",
        "Questa riga viene dopo e non deve sparire.",
        "E nemmeno questa, che viene dopo ancora.",
    ])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori)

    prima, dopo = _testo(dentro), _testo(fuori)
    assert "Questa riga viene dopo e non deve sparire." in dopo
    assert "E nemmeno questa" in dopo
    # Il testo non si accorcia oltre la lunghezza del valore tolto.
    assert len(dopo) > len(prima) * 0.9, (len(prima), len(dopo))


def test_il_segnaposto_resta_al_suo_posto_nella_riga(tmp_path):
    """Il testo redatto deve **leggersi**, ed e' meta' del prodotto.

    Disegnando l'etichetta in coda al flusso — che è la strada più semplice —
    il documento resta bello e il testo copiato esce con tutte le etichette
    ammucchiate in fondo alla pagina. Qui si pretende che stiano nella frase.
    """
    dentro = _pdf_con_righe(tmp_path / "dentro.pdf", [
        "Il cliente Mario Rossi ha firmato oggi.",
    ])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori)

    dopo = " ".join(_testo(fuori).split())
    assert re.search(r"cliente\s+\{\{NAME_1\}\}\s+ha firmato", dopo), dopo


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


# ------------------------------------------- il fondo colorato arriva a schermo


def _pdf_con_fondo(percorso, righe: list[str]):
    """Una pagina che **dipinge un proprio fondo** prima di scrivere.

    E' come sono fatte le slide, le carte intestate e i riquadri bianchi
    arrotondati: un rettangolo bianco grande quanto la pagina, e poi il testo.
    Senza questa variante il controllo sul fondo colorato non puo' fallire --
    su una pagina che non dipinge niente, un rettangolo messo in testa al
    flusso si vede sempre.
    """
    pdf = pikepdf.Pdf.new()
    font = pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Font"), Subtype=pikepdf.Name("/Type1"),
        BaseFont=pikepdf.Name("/Helvetica"),
        Encoding=pikepdf.Name("/WinAnsiEncoding")))
    comandi = ["q 1 1 1 rg 0 0 595 842 re f Q", "BT", "/F1 12 Tf"]
    y = 760
    for riga in righe:
        comandi.append(f"1 0 0 1 60 {y} Tm ({riga}) Tj")
        y -= 30
    comandi.append("ET")
    pdf.pages.append(pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)),
        Contents=pdf.make_stream("\n".join(comandi).encode("latin-1"))))))
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _pixel_del_fondo(percorso, pagina: int = 0) -> int:
    """Quanti pixel del verde del rettangolo si vedono sulla pagina."""
    from mr_rao.redazione_pdf import COLORE_RETTANGOLO, TOLLERANZA_COLORE

    atteso = [round(c * 255) for c in COLORE_RETTANGOLO]
    documento = pdfium.PdfDocument(str(percorso))
    try:
        immagine = documento[pagina].render(scale=1.5).to_pil().convert("RGB")
    finally:
        documento.close()
    dati = immagine.tobytes()
    return sum(
        1
        for i in range(0, len(dati), 3)
        if all(abs(dati[i + k] - atteso[k]) <= TOLLERANZA_COLORE for k in range(3))
    )


def test_il_misuratore_del_fondo_sa_dire_di_no(tmp_path):
    """Prima di credere ai numeri qui sotto: su un PDF **non redatto** quei
    pixel devono essere zero. Se il contatore li trovasse anche li', starebbe
    misurando un'altra cosa e ogni verifica successiva sarebbe vera per
    costruzione."""
    dentro = _pdf_con_righe(tmp_path / "dentro.pdf", ["Il cliente Mario Rossi."])
    assert _pixel_del_fondo(dentro) == 0


def test_il_fondo_si_vede_su_una_pagina_normale(tmp_path):
    dentro = _pdf_con_righe(tmp_path / "dentro.pdf", ["Il cliente Mario Rossi."])
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori)

    assert esito.segnaposto_inseriti == 1
    assert _pixel_del_fondo(fuori) > 200
    # Non e' stato necessario rifare niente: questa pagina non copre niente.
    assert esito.pagine_riquadro_sopra == []


def test_il_fondo_si_vede_anche_se_la_pagina_ne_ha_uno_suo(tmp_path):
    """**Il difetto per cui esiste il secondo passaggio.**

    Il rettangolo va in testa al flusso, cioe' dietro a tutto. Una pagina che
    dipinge un proprio fondo lo copre, e siccome il segnaposto e' scritto in
    bianco -- conta sul rettangolo scuro dietro -- di quella redazione **non
    si vede piu' niente**: ne' che un dato e' stato tolto, ne' quale.

    Trovato su documenti veri: due PDF impaginati come slide su dodici presi
    dal disco. Prima della correzione questo test trova zero pixel verdi.
    """
    dentro = _pdf_con_fondo(tmp_path / "dentro.pdf", ["Il cliente Mario Rossi."])
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori)

    assert esito.segnaposto_inseriti == 1
    assert _pixel_del_fondo(fuori) > 200, (
        "il rettangolo e' nel file ma non arriva a schermo: il fondo della "
        "pagina lo ha coperto"
    )
    assert esito.pagine_riquadro_sopra == [0]


def test_l_etichetta_resta_leggibile_sul_riquadro_rifatto(tmp_path):
    """Un rettangolo pieno e muto direbbe meta' di quello che serve.

    Dentro al verde ci devono essere dei pixel chiari: sono l'etichetta
    riscritta sopra. Si guardano **solo i pixel dentro il rettangolo**, se no
    li si troverebbe nel bianco della pagina.
    """
    from mr_rao.redazione_pdf import segnaposto_sulla_pagina

    dentro = _pdf_con_fondo(tmp_path / "dentro.pdf", ["Il cliente Mario Rossi."])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori)

    documento = pdfium.PdfDocument(str(fuori))
    try:
        riquadri = segnaposto_sulla_pagina(documento[0])
        assert riquadri, "nessun segnaposto misurato sulla pagina"
        sinistra, basso, destra, alto = riquadri[0][:4]
        _, altezza_pagina = documento[0].get_size()
        immagine = documento[0].render(scale=2.0).to_pil().convert("L")
    finally:
        documento.close()

    ritaglio = immagine.crop((
        int(sinistra * 2), int((altezza_pagina - alto) * 2),
        int(destra * 2), int((altezza_pagina - basso) * 2),
    ))
    chiari = sum(1 for p in ritaglio.tobytes() if p > 200)
    assert chiari > 30, (
        f"dentro il rettangolo non c'e' testo chiaro: {chiari} pixel. "
        "Il riquadro e' pieno e muto."
    )


def test_su_una_pagina_normale_il_segnaposto_non_si_ripete(tmp_path):
    """Il prezzo del riquadro rifatto **non** si paga dove non serve.

    Sulla pagina rifatta l'etichetta viene riscritta, quindi in un
    copia-incolla il segnaposto compare due volte. Su tutte le altre pagine
    -- cioe' la stragrande maggioranza -- deve restare una sola.
    """
    dentro = _pdf_con_righe(tmp_path / "dentro.pdf", ["Il cliente Mario Rossi."])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori)

    assert len(re.findall(r"\{\{NAME(?:_\d+)?\}\}", _testo(fuori))) == 1


def test_il_riquadro_rifatto_raddoppia_il_segnaposto_nel_testo(tmp_path):
    """Il prezzo, scritto invece che scoperto.

    Sulla pagina rifatta l'etichetta viene ridisegnata sopra al rettangolo, e
    quel testo si aggiunge a quello che sta gia' nel flusso: chi copia la
    pagina trova il segnaposto due volte. E' il compromesso dichiarato in
    `ETICHETTA_SUL_RIQUADRO_SOPRA`, e questo test esiste perche' cambiarlo
    senza accorgersene non si possa.
    """
    dentro = _pdf_con_fondo(tmp_path / "dentro.pdf", ["Il cliente Mario Rossi."])
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori)

    assert esito.pagine_riquadro_sopra == [0]
    quante = len(re.findall(r"\{\{NAME(?:_\d+)?\}\}", _testo(fuori)))
    assert quante == 2, quante


def test_quota_visibile_distingue_coperto_da_scoperto(tmp_path):
    """La misura su cui si regge la decisione, messa alla prova nei due versi.

    Un controllo che rispondesse sempre «si vede» lascerebbe passare
    esattamente il difetto che deve prendere, e sarebbe verde per sempre.
    """
    from mr_rao.redazione_pdf import (
        QUOTA_MINIMA_VISIBILE,
        quota_visibile,
        segnaposto_sulla_pagina,
    )

    partenza = _pdf_con_righe(tmp_path / "a.pdf", ["Il cliente Mario Rossi."])
    normale = tmp_path / "normale.pdf"
    redigi_pdf(partenza, normale)

    documento = pdfium.PdfDocument(str(normale))
    try:
        riquadri = segnaposto_sulla_pagina(documento[0])
        visibile = quota_visibile(documento[0], riquadri)
    finally:
        documento.close()

    # Gli stessi rettangoli, misurati dove non sono stati disegnati: la pagina
    # di partenza. Li' la risposta deve essere «non si vede».
    prima = pdfium.PdfDocument(str(partenza))
    try:
        coperto = quota_visibile(prima[0], riquadri)
    finally:
        prima.close()

    assert visibile > QUOTA_MINIMA_VISIBILE, visibile
    assert coperto < QUOTA_MINIMA_VISIBILE, coperto
