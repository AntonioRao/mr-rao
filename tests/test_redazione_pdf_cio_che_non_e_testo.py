# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Cio' che in un PDF **non e' testo**, e usciva lo stesso col dato dentro.

Quattro casi misurati il 3 ottobre 2026 su PDF sintetici, piu' uno trovato
riproducendoli. In tutti il rapporto diceva di si' e il file diceva di no.

1. I pixel sotto il rettangolo
------------------------------

Su una scansione con strato OCR la 1.30.0 toglieva il testo invisibile e
disegnava un rettangolo **sopra** l'immagine. L'immagine incorporata non la
toccava nessuno: estraendo l'XObject dal file redatto il dato si leggeva
intero. Coprire non e' cancellare. Misurato:

    pagine_coperte_sull_ocr=[0], pagine_in_ripiego=[]
    immagine /Im0 del redatto: identica all'originale = True
    verifica_redazione: sopravvissuti 0

Qui si guarda **l'immagine estratta**, mai la pagina renderizzata: la pagina
renderizzata mostra il rettangolo, ed e' esattamente il modo in cui questo
difetto e' rimasto verde.

1 bis. Il rettangolo spostato
-----------------------------

Trovato riproducendo il caso 1 con un foglio di quattro righe invece di una:
il riquadro si misurava passando a pdfium degli indici presi dal testo del
flusso. Le due numerazioni differiscono di un carattere per ogni a capo, e
alla terza riga il rettangolo lasciava scoperta la coda dell'IBAN. I banchi
esistenti avevano tutti una riga sola, dove le due numerazioni coincidono.

1 ter. Il testo sotto l'immagine
--------------------------------

Lasciato aperto dalla 1.30.1, chiuso nella 1.30.2: lo strato OCR scritto in
modo normale e poi coperto dall'immagine, invece che invisibile sopra. Sta in
fondo al file, con la sua misura.

2. La miniatura di pagina
-------------------------

`/Thumb` e' un'immagine della pagina **originale**, appesa al dizionario
della pagina. Sopravviveva intatta.

3. Il testo di struttura
------------------------

`/ActualText`, `/Alt`, `/E` e `/T` degli elementi di `/StructTreeRoot` sono
stringhe fuori dal flusso, come metadati e segnalibri. Uscivano in chiaro.

4. La pagina-immagine con una riga di testo
-------------------------------------------

Un'immagine a tutta pagina con un cedolino dentro e un pie' di pagina di
sette parole: il testo non e' vuoto, quindi non era una «scansione»; non ha
valori, quindi si passava oltre. File identico all'ingresso, esito muto.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import io
import shutil
import zlib

import pytest

pikepdf = pytest.importorskip("pikepdf")
pdfium = pytest.importorskip("pypdfium2")
PIL_Image = pytest.importorskip("PIL.Image")
from PIL import Image, ImageChops, ImageDraw  # noqa: E402

from mr_rao.privacy import PrivacyOptions  # noqa: E402
from mr_rao import redazione_pdf as modulo  # noqa: E402
from mr_rao.redazione_pdf import (  # noqa: E402
    redigi_pdf,
    testo_per_pagina as _testo_per_pagina,
    verifica_redazione,
)

CF = "RSSMRA85M01H501Z"
IBAN = "IT60X0542811101000000123456"

#: Un cedolino di quattro righe. **Quattro e non una**: con una riga sola gli
#: indici del flusso e quelli di pdfium coincidono, e il rettangolo spostato
#: (caso 1 bis) non si vede.
RIGHE = [
    "Cedolino di ottobre",
    f"Codice fiscale {CF}",
    f"IBAN {IBAN}",
    "NETTO IN BUSTA 1.612,34",
]

LARGO, ALTO = 595, 842
#: Pixel per punto del finto foglio scansionato.
SCALA = 2
CORPO = 15
#: Quanto puo' variare una zona azzerata. Zero su un'immagine senza perdita;
#: qualche unita' su un JPEG, dove il blocco accanto sporca il bordo.
PIATTO = 8
#: Sotto questa escursione non c'e' inchiostro: c'e' carta.
INCHIOSTRO = 100


# ----------------------------------------------------------------- il foglio


def _font(pdf):
    return pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Font"), Subtype=pikepdf.Name("/Type1"),
        BaseFont=pikepdf.Name("/Helvetica"),
        Encoding=pikepdf.Name("/WinAnsiEncoding")))


def _comandi_di_testo(righe, invisibile: bool, corpo: float = CORPO,
                      alto: int = 740, passo: int = 24) -> list[str]:
    comandi = ["BT", f"/F1 {corpo} Tf"]
    if invisibile:
        comandi.append("3 Tr")     # come lo mette ogni motore OCR
    y = alto
    for riga in righe:
        comandi.append(f"1 0 0 1 60 {y} Tm ({riga}) Tj")
        y -= passo
    comandi.append("ET")
    return comandi


def _aggiungi_pagina(pdf, comandi: list[str], xobject=None, extra=None):
    risorse = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=_font(pdf)))
    if xobject:
        risorse["/XObject"] = pikepdf.Dictionary(xobject)
    dizionario = pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, LARGO, ALTO]),
        Resources=risorse,
        Contents=pdf.make_stream("\n".join(comandi).encode("latin-1")))
    for chiave, valore in (extra or {}).items():
        dizionario[chiave] = valore
    pdf.pages.append(pikepdf.Page(pdf.make_indirect(dizionario)))


def _riquadri(righe, cercati, corpo: float = CORPO) -> dict[str, tuple[float, float, float, float]]:
    """Dove sta ogni stringa cercata, **secondo pdfium** e in punti pagina.

    Si misura su un PDF di solo testo con la stessa impaginazione: serve
    *prima* di disegnare il foglio, perche' l'inchiostro va messo dove lo
    strato OCR dira' che sta la parola.
    """
    pdf = pikepdf.Pdf.new()
    _aggiungi_pagina(pdf, _comandi_di_testo(righe, invisibile=False, corpo=corpo))
    buffer = io.BytesIO()
    pdf.save(buffer)
    pdf.close()
    documento = pdfium.PdfDocument(buffer.getvalue())
    try:
        testo = documento[0].get_textpage()
        try:
            contenuto = testo.get_text_range()
            fuori = {}
            for cercato in cercati:
                inizio = contenuto.index(cercato)
                scatole = [testo.get_charbox(k)
                           for k in range(inizio, inizio + len(cercato))]
                scatole = [s for s in scatole if s[0] != s[2] and s[1] != s[3]]
                fuori[cercato] = (min(s[0] for s in scatole), min(s[1] for s in scatole),
                                  max(s[2] for s in scatole), max(s[3] for s in scatole))
            return fuori
        finally:
            testo.close()
    finally:
        documento.close()


def _dritta(riquadro) -> tuple[int, int, int, int]:
    """Dal riquadro in punti al rettangolo in pixel, immagine a tutta pagina."""
    sinistra, basso, destra, alto = riquadro
    return (int(sinistra * SCALA), int((ALTO - alto) * SCALA),
            int(destra * SCALA) + 1, int((ALTO - basso) * SCALA) + 1)


def _ruotata(riquadro) -> tuple[int, int, int, int]:
    """Lo stesso, per l'immagine messa con `0 842 -595 0 595 0 cm`.

    Con quella matrice la colonna dell'immagine corre lungo la **y** della
    pagina e la riga lungo la **x**: e' la scansione fatta col foglio di
    traverso, e i conti si fanno a mano qui apposta, senza passare dal modulo.
    """
    sinistra, basso, destra, alto = riquadro
    return (int(basso * SCALA), int(sinistra * SCALA),
            int(alto * SCALA) + 1, int(destra * SCALA) + 1)


def _foglio(righe, in_pixel=_dritta, dimensione=(LARGO * SCALA, ALTO * SCALA),
            corpo: float = CORPO):
    """Il foglio scansionato: carta bianca, e un pettine nero dove c'e' scritto.

    Un pettine e non una scritta vera: non dipende da nessun font installato,
    e una zona «con l'inchiostro» si distingue da una azzerata con una
    domanda sola -- **e' piatta o no?** -- qualunque sia il colore usato per
    azzerarla.
    """
    immagine = Image.new("L", dimensione, 255)
    disegno = ImageDraw.Draw(immagine)
    for riquadro in _riquadri(righe, righe, corpo).values():
        x0, y0, x1, y1 = in_pixel(riquadro)
        for x in range(x0, x1, 8):
            disegno.rectangle((x, y0, min(x + 3, x1 - 1), y1 - 1), fill=0)
    return immagine


def _incorpora(pdf, immagine, formato: str = "grigio"):
    """L'immagine come XObject, nel formato chiesto."""
    if formato == "jpeg":
        buffer = io.BytesIO()
        immagine.save(buffer, "JPEG", quality=85)
        oggetto = pdf.make_stream(buffer.getvalue())
        oggetto.Filter = pikepdf.Name("/DCTDecode")
        oggetto.BitsPerComponent = 8
    elif formato == "colori":
        oggetto = pdf.make_stream(zlib.compress(immagine.convert("RGB").tobytes()))
        oggetto.Filter = pikepdf.Name("/FlateDecode")
        oggetto.BitsPerComponent = 8
    elif formato == "bilivello":
        oggetto = pdf.make_stream(zlib.compress(immagine.convert("1").tobytes()))
        oggetto.Filter = pikepdf.Name("/FlateDecode")
        oggetto.BitsPerComponent = 1
    elif formato == "fax":
        # CCITT gruppo 4: il formato delle scansioni in bianco e nero degli
        # scanner d'ufficio. Il motore PDF non lo decomprime da solo, quindi
        # passa per una strada diversa dalle altre tre.
        buffer = io.BytesIO()
        # Una striscia sola (campo 278): di default Pillow ne fa quattro, e
        # ognuna e' codificata per conto suo -- incollate non sono un fax.
        immagine.convert("1").save(buffer, "TIFF", compression="group4",
                                   tiffinfo={278: immagine.height})
        tiff = Image.open(io.BytesIO(buffer.getvalue()))
        (inizio,), (lunghezza,) = tiff.tag_v2[273], tiff.tag_v2[279]
        oggetto = pdf.make_stream(buffer.getvalue()[inizio:inizio + lunghezza])
        oggetto.Filter = pikepdf.Name("/CCITTFaxDecode")
        oggetto.DecodeParms = pikepdf.Dictionary(
            K=-1, Columns=immagine.width, Rows=immagine.height, BlackIs1=True)
        oggetto.BitsPerComponent = 1
    elif formato == "illeggibile":
        # Un filtro che qui nessuno sa aprire: la forma del JBIG2 senza il
        # decodificatore esterno, che e' il caso vero.
        oggetto = pdf.make_stream(b"\x00\x01\x02\x03 non e' un JBIG2")
        oggetto.Filter = pikepdf.Name("/JBIG2Decode")
        oggetto.BitsPerComponent = 1
    else:
        oggetto = pdf.make_stream(zlib.compress(immagine.tobytes()))
        oggetto.Filter = pikepdf.Name("/FlateDecode")
        oggetto.BitsPerComponent = 8
    oggetto.Type = pikepdf.Name("/XObject")
    oggetto.Subtype = pikepdf.Name("/Image")
    oggetto.Width, oggetto.Height = immagine.size
    oggetto.ColorSpace = pikepdf.Name(
        "/DeviceRGB" if formato == "colori" else "/DeviceGray")
    return oggetto


IMMAGINE_PIENA = ["q", f"{LARGO} 0 0 {ALTO} 0 0 cm", "/Im0 Do", "Q"]


def _scansione_con_ocr(percorso, righe=RIGHE, formato: str = "grigio",
                       corpo: float = CORPO):
    pdf = pikepdf.Pdf.new()
    _aggiungi_pagina(
        pdf,
        IMMAGINE_PIENA + _comandi_di_testo(righe, invisibile=True, corpo=corpo),
        xobject={"/Im0": _incorpora(pdf, _foglio(righe, corpo=corpo), formato)})
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _immagine_estratta(percorso, pagina: int = 0, dentro: str | None = None):
    """L'XObject immagine **tolto dal file**, decodificato qui e non dal modulo.

    Non si rende la pagina: sulla pagina resa c'e' il rettangolo sopra, e una
    prova che guarda li' e' verde anche quando i pixel sotto sono intatti.
    """
    with pikepdf.open(str(percorso)) as pdf:
        oggetti = pdf.pages[pagina].obj["/Resources"]["/XObject"]
        if dentro:
            oggetti = oggetti[dentro]["/Resources"]["/XObject"]
        oggetto = oggetti["/Im0"]
        grezzo = oggetto.read_raw_bytes()
        filtro = str(oggetto.get("/Filter"))
        dimensione = (int(oggetto.Width), int(oggetto.Height))
        if filtro == "/DCTDecode":
            return Image.open(io.BytesIO(grezzo)).convert("L")
        if filtro == "/CCITTFaxDecode":
            # Serve solo a guardare il foglio **di partenza**: quello redatto
            # esce riscritto in un formato che si legge con `zlib`.
            return _fax(grezzo, dimensione)
        assert filtro == "/FlateDecode", f"filtro inatteso: {filtro}"
        if str(oggetto.get("/ColorSpace")) == "/DeviceRGB":
            modo = "RGB"
        else:
            modo = "1" if int(oggetto.BitsPerComponent) == 1 else "L"
        return Image.frombytes(modo, dimensione, zlib.decompress(grezzo)).convert("L")


def _fax(grezzo: bytes, dimensione) -> "Image.Image":
    """Un flusso CCITT gruppo 4, fatto decodificare a pdfium.

    Lo si mette da solo su una pagina grande quanto lui, un punto per pixel,
    e si rende la pagina: quello che esce e' l'immagine, pixel per pixel.
    """
    pdf = pikepdf.Pdf.new()
    oggetto = pdf.make_stream(grezzo)
    oggetto.Type = pikepdf.Name("/XObject")
    oggetto.Subtype = pikepdf.Name("/Image")
    oggetto.Width, oggetto.Height = dimensione
    oggetto.ColorSpace = pikepdf.Name("/DeviceGray")
    oggetto.BitsPerComponent = 1
    oggetto.Filter = pikepdf.Name("/CCITTFaxDecode")
    oggetto.DecodeParms = pikepdf.Dictionary(
        K=-1, Columns=dimensione[0], Rows=dimensione[1], BlackIs1=True)
    _aggiungi_pagina(pdf, [f"q {dimensione[0]} 0 0 {dimensione[1]} 0 0 cm /Im0 Do Q"],
                     xobject={"/Im0": oggetto})
    pdf.pages[0].obj["/MediaBox"] = pikepdf.Array([0, 0, dimensione[0], dimensione[1]])
    dati = io.BytesIO()
    pdf.save(dati)
    pdf.close()
    documento = pdfium.PdfDocument(dati.getvalue())
    try:
        return documento[0].render(scale=1).to_pil().convert("L")
    finally:
        documento.close()


def _escursione(immagine, rettangolo) -> int:
    minimo, massimo = immagine.crop(rettangolo).getextrema()
    return massimo - minimo


# ------------------------------------------------ 1. i pixel sotto il rettangolo


@pytest.mark.parametrize("formato", ["grigio", "colori", "bilivello", "jpeg", "fax"])
def test_i_pixel_del_dato_spariscono_dall_immagine_incorporata(tmp_path, formato):
    """**Coprire non e' cancellare.** Si guarda l'XObject, non la pagina.

    Cinque formati perche' sono strade diverse nel codice: i campioni
    azzerati al loro posto (a una componente, a tre, a un bit solo), il JPEG
    riaperto, il fax passato da un'immagine. Una prova sola lascerebbe le
    altre al buio.
    """
    dentro = _scansione_con_ocr(tmp_path / "dentro.pdf", formato=formato)
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())
    assert esito.pagine_coperte_sull_ocr == [0], esito

    dove = _riquadri(RIGHE, [CF, IBAN, RIGHE[0], RIGHE[3]])
    prima = _immagine_estratta(dentro)
    dopo = _immagine_estratta(fuori)

    # Il banco deve poter dire di no: sul file di partenza l'inchiostro c'e'.
    for valore in (CF, IBAN):
        assert _escursione(prima, _dritta(dove[valore])) > INCHIOSTRO, (
            "il foglio di prova non ha inchiostro sotto il valore: il banco "
            "non misurerebbe niente")

    for valore in (CF, IBAN):
        assert _escursione(dopo, _dritta(dove[valore])) <= PIATTO, (
            f"i pixel di {valore[:4]}... sono ancora dentro l'immagine "
            f"incorporata ({formato}): il rettangolo li copre, non li toglie")

    # E la riga che impedisce di «correggere» azzerando tutto il foglio: cio'
    # che non e' un dato resta com'era. **Com'era**, non «con dell'inchiostro
    # dentro»: un'immagine riscritta in negativo, o spostata di una riga,
    # avrebbe ancora dell'inchiostro e sarebbe un altro documento.
    tolleranza = 48 if formato == "jpeg" else 0
    for riga in (RIGHE[0], RIGHE[3]):
        zona = _dritta(dove[riga])
        assert _escursione(dopo, zona) > INCHIOSTRO, (
            f"sparita anche «{riga}», che non andava toccata")
        scarto = ImageChops.difference(prima.crop(zona), dopo.crop(zona)).getextrema()[1]
        assert scarto <= tolleranza, (
            f"«{riga}» non e' piu' quella di prima ({formato}): scarto {scarto}")


def test_la_zona_azzerata_deborda_un_poco_dal_riquadro(tmp_path):
    """Lo strato OCR non e' un righello: ai bordi si toglie un po' di piu'.

    Riproducendo il primo caso con un foglio scritto davvero, dell'ultima
    lettera del codice fiscale restava fuori una fetta: il riquadro finiva
    dove lo strato OCR diceva che finiva la parola, e l'inchiostro andava
    mezzo punto oltre.

    Il foglio qui e' fatto apposta: l'IBAN e' una fascia che deborda di due
    punti e mezzo per lato dal riquadro che lo strato OCR dichiara, e
    l'inchiostro e' **grigio**. Sul pettine nero degli altri banchi una fetta
    rimasta e una fetta azzerata hanno lo stesso colore, e questa prova
    restava verde anche togliendo il margine.
    """
    inchiostro = 100
    dove = _riquadri(RIGHE, [IBAN, "IBAN"])
    sinistra, basso, destra, alto = dove[IBAN]
    fascia = _dritta((sinistra - 2.4, basso, destra + 2.4, alto))
    accanto = _dritta(dove["IBAN"])

    immagine = Image.new("L", (LARGO * SCALA, ALTO * SCALA), 255)
    disegno = ImageDraw.Draw(immagine)
    for x0, y0, x1, y1 in (fascia, accanto):
        disegno.rectangle((x0, y0, x1 - 1, y1 - 1), fill=inchiostro)

    pdf = pikepdf.Pdf.new()
    _aggiungi_pagina(pdf, IMMAGINE_PIENA + _comandi_di_testo(RIGHE, invisibile=True),
                     xobject={"/Im0": _incorpora(pdf, immagine)})
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())
    dopo = _immagine_estratta(fuori)

    assert inchiostro not in set(dopo.crop(fascia).getdata()), (
        "ai lati del riquadro e' rimasta una fetta dell'inchiostro di prima")
    # E non si mangia la parola accanto: «IBAN» sta prima dello spazio.
    assert set(dopo.crop(accanto).getdata()) == {inchiostro}, (
        "il margine si e' mangiato la parola accanto al valore")


def test_un_immagine_di_traverso_si_azzera_nel_punto_giusto(tmp_path):
    """La matrice dell'immagine non e' sempre «larga quanto la pagina».

    Un foglio scansionato di traverso arriva con una rotazione di novanta
    gradi nella matrice: se i conti la ignorassero si azzererebbe il punto
    sbagliato, e il dato resterebbe accanto a un buco nero.
    """
    immagine = _foglio(RIGHE, in_pixel=_ruotata,
                       dimensione=(ALTO * SCALA, LARGO * SCALA))
    pdf = pikepdf.Pdf.new()
    # Due `cm` di fila, come li scrive un programma vero: prima lo
    # spostamento, poi la rotazione con la scala. Insieme fanno
    # `0 842 -595 0 595 0`; composti nell'ordine sbagliato fanno un'altra
    # matrice, e con un `cm` solo l'ordine non si potrebbe sbagliare.
    _aggiungi_pagina(
        pdf,
        ["q", f"1 0 0 1 {LARGO} 0 cm", f"0 {ALTO} -{LARGO} 0 0 0 cm", "/Im0 Do", "Q"]
        + _comandi_di_testo(RIGHE, invisibile=True),
        xobject={"/Im0": _incorpora(pdf, immagine)})
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())

    dove = _riquadri(RIGHE, [CF, IBAN, RIGHE[0]])
    dopo = _immagine_estratta(fuori)
    for valore in (CF, IBAN):
        assert _escursione(dopo, _ruotata(dove[valore])) <= PIATTO, (
            f"{valore[:4]}... ancora nei pixel dell'immagine ruotata")
    assert _escursione(dopo, _ruotata(dove[RIGHE[0]])) > INCHIOSTRO


def test_anche_l_immagine_dentro_un_form_xobject(tmp_path):
    """Diversi programmi avvolgono la scansione in un Form XObject.

    Li' l'immagine non sta fra le risorse della pagina ma un livello sotto, e
    la matrice che la posiziona e' il prodotto di quelle incontrate scendendo.
    """
    pdf = pikepdf.Pdf.new()
    modulo_xobject = pdf.make_stream(
        f"q {LARGO} 0 0 {ALTO} 0 0 cm /Im0 Do Q".encode("latin-1"))
    modulo_xobject.Type = pikepdf.Name("/XObject")
    modulo_xobject.Subtype = pikepdf.Name("/Form")
    modulo_xobject.BBox = pikepdf.Array([0, 0, LARGO, ALTO])
    # Il form ha una matrice sua, e la pagina lo disegna spostato del
    # contrario: l'immagine finisce a tutta pagina solo se le tre matrici si
    # compongono tutte, e nell'ordine giusto.
    modulo_xobject.Matrix = pikepdf.Array([1, 0, 0, 1, -40, -70])
    modulo_xobject.Resources = pikepdf.Dictionary(
        XObject=pikepdf.Dictionary(Im0=_incorpora(pdf, _foglio(RIGHE))))
    _aggiungi_pagina(
        pdf,
        ["q", "1 0 0 1 40 70 cm", "/Fm0 Do", "Q"] + _comandi_di_testo(RIGHE, invisibile=True),
        xobject={"/Fm0": modulo_xobject})
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())
    assert esito.pagine_coperte_sull_ocr == [0], esito

    dove = _riquadri(RIGHE, [CF, IBAN])
    dopo = _immagine_estratta(fuori, dentro="/Fm0")
    for valore in (CF, IBAN):
        assert _escursione(dopo, _dritta(dove[valore])) <= PIATTO, (
            f"{valore[:4]}... ancora nei pixel dell'immagine dentro il form")
    assert verifica_redazione(dentro, fuori, PrivacyOptions())["sopravvissuti"] == 0


def test_un_immagine_che_non_si_sa_aprire_fa_dichiarare_la_pagina(tmp_path):
    """Se i pixel non si possono azzerare, la pagina **non e' trattata**.

    Prima usciva fra le «coperte»: un rettangolo sopra un'immagine intatta.
    Il rifiuto e' la risposta scarsa e l'unica vera, e deve arrivare prima di
    toccare il testo -- una pagina dichiarata non trattata resta com'era.
    """
    dentro = _scansione_con_ocr(tmp_path / "dentro.pdf", formato="illeggibile")
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    assert esito.pagine_coperte_sull_ocr == [], (
        "dichiarata coperta una pagina la cui immagine non e' stata toccata")
    assert esito.pagine_in_ripiego == [0], esito
    assert esito.motivi_ripiego == [modulo.MOTIVO_OCR], esito.motivi_ripiego


def test_un_immagine_in_linea_fa_dichiarare_la_pagina(tmp_path):
    """Un'immagine scritta **dentro** il flusso non e' un oggetto da riscrivere.

    Si sa dov'e' e non la si puo' toccare senza riscrivere il flusso intorno:
    la pagina si dichiara, come per il formato che non si sa aprire.
    """
    pdf = pikepdf.Pdf.new()
    in_linea = (f"q {LARGO} 0 0 {ALTO} 0 0 cm "
                "BI /W 2 /H 2 /CS /G /BPC 8 /F /AHx ID 00FF FF00 > EI Q")
    _aggiungi_pagina(pdf, [in_linea] + _comandi_di_testo(RIGHE, invisibile=True))
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    esito = redigi_pdf(dentro, tmp_path / "fuori.pdf", PrivacyOptions())
    assert esito.pagine_coperte_sull_ocr == [], esito
    assert esito.pagine_in_ripiego == [0], esito
    assert esito.motivi_ripiego == [modulo.MOTIVO_OCR], esito.motivi_ripiego


def test_anche_la_maschera_dell_immagine_si_azzera(tmp_path):
    """In una scansione compressa a livelli le lettere stanno nella maschera.

    Il colore e' una macchia e la **forma** e' la maschera: azzerando solo il
    colore il valore resterebbe leggibile nella sagoma.
    """
    pdf = pikepdf.Pdf.new()
    immagine = _incorpora(pdf, Image.new("L", (LARGO * SCALA, ALTO * SCALA), 40))
    immagine.SMask = _incorpora(pdf, _foglio(RIGHE))
    _aggiungi_pagina(pdf, IMMAGINE_PIENA + _comandi_di_testo(RIGHE, invisibile=True),
                     xobject={"/Im0": immagine})
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())

    with pikepdf.open(str(fuori)) as redatto:
        maschera = redatto.pages[0].obj["/Resources"]["/XObject"]["/Im0"]["/SMask"]
        dopo = Image.frombytes(
            "L", (int(maschera.Width), int(maschera.Height)),
            zlib.decompress(maschera.read_raw_bytes()))
    dove = _riquadri(RIGHE, [CF, IBAN, RIGHE[0]])
    for valore in (CF, IBAN):
        assert _escursione(dopo, _dritta(dove[valore])) <= PIATTO, (
            f"la sagoma di {valore[:4]}... e' ancora nella maschera")
    assert _escursione(dopo, _dritta(dove[RIGHE[0]])) > INCHIOSTRO


def test_un_valore_su_due_righe_si_azzera_su_tutte_e_due(tmp_path):
    """Un indirizzo che va a capo: un riquadro per riga, non uno saltato.

    Prima un valore a cavallo di due righe non aveva nessun riquadro — uno
    solo sarebbe stato alto quanto le due e avrebbe coperto il testo in mezzo
    — e la pagina usciva lo stesso fra le coperte.
    """
    righe = ["Il sottoscritto, residente in Via Giuseppe Garibaldi 12,",
             "95100 Catania (CT) dichiara quanto segue."]
    dentro = _scansione_con_ocr(tmp_path / "dentro.pdf", righe=righe)
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())
    assert esito.pagine_coperte_sull_ocr == [0], esito

    dove = _riquadri(righe, ["Via Giuseppe Garibaldi 12", "95100 Catania",
                             "Il sottoscritto", "dichiara quanto segue"])
    dopo = _immagine_estratta(fuori)
    for pezzo in ("Via Giuseppe Garibaldi 12", "95100 Catania"):
        assert _escursione(dopo, _dritta(dove[pezzo])) <= PIATTO, (
            f"«{pezzo}» e' ancora nei pixel: il valore andava a capo")
    for pezzo in ("Il sottoscritto", "dichiara quanto segue"):
        assert _escursione(dopo, _dritta(dove[pezzo])) > INCHIOSTRO, (
            f"sparito anche «{pezzo}», che non e' un dato")


def test_un_valore_visibile_accanto_non_salva_i_pixel_degli_altri(tmp_path):
    """Scansione con OCR **piu'** un timbro di testo vero con un nome dentro.

    La pagina non e' «tutta invisibile», e prima bastava questo a mandarla
    per la strada delle pagine digitali: via i glifi, rettangolo sul
    segnaposto, e il codice fiscale intero nei pixel.
    """
    pdf = pikepdf.Pdf.new()
    # `0 Tr` va scritto: il modo di rendering non si azzera con `ET`, e senza
    # il timbro resterebbe invisibile come lo strato OCR che lo precede. La
    # prima stesura di questo banco lo dimenticava, e restava verde anche
    # rimettendo la regola vecchia: non provava niente.
    _aggiungi_pagina(
        pdf,
        IMMAGINE_PIENA + _comandi_di_testo(RIGHE, invisibile=True)
        + ["BT 0 Tr /F1 9 Tf 1 0 0 1 60 40 Tm (Firmato digitalmente da Mario Rossi) Tj ET"],
        xobject={"/Im0": _incorpora(pdf, _foglio(RIGHE))})
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())

    dove = _riquadri(RIGHE, [CF, IBAN])
    dopo = _immagine_estratta(fuori)
    for valore in (CF, IBAN):
        assert _escursione(dopo, _dritta(dove[valore])) <= PIATTO, (
            f"{valore[:4]}... ancora nei pixel: il timbro visibile ha fatto "
            "trattare la pagina come se fosse digitale")
    assert "Mario Rossi" not in "\n".join(_testo_per_pagina(fuori))


def test_i_bit_accanto_alla_zona_restano_com_erano():
    """In un'immagine a un bit per pixel ogni byte ne porta otto.

    Una zona che non comincia su un multiplo di otto deve lasciare intatti i
    vicini nello stesso byte: azzerarli vorrebbe dire mangiare fino a sette
    pixel del testo accanto, a sinistra e a destra, su ogni riga.
    """
    # Due righe da tre byte, tutte a uno. Si azzerano i bit da 3 a 13 della
    # seconda riga soltanto.
    dati = bytearray(b"\xff" * 6)
    modulo._azzera_i_bit(dati, 3, 3, 13, 1, 2)
    assert bytes(dati[:3]) == b"\xff\xff\xff", "toccata la riga sopra"
    assert bytes(dati[3:]) == bytes([0b11100000, 0b00000111, 0xFF]), (
        f"bit sbagliati: {[bin(b) for b in dati[3:]]}")

    # Dentro un byte solo: i bit 2, 3 e 4.
    dati = bytearray(b"\xff")
    modulo._azzera_i_bit(dati, 1, 2, 5, 0, 1)
    assert dati[0] == 0b11000111, bin(dati[0])

    # Una zona larga quattro byte interi, per la strada veloce.
    dati = bytearray(b"\xff" * 6)
    modulo._azzera_i_bit(dati, 6, 8, 40, 0, 1)
    assert bytes(dati) == b"\xff\x00\x00\x00\x00\xff", dati.hex()


def _verde(colore) -> bool:
    atteso = [round(c * 255) for c in modulo.COLORE_RETTANGOLO]
    return all(abs(colore[i] - atteso[i]) <= 40 for i in range(3))


def test_il_rettangolo_copre_il_valore_anche_alla_terza_riga(tmp_path):
    """Il caso 1 bis: il rettangolo scivolava di un carattere a ogni a capo.

    Qui si guarda la pagina **resa**, perche' la domanda e' un'altra: non se
    il dato e' ancora nel file, ma se chi apre il documento vede coperto il
    punto giusto. Tre quote per valore, e l'ultima e' quella che cadeva.
    """
    dentro = _scansione_con_ocr(tmp_path / "dentro.pdf")
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())

    documento = pdfium.PdfDocument(str(fuori))
    try:
        resa = documento[0].render(scale=SCALA).to_pil().convert("RGB")
    finally:
        documento.close()

    dove = _riquadri(RIGHE, [CF, IBAN])
    for valore in (CF, IBAN):
        sinistra, basso, destra, alto = dove[valore]
        # Sul filo alto del riquadro e non al centro: al centro c'e'
        # l'etichetta, scritta in bianco, e un pixel bianco li' non vuol dire
        # «scoperto».
        y = alto + 0.5
        for quota in (0.03, 0.5, 0.97):
            x = sinistra + (destra - sinistra) * quota
            colore = resa.getpixel((int(x * SCALA), int((ALTO - y) * SCALA)))
            assert _verde(colore), (
                f"{valore[:4]}... scoperto al {quota:.0%} della sua lunghezza "
                f"({x:.0f}, {y:.0f}): {colore}")


def test_la_verifica_guarda_l_immagine_estratta(tmp_path):
    """**Un controllo che non puo' dire di no non e' un controllo.**

    Il file «redatto male» e' quello che la 1.30.0 produceva: testo
    invisibile sparito, immagine intatta. La verifica leggeva il testo, non
    trovava niente e diceva zero.
    """
    dentro = _scansione_con_ocr(tmp_path / "dentro.pdf")

    male = tmp_path / "male.pdf"
    pdf = pikepdf.Pdf.new()
    r, v, b = modulo.COLORE_RETTANGOLO
    _aggiungi_pagina(
        pdf,
        IMMAGINE_PIENA + [f"q {r} {v} {b} rg 50 700 500 60 re f Q"],
        xobject={"/Im0": _incorpora(pdf, _foglio(RIGHE))})
    pdf.save(str(male))
    pdf.close()

    esito = verifica_redazione(dentro, male, PrivacyOptions())
    assert esito["sopravvissuti"] >= 2, esito
    assert esito["nei_pixel"] >= 2, esito
    assert any(IBAN in e for e in esito["esempi"]), esito
    assert esito["pagine_con_superstiti"] == [0], esito

    # E sul file redatto davvero dice zero: il no di sopra non e' un no fisso.
    bene = tmp_path / "bene.pdf"
    redigi_pdf(dentro, bene, PrivacyOptions())
    pulito = verifica_redazione(dentro, bene, PrivacyOptions())
    assert pulito["sopravvissuti"] == 0, pulito
    assert pulito["nei_pixel"] == 0, pulito


def test_la_verifica_non_scambia_l_eco_di_un_jpeg_per_un_dato(tmp_path):
    """Un JPEG azzerato dev'essere **piatto**, o la verifica ferma un file a posto.

    Un JPEG si comprime a blocchi. Un blocco meta' azzerato e meta' scritto,
    ricompresso, porta nella parte azzerata l'eco della parte scritta: non e'
    il dato — e' la parola accanto, che nel file c'e' comunque — ma la
    verifica chiede una zona piatta. Per questo la zona si allarga fino al
    blocco.

    Misurato su questo foglio, in corpo 5: escursione **0** con
    l'allineamento, **7** senza, e la verifica tollera 8. Senza, cioe', una
    redazione riuscita sta a un passo dall'essere fermata, e basta un JPEG
    compresso un po' di piu' per passare il segno. Il limite qui e' 2, non 8:
    a 8 questa prova restava verde anche togliendo l'allineamento.
    """
    righe = [f"Bonifico sul conto {IBAN} intestato al contribuente",
             f"con codice fiscale {CF} residente a Catania"]
    dentro = _scansione_con_ocr(tmp_path / "dentro.pdf", righe=righe,
                                formato="jpeg", corpo=5)
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())
    assert esito.pagine_coperte_sull_ocr == [0], esito

    dove = _riquadri(righe, [CF, IBAN], corpo=5)
    dopo = _immagine_estratta(fuori)
    for valore in (CF, IBAN):
        assert _escursione(dopo, _dritta(dove[valore])) <= 2, (
            f"la zona di {valore[:4]}... non e' piatta: l'eco del blocco accanto")

    controllo = verifica_redazione(dentro, fuori, PrivacyOptions())
    assert controllo["nei_pixel"] == 0, controllo
    assert controllo["sopravvissuti"] == 0, controllo

    # E resta un banco che sa dire di no: sulla copia non redatta li trova.
    male = tmp_path / "male.pdf"
    with pikepdf.open(str(dentro)) as pdf:
        pdf.pages[0].obj["/Contents"] = pdf.make_stream(" ".join(IMMAGINE_PIENA).encode())
        pdf.save(str(male))
    assert verifica_redazione(dentro, male, PrivacyOptions())["nei_pixel"] >= 2


def test_un_immagine_che_la_verifica_non_riesce_a_estrarre_e_un_no(tmp_path, monkeypatch):
    """«Non ho potuto guardare» non e' «non c'era niente».

    Se l'immagine sotto il valore non si estrae, la verifica non sa cosa c'e'
    dentro: rispondere zero sarebbe il silenzio con la faccia della garanzia.
    """
    dentro = _scansione_con_ocr(tmp_path / "dentro.pdf")
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())
    assert verifica_redazione(dentro, fuori, PrivacyOptions())["nei_pixel"] == 0

    monkeypatch.setattr(modulo, "_immagine_secondo_pdfium", lambda oggetto: None)
    esito = verifica_redazione(dentro, fuori, PrivacyOptions())
    assert esito["nei_pixel"] >= 2, esito
    assert esito["sopravvissuti"] >= 2, esito


# ----------------------------------------------------- 2. la miniatura di pagina


def _miniatura(pdf):
    oggetto = _incorpora(pdf, _foglio(RIGHE).resize((149, 211)))
    del oggetto["/Type"]
    del oggetto["/Subtype"]
    return oggetto


def _pdf_con_miniature(percorso):
    pdf = pikepdf.Pdf.new()
    _aggiungi_pagina(pdf, _comandi_di_testo(RIGHE, invisibile=False),
                     extra={"/Thumb": _miniatura(pdf)})
    # Anche sulla pagina senza un solo valore: la miniatura e' un'immagine, e
    # di cosa ci sia dentro qui non si sa niente.
    _aggiungi_pagina(pdf, _comandi_di_testo(["Una pagina senza dati."], invisibile=False),
                     extra={"/Thumb": _miniatura(pdf)})
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _miniature_nel_file(percorso) -> tuple[list[int], int]:
    """(pagine che hanno ancora `/Thumb`, flussi larghi 149 rimasti nel file)."""
    with pikepdf.open(str(percorso)) as pdf:
        pagine = [n for n, pagina in enumerate(pdf.pages) if "/Thumb" in pagina.obj]
        orfani = sum(1 for oggetto in pdf.objects
                     if isinstance(oggetto, pikepdf.Stream)
                     and oggetto.get("/Width") == 149)
        return pagine, orfani


def test_la_miniatura_di_pagina_non_esce(tmp_path):
    dentro = _pdf_con_miniature(tmp_path / "dentro.pdf")
    assert _miniature_nel_file(dentro) == ([0, 1], 2), "il file di prova non ha miniature"

    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    pagine, orfani = _miniature_nel_file(fuori)
    assert pagine == [], f"la miniatura della pagina originale e' ancora li': {pagine}"
    assert orfani == 0, "tolta la chiave, il flusso della miniatura e' rimasto nel file"
    assert esito.miniature_tolte == 2, esito


def test_la_verifica_dice_di_no_su_una_miniatura_rimasta(tmp_path):
    dentro = _pdf_con_miniature(tmp_path / "dentro.pdf")
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())
    assert verifica_redazione(dentro, fuori, PrivacyOptions())["sopravvissuti"] == 0

    # La stessa redazione, con la miniatura rimessa al suo posto.
    male = tmp_path / "male.pdf"
    with pikepdf.open(str(fuori)) as pdf:
        pdf.pages[0].obj["/Thumb"] = _miniatura(pdf)
        pdf.save(str(male))

    esito = verifica_redazione(dentro, male, PrivacyOptions())
    assert esito["sopravvissuti"] >= 1, esito
    assert esito["miniature_rimaste"] == [0], esito
    assert 0 in esito["pagine_con_superstiti"], esito


# ------------------------------------------------------ 3. il testo di struttura


def _pdf_con_struttura(percorso, righe=("Una riga qualunque senza niente dentro.",)):
    """Un albero di struttura a due livelli, con i dati nelle quattro chiavi."""
    pdf = pikepdf.Pdf.new()
    _aggiungi_pagina(pdf, _comandi_di_testo(list(righe), invisibile=False))
    radice = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name("/StructTreeRoot")))

    def elemento(genitore, **chiavi):
        dizionario = pikepdf.Dictionary(
            Type=pikepdf.Name("/StructElem"), S=pikepdf.Name("/Span"), P=genitore)
        for chiave, testo in chiavi.items():
            dizionario["/" + chiave] = pikepdf.String(testo)
        return pdf.make_indirect(dizionario)

    sezione = elemento(radice, T="Scheda di Mario Rossi")
    sezione["/K"] = pikepdf.Array([
        elemento(sezione, ActualText="NETTO IN BUSTA 1.612,34"),
        elemento(sezione, Alt=f"IBAN {IBAN}"),
        elemento(sezione, E=f"codice fiscale {CF}"),
        elemento(sezione, Alt="Logo dell'azienda"),
        # Un riferimento a contenuto marcato: un intero, non un elemento.
        0,
    ])
    radice["/K"] = pikepdf.Array([sezione])
    pdf.Root["/StructTreeRoot"] = radice
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _testi_di_struttura(percorso) -> list[str]:
    """Le stringhe dell'albero, lette a mano e non con la funzione del modulo."""
    with pikepdf.open(str(percorso)) as pdf:
        sezione = pdf.Root["/StructTreeRoot"]["/K"][0]
        fuori = [str(sezione["/T"])]
        for figlio in sezione["/K"]:
            if not isinstance(figlio, pikepdf.Dictionary):
                continue
            for chiave in ("/ActualText", "/Alt", "/E"):
                if chiave in figlio:
                    fuori.append(str(figlio[chiave]))
        return fuori


def test_il_testo_di_struttura_passa_dal_filtro(tmp_path):
    dentro = _pdf_con_struttura(tmp_path / "dentro.pdf")
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    testi = "\n".join(_testi_di_struttura(fuori))
    assert IBAN not in testi, f"IBAN ancora in /Alt: {testi}"
    assert CF not in testi, f"codice fiscale ancora in /E: {testi}"
    assert "Mario Rossi" not in testi, f"nome ancora in /T: {testi}"
    assert esito.struttura_tolti == 3, esito
    assert esito.valori_da_togliere >= 3, esito

    # Cio' che il filtro non riconosce resta identico: l'albero serve a chi
    # legge con uno screen reader, e non si svuota per prudenza.
    assert "Logo dell'azienda" in testi
    assert "NETTO IN BUSTA 1.612,34" in testi, (
        "gli importi sono spenti di default: questa stringa doveva restare")


def test_con_gli_importi_accesi_sparisce_anche_il_netto(tmp_path):
    dentro = _pdf_con_struttura(tmp_path / "dentro.pdf")
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions(amounts=True))
    assert "1.612,34" not in "\n".join(_testi_di_struttura(fuori))


def test_la_verifica_guarda_anche_il_testo_di_struttura(tmp_path):
    dentro = _pdf_con_struttura(tmp_path / "dentro.pdf")
    # «Redatto male»: una copia identica, albero compreso.
    male = tmp_path / "male.pdf"
    shutil.copyfile(dentro, male)

    esito = verifica_redazione(dentro, male, PrivacyOptions())
    assert esito["sopravvissuti"] >= 3, esito
    assert any(IBAN in e for e in esito["esempi"]), esito

    bene = tmp_path / "bene.pdf"
    redigi_pdf(dentro, bene, PrivacyOptions())
    assert verifica_redazione(dentro, bene, PrivacyOptions())["sopravvissuti"] == 0


# -------------------------------------- 4. la pagina-immagine con poco testo sopra


PIE_DI_PAGINA = "Documento generato dal portale del personale aziendale"


def _pagina_immagine_con_pie(pdf, righe_del_foglio=RIGHE, pie=PIE_DI_PAGINA):
    _aggiungi_pagina(
        pdf,
        IMMAGINE_PIENA + [f"BT /F1 8 Tf 1 0 0 1 60 30 Tm ({pie}) Tj ET"],
        xobject={"/Im0": _incorpora(pdf, _foglio(righe_del_foglio))})


def _pdf_con_pagina_immagine(percorso, prima_digitale: bool = True):
    pdf = pikepdf.Pdf.new()
    if prima_digitale:
        _aggiungi_pagina(pdf, _comandi_di_testo(
            [f"Il contribuente C.F. {CF} dichiara."], invisibile=False))
    _pagina_immagine_con_pie(pdf)
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def test_una_pagina_immagine_con_una_riga_di_testo_si_dichiara(tmp_path):
    """Sette parole di pie' di pagina non fanno di un'immagine una pagina letta."""
    dentro = _pdf_con_pagina_immagine(tmp_path / "dentro.pdf")
    assert PIE_DI_PAGINA in _testo_per_pagina(dentro)[1], "il testo doveva essere estraibile"

    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    assert esito.pagine_in_ripiego == [1], (
        f"la pagina-immagine e' uscita fra le trattate: {esito}")
    assert esito.motivi_ripiego == [modulo.MOTIVO_IMMAGINE], esito.motivi_ripiego
    assert not esito.scansione, "la prima pagina e' digitale: il documento si consegna"
    assert CF not in _testo_per_pagina(fuori)[0], "la pagina digitale va comunque redatta"


def _pagina_con_figura(pdf, quota_del_foglio: float):
    """Una pagina con un'immagine centrata che copre quella quota del foglio."""
    lato = quota_del_foglio ** 0.5
    larghezza, altezza = LARGO * lato, ALTO * lato
    x, y = (LARGO - larghezza) / 2, (ALTO - altezza) / 2
    _aggiungi_pagina(
        pdf,
        ["q", f"{larghezza:.2f} 0 0 {altezza:.2f} {x:.2f} {y:.2f} cm", "/Im0 Do", "Q",
         f"BT /F1 8 Tf 1 0 0 1 60 30 Tm ({PIE_DI_PAGINA}) Tj ET"],
        xobject={"/Im0": _incorpora(pdf, Image.new("L", (60, 84), 180))})


@pytest.mark.parametrize("quota, dichiarata", [(0.70, True), (0.30, False)])
def test_la_soglia_sta_a_meta_pagina(tmp_path, quota, dichiarata):
    """Meta' pagina, misurata dai due lati.

    Il 70% e' la scansione incollata in un documento di testo e uscita in PDF
    con i margini del documento attorno: e' lei la ragione per cui la soglia
    non e' «tutta la pagina». Il 30% e' una figura con la sua didascalia in
    una relazione, e dichiarare quella vorrebbe dire dichiarare mezzo
    documento.
    """
    pdf = pikepdf.Pdf.new()
    _aggiungi_pagina(pdf, _comandi_di_testo(
        [f"Il contribuente C.F. {CF} dichiara."], invisibile=False))
    _pagina_con_figura(pdf, quota)
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    esito = redigi_pdf(dentro, tmp_path / "fuori.pdf", PrivacyOptions())
    assert esito.pagine_in_ripiego == ([1] if dichiarata else []), (
        f"immagine al {quota:.0%} del foglio: {esito.motivi_ripiego}")


def test_un_documento_di_sole_pagine_immagine_e_una_scansione(tmp_path):
    """Stessa regola delle scansioni: se non c'e' una pagina trattata, si rifiuta."""
    dentro = _pdf_con_pagina_immagine(tmp_path / "dentro.pdf", prima_digitale=False)
    esito = redigi_pdf(dentro, tmp_path / "fuori.pdf", PrivacyOptions())
    assert esito.pagine_in_ripiego == [0], esito
    assert esito.scansione, f"un documento tutto di pagine-immagine non e' redatto: {esito}"


def test_un_nome_nel_timbro_non_fa_passare_la_pagina_per_trattata(tmp_path):
    """La pagina si dichiara **prima** di guardare se nel testo ci sono valori.

    Con un valore nel timbro si toglierebbe quello e la pagina uscirebbe
    «trattata»: il cedolino nell'immagine nessuno l'ha guardato.
    """
    pdf = pikepdf.Pdf.new()
    _aggiungi_pagina(pdf, _comandi_di_testo(["Pagina digitale senza dati."], invisibile=False))
    _pagina_immagine_con_pie(pdf, pie="Firmato digitalmente da Mario Rossi")
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    esito = redigi_pdf(dentro, tmp_path / "fuori.pdf", PrivacyOptions())
    assert esito.pagine_in_ripiego == [1], esito
    assert esito.motivi_ripiego == [modulo.MOTIVO_IMMAGINE], esito.motivi_ripiego


def test_una_pagina_di_testo_su_uno_sfondo_resta_trattata(tmp_path):
    """La riga che impedisce di dichiarare ogni pagina con un fondo a immagine.

    Una carta intestata fatta di un'immagine a tutta pagina, con sopra una
    lettera vera: il testo **e'** la pagina, e l'immagine e' lo sfondo.
    """
    lettera = [f"Riga {n} della lettera, scritta per esteso e fino in fondo."
               for n in range(1, 25)] + [f"Codice fiscale {CF}"]
    pdf = pikepdf.Pdf.new()
    _aggiungi_pagina(
        pdf, IMMAGINE_PIENA + _comandi_di_testo(lettera, invisibile=False, corpo=12),
        xobject={"/Im0": _incorpora(pdf, Image.new("L", (60, 84), 235))})
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())
    assert esito.pagine_in_ripiego == [], esito.motivi_ripiego
    assert CF not in "\n".join(_testo_per_pagina(fuori))
    assert verifica_redazione(dentro, fuori, PrivacyOptions())["sopravvissuti"] == 0


def test_la_verifica_dice_di_no_su_una_pagina_immagine(tmp_path):
    """Qui non c'e' un valore da cercare: c'e' una pagina che nessuno ha letto.

    La verifica la nomina fra quelle con superstiti, e sta a chi chiama
    confrontarla con le pagine dichiarate: dichiarata, il file si consegna;
    taciuta, no. E' lo stesso patto dei valori rimasti nel testo.
    """
    dentro = _pdf_con_pagina_immagine(tmp_path / "dentro.pdf")
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    controllo = verifica_redazione(dentro, fuori, PrivacyOptions())
    assert controllo["pagine_immagine"] == [1], controllo
    assert controllo["sopravvissuti"] >= 1, controllo
    assert 1 in controllo["pagine_con_superstiti"], controllo
    # Dichiarata: niente di taciuto, quindi niente da fermare.
    assert set(controllo["pagine_con_superstiti"]) <= set(esito.pagine_in_ripiego)


def test_una_scansione_dentro_un_form_xobject_e_una_scansione(tmp_path):
    """Pagina senza testo, con l'immagine un livello sotto le risorse.

    Si cercava l'immagine solo fra le risorse della pagina: avvolta in un
    form non si vedeva, e la pagina usciva come una pagina bianca.
    """
    pdf = pikepdf.Pdf.new()
    _aggiungi_pagina(pdf, _comandi_di_testo(
        [f"Il contribuente C.F. {CF} dichiara."], invisibile=False))
    modulo_xobject = pdf.make_stream(
        f"q {LARGO} 0 0 {ALTO} 0 0 cm /Im0 Do Q".encode("latin-1"))
    modulo_xobject.Type = pikepdf.Name("/XObject")
    modulo_xobject.Subtype = pikepdf.Name("/Form")
    modulo_xobject.BBox = pikepdf.Array([0, 0, LARGO, ALTO])
    modulo_xobject.Resources = pikepdf.Dictionary(
        XObject=pikepdf.Dictionary(Im0=_incorpora(pdf, _foglio(RIGHE))))
    _aggiungi_pagina(pdf, ["q", "/Fm0 Do", "Q"], xobject={"/Fm0": modulo_xobject})
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    esito = redigi_pdf(dentro, tmp_path / "fuori.pdf", PrivacyOptions())
    assert esito.pagine_in_ripiego == [1], esito
    assert esito.motivi_ripiego == [modulo.MOTIVO_SCANSIONE], esito.motivi_ripiego


# ------------------------------------------- 1 ter. il testo SOTTO l'immagine
#
# Lasciato aperto dalla 1.30.1 e chiuso nella 1.30.2. Alcuni programmi di OCR
# non scrivono il testo riconosciuto in modo invisibile sopra la scansione:
# lo scrivono normale e **poi ci dipingono sopra l'immagine**. Per chi guarda
# la pagina e' la stessa cosa; per il modulo quei glifi «si vedevano», e la
# pagina prendeva la strada delle pagine digitali:
#
#     pagine_in_ripiego [], pagine_coperte_sull_ocr []
#     pixel del codice fiscale ancora nell'immagine estratta
#     verifica_redazione: sopravvissuti 0


def _scansione_con_testo_sotto(percorso, righe=RIGHE):
    """Prima il testo, **visibile**; poi l'immagine a tutta pagina, sopra."""
    pdf = pikepdf.Pdf.new()
    _aggiungi_pagina(pdf, _comandi_di_testo(righe, invisibile=False) + IMMAGINE_PIENA,
                     xobject={"/Im0": _incorpora(pdf, _foglio(righe))})
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def test_il_testo_sotto_l_immagine_vale_come_quello_invisibile(tmp_path):
    """Un glifo coperto da un'immagine dipinta dopo non si vede: il dato e' nei pixel."""
    dentro = _scansione_con_testo_sotto(tmp_path / "dentro.pdf")
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    assert esito.pagine_coperte_sull_ocr == [0], (
        f"la pagina e' stata trattata come digitale: {esito}")
    dove = _riquadri(RIGHE, [CF, IBAN, RIGHE[0]])
    dopo = _immagine_estratta(fuori)
    for valore in (CF, IBAN):
        assert _escursione(dopo, _dritta(dove[valore])) <= PIATTO, (
            f"{valore[:4]}... ancora nei pixel: il testo stava sotto l'immagine")
    assert _escursione(dopo, _dritta(dove[RIGHE[0]])) > INCHIOSTRO
    assert CF not in "\n".join(_testo_per_pagina(fuori))
    assert verifica_redazione(dentro, fuori, PrivacyOptions())["sopravvissuti"] == 0


def test_la_verifica_dice_di_no_sul_testo_sotto_l_immagine(tmp_path):
    """Il file «redatto male» della 1.30.1: testo tolto, immagine intatta.

    La verifica chiedeva a pdfium soltanto il modo di rendering: questi glifi
    sono in modo normale, quindi «si vedevano», e dei pixel non si guardava
    niente.
    """
    dentro = _scansione_con_testo_sotto(tmp_path / "dentro.pdf")
    male = tmp_path / "male.pdf"
    pdf = pikepdf.Pdf.new()
    _aggiungi_pagina(pdf, IMMAGINE_PIENA,
                     xobject={"/Im0": _incorpora(pdf, _foglio(RIGHE))})
    pdf.save(str(male))
    pdf.close()

    esito = verifica_redazione(dentro, male, PrivacyOptions())
    assert esito["nei_pixel"] >= 2, esito
    assert esito["sopravvissuti"] >= 2, esito
    assert any(IBAN in e for e in esito["esempi"]), esito


def test_un_valore_scritto_sopra_lo_sfondo_resta_una_pagina_digitale(tmp_path):
    """La riga che impedisce di trattare da scansione ogni pagina con uno sfondo.

    Un'intestazione, poi lo sfondo a tutta pagina, poi la lettera con i
    valori: qui un'immagine e' disegnata **dopo** del testo, e copre il punto
    in cui stanno i valori. Ma i valori sono scritti dopo di lei, quindi le
    stanno sopra e si vedono: e' l'ordine fra quel valore e quell'immagine
    che conta, non il fatto che nella pagina ci sia del testo prima.

    Nell'intestazione non c'e' nessun dato, ed e' voluto. La prima stesura ci
    metteva un indirizzo, e il banco diventava rosso a ragione: un indirizzo
    scritto prima di uno sfondo opaco **sta sotto lo sfondo**, e quella
    pagina va trattata come le altre di questa sezione.
    """
    lettera = [f"Riga {n} della lettera, scritta per esteso e fino in fondo."
               for n in range(1, 25)] + [f"Codice fiscale {CF}"]
    # Uno sfondo **a righe**, non a tinta unita: sotto i valori dev'esserci
    # qualcosa che non e' piatto, o una verifica che andasse a guardare quei
    # pixel per sbaglio non troverebbe niente da ridire e il banco tacerebbe.
    sfondo = Image.new("L", (LARGO, ALTO), 245)
    disegno = ImageDraw.Draw(sfondo)
    for x in range(0, LARGO, 6):
        disegno.rectangle((x, 0, x + 2, ALTO - 1), fill=215)
    pdf = pikepdf.Pdf.new()
    _aggiungi_pagina(
        pdf,
        ["BT /F1 9 Tf 1 0 0 1 60 800 Tm (Pagina 1 di 3 - copia per il cliente) Tj ET"]
        + IMMAGINE_PIENA
        + _comandi_di_testo(lettera, invisibile=False, corpo=12),
        xobject={"/Im0": _incorpora(pdf, sfondo)})
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())
    assert esito.pagine_coperte_sull_ocr == [], (
        "pagina digitale con uno sfondo trattata come una scansione")
    assert esito.pagine_in_ripiego == [], esito.motivi_ripiego
    assert _immagine_estratta(fuori).tobytes() == sfondo.tobytes(), (
        "lo sfondo e' stato toccato: sotto i valori non c'era niente da togliere")
    assert CF not in "\n".join(_testo_per_pagina(fuori))
    assert verifica_redazione(dentro, fuori, PrivacyOptions())["sopravvissuti"] == 0


def test_un_logo_dipinto_dopo_il_testo_non_fa_una_scansione(tmp_path):
    """Dipinta dopo non vuol dire dipinta **sopra**.

    Molti programmi disegnano il marchio a pie' di pagina per ultimo, dopo
    tutto il testo. Viene dopo i valori, e non li copre: sta da un'altra
    parte del foglio. Senza guardare dove sta, ogni pagina di carta intestata
    finirebbe fra le scansioni da controllare.
    """
    marchio = Image.new("L", (120, 60), 255)
    disegno = ImageDraw.Draw(marchio)
    for x in range(0, 120, 8):
        disegno.rectangle((x, 0, x + 3, 59), fill=0)
    pdf = pikepdf.Pdf.new()
    _aggiungi_pagina(
        pdf,
        _comandi_di_testo(RIGHE, invisibile=False)
        + ["q", "120 0 0 60 400 40 cm", "/Im0 Do", "Q"],
        xobject={"/Im0": _incorpora(pdf, marchio)})
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())
    assert esito.pagine_coperte_sull_ocr == [], (
        "pagina digitale con un marchio in fondo trattata come una scansione")
    assert esito.pagine_in_ripiego == [], esito.motivi_ripiego
    assert _immagine_estratta(fuori).tobytes() == marchio.tobytes(), "marchio toccato"
    assert CF not in "\n".join(_testo_per_pagina(fuori))
    assert verifica_redazione(dentro, fuori, PrivacyOptions())["sopravvissuti"] == 0


def _form(pdf, contenuto: str, risorse) -> "pikepdf.Stream":
    oggetto = pdf.make_stream(contenuto.encode("latin-1"))
    oggetto.Type = pikepdf.Name("/XObject")
    oggetto.Subtype = pikepdf.Name("/Form")
    oggetto.BBox = pikepdf.Array([0, 0, LARGO, ALTO])
    oggetto.Resources = risorse
    return oggetto


@pytest.mark.parametrize("dove_sta_il_testo", ["pagina", "form"])
def test_l_ordine_si_segue_anche_attraverso_un_form(tmp_path, dove_sta_il_testo):
    """Chi viene prima si decide **nel flusso intero**, form compresi.

    Due impaginazioni che si incontrano davvero: il testo sulla pagina e la
    scansione dentro un form disegnato dopo; oppure il testo dentro un form,
    e la scansione sulla pagina dopo di lui. Contando le istruzioni solo
    dentro il proprio contenitore, in tutti e due i casi il confronto si
    farebbe fra numeri che non hanno niente a che vedere l'uno con l'altro.
    """
    pdf = pikepdf.Pdf.new()
    immagine = _incorpora(pdf, _foglio(RIGHE))
    font = pikepdf.Dictionary(F1=_font(pdf))
    testo = "\n".join(_comandi_di_testo(RIGHE, invisibile=False))
    disegna = " ".join(IMMAGINE_PIENA)
    if dove_sta_il_testo == "pagina":
        # Il form con l'immagine e' la terza istruzione di pagina, dopo molte
        # di testo: dentro il form l'immagine e' all'istruzione 1.
        form = _form(pdf, disegna, pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=immagine)))
        comandi = _comandi_di_testo(RIGHE, invisibile=False) + ["q", "/Fm0 Do", "Q"]
        xobject = {"/Fm0": form}
        dentro_il_form = "/Fm0"
    else:
        # Il testo sta in un form disegnato per primo, con molte istruzioni;
        # l'immagine e' la terza istruzione di pagina.
        form = _form(pdf, testo, pikepdf.Dictionary(Font=font))
        comandi = ["/Fm0 Do"] + IMMAGINE_PIENA
        xobject = {"/Fm0": form, "/Im0": immagine}
        dentro_il_form = None
    _aggiungi_pagina(pdf, comandi, xobject=xobject)
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())
    assert esito.pagine_coperte_sull_ocr == [0], esito

    dove = _riquadri(RIGHE, [CF, IBAN])
    dopo = _immagine_estratta(fuori, dentro=dentro_il_form)
    for valore in (CF, IBAN):
        assert _escursione(dopo, _dritta(dove[valore])) <= PIATTO, (
            f"{valore[:4]}... ancora nei pixel (testo nel contenitore «{dove_sta_il_testo}»)")
    assert verifica_redazione(dentro, fuori, PrivacyOptions())["sopravvissuti"] == 0

    # E la verifica segue lo stesso ordine con il suo righello: sul file con
    # il testo tolto e l'immagine intatta dice di no.
    male = tmp_path / "male.pdf"
    with pikepdf.open(str(dentro)) as redatto_male:
        pagina = redatto_male.pages[0].obj
        if dove_sta_il_testo == "pagina":
            pagina["/Contents"] = redatto_male.make_stream(b"q /Fm0 Do Q")
        else:
            pagina["/Resources"]["/XObject"]["/Fm0"].write(b"")
        redatto_male.save(str(male))
    assert verifica_redazione(dentro, male, PrivacyOptions())["nei_pixel"] >= 2


def test_una_firma_sopra_il_nome_si_buca_solo_li(tmp_path):
    """Un'immagine piccola dipinta sopra un valore: il caso della firma.

    Non e' una scansione e non copre la pagina, ma sotto quel pezzo di
    immagine c'e' un valore che non si vede, e in quel pezzo puo' esserci
    scritto lui. Si toglie **quel pezzo**: il resto dell'immagine resta
    com'era, e la pagina si dichiara fra quelle da guardare.
    """
    righe = ["Il sottoscritto dichiara quanto segue.", f"Codice fiscale {CF}"]
    dove = _riquadri(righe, [CF])
    sinistra, basso, destra, alto = dove[CF]
    # La «firma»: 200 x 60 punti, a cavallo della seconda meta' del valore.
    x0, y0, larga, alta = (sinistra + destra) / 2, basso - 20, 200.0, 60.0
    firma = Image.new("L", (int(larga * SCALA), int(alta * SCALA)), 255)
    disegno = ImageDraw.Draw(firma)
    for x in range(0, firma.width, 8):
        disegno.rectangle((x, 0, x + 3, firma.height - 1), fill=0)

    pdf = pikepdf.Pdf.new()
    _aggiungi_pagina(
        pdf,
        _comandi_di_testo(righe, invisibile=False)
        + ["q", f"{larga} 0 0 {alta} {x0:.2f} {y0:.2f} cm", "/Im0 Do", "Q"],
        xobject={"/Im0": _incorpora(pdf, firma)})
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())
    assert esito.pagine_coperte_sull_ocr == [0], esito
    assert CF not in "\n".join(_testo_per_pagina(fuori))

    dopo = _immagine_estratta(fuori)
    # Il pezzo di firma che sta sopra il valore, nei pixel della firma: la
    # firma comincia a meta' valore, quindi a sinistra c'e' il suo bordo.
    sopra_il_valore = (0, int((y0 + alta - alto) * SCALA),
                       int((destra - x0) * SCALA), int((y0 + alta - basso) * SCALA) + 1)
    assert _escursione(dopo, sopra_il_valore) <= PIATTO, (
        "il pezzo di immagine sopra il valore e' rimasto com'era")
    # E lontano dal valore la firma e' quella di prima.
    lontano = (int(150 * SCALA), 0, firma.width, int(10 * SCALA))
    assert dopo.crop(lontano).tobytes() == firma.crop(lontano).tobytes(), (
        "bucata l'immagine anche dove non c'era nessun valore sotto")
    assert verifica_redazione(dentro, fuori, PrivacyOptions())["sopravvissuti"] == 0


# --------------------------------------------------------- dal prodotto, non da qui


def test_lo_scaricamento_consegna_un_immagine_senza_il_dato(tmp_path):
    """La rotta che l'utente usa: il file che arriva ha l'immagine azzerata.

    Passa dalla verifica vera, quindi prova due cose insieme: che la
    correzione c'e', e che il controllo nuovo non ferma un file a posto.
    """
    from mr_rao.app_factory import create_app

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    dentro = _scansione_con_ocr(tmp_path / "dentro.pdf")
    risposta = client.post(
        "/api/export/pdf", base_url="http://127.0.0.1:5000",
        data={"file": (io.BytesIO(dentro.read_bytes()), "cedolino.pdf"), "lang": "it"},
        content_type="multipart/form-data",
    )
    assert risposta.status_code == 200, risposta.get_data(as_text=True)[:300]

    fuori = tmp_path / "scaricato.pdf"
    fuori.write_bytes(risposta.data)
    dove = _riquadri(RIGHE, [CF, IBAN])
    dopo = _immagine_estratta(fuori)
    for valore in (CF, IBAN):
        assert _escursione(dopo, _dritta(dove[valore])) <= PIATTO
