# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Chi ha scritto il documento, e cio' che il programma ci ha lasciato dentro.

Tre cose misurate il 3 ottobre 2026, cercando sugli altri canali il dato che
la 1.30.1 aveva tolto dai pixel. Tutte e tre uscivano dal file redatto, e la
verifica diceva zero.

1. L'autore
-----------

    /Author (mario.rossi)        ->  /Author (mario.rossi), metadati_tolti 0
    nota con /T (Mario Rossi)    ->  /T (Mario Rossi)

`mario.rossi` non e' una forma che il motore riconosce, e nel testo libero
non deve diventarlo: `nome.cognome` e' anche un file, un modulo, un dominio.
Ma `/Author` **non e' testo libero**. E' il campo che dice chi ha scritto, e
li' qualunque valore e' un'identita': non c'e' niente da riconoscere, c'e'
da sapere che campo e'. Lo stesso per `/T` di una nota, che per convenzione
e' il nome di chi l'ha messa — e che non era fra le chiavi di testo delle
annotazioni, perche' sui **campi modulo** `/T` e' il nome del campo e non va
toccato.

Con la casella «Nomi» accesa i due campi escono col segnaposto, per intero.
Il segnaposto e' **suo**, `{{AUTHOR}}`, non quello dei nomi: chi ha scritto
il documento non e' una delle persone di cui il documento parla, e chi
rilegge il redatto deve poterle distinguere.
Spenta, restano: chi ha deciso di tenere i nomi ha deciso anche questo.

2. I dati privati delle applicazioni
------------------------------------

`/PieceInfo` e' lo spazio in cui un programma tiene le sue cose dentro il
PDF. Alcuni programmi di grafica ci tengono una **copia di lavoro del
documento**: il file redatto usciva con l'originale accanto. Si toglie
sempre, come gli allegati, e si conta.

3. L'avviso che non arrivava
----------------------------

`pagine_coperte_sull_ocr` e `allegati_rimossi` uscivano dalla rotta di
anteprima dalla 1.30.0, e l'interfaccia non li leggeva. Un campo che il
pannello non mostra non esiste per chi usa il programma.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import io
import shutil
from pathlib import Path

import pytest

pikepdf = pytest.importorskip("pikepdf")
pytest.importorskip("pypdfium2")

from mr_rao.privacy import PrivacyOptions  # noqa: E402
from mr_rao.redazione_pdf import redigi_pdf, verifica_redazione  # noqa: E402

BASE = "http://127.0.0.1:5000"
CF = "RSSMRA85M01H501Z"
IBAN = "IT60X0542811101000000123456"
RADICE = Path(__file__).resolve().parents[1]


def _pagina(pdf, riga: str = "Una riga qualunque senza niente dentro."):
    font = pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Font"), Subtype=pikepdf.Name("/Type1"),
        BaseFont=pikepdf.Name("/Helvetica"),
        Encoding=pikepdf.Name("/WinAnsiEncoding")))
    pagina = pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)),
        Contents=pdf.make_stream(
            f"BT /F1 11 Tf 1 0 0 1 60 760 Tm ({riga}) Tj ET".encode("latin-1"))))
    pdf.pages.append(pikepdf.Page(pagina))
    return pagina


def _pdf_con_proprieta(percorso, **proprieta: str):
    pdf = pikepdf.Pdf.new()
    _pagina(pdf)
    for chiave, valore in proprieta.items():
        pdf.docinfo["/" + chiave] = valore
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _proprieta(percorso) -> dict[str, str]:
    with pikepdf.open(str(percorso)) as pdf:
        return {str(k): str(v) for k, v in pdf.docinfo.items()
                if isinstance(v, pikepdf.String)}


# --------------------------------------------------------------- 1. l'autore


@pytest.mark.parametrize("autore", [
    "mario.rossi",                 # il caso misurato: il motore non lo riconosce
    "MRossi",
    "rossim",
    "Mario Rossi",                 # questo lo riconosceva gia'
    "m.rossi (Ufficio Tecnico)",   # riconosciuto a meta' resterebbe meta'
])
def test_l_autore_esce_col_segnaposto_qualunque_forma_abbia(tmp_path, autore):
    dentro = _pdf_con_proprieta(tmp_path / "dentro.pdf", Author=autore)
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    assert _proprieta(fuori)["/Author"] == "{{AUTHOR_1}}", _proprieta(fuori)
    assert esito.metadati_tolti >= 1, esito
    assert esito.valori_da_togliere >= 1, esito


def test_a_nomi_spenti_l_autore_resta(tmp_path):
    """Chi ha scelto di tenere i nomi ha scelto anche questo."""
    dentro = _pdf_con_proprieta(tmp_path / "dentro.pdf", Author="mario.rossi")
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions(names=False))
    assert _proprieta(fuori)["/Author"] == "mario.rossi"


def test_senza_numeri_il_segnaposto_e_quello_piatto(tmp_path):
    dentro = _pdf_con_proprieta(tmp_path / "dentro.pdf", Author="mario.rossi")
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions(numerati=False))
    assert _proprieta(fuori)["/Author"] == "{{AUTHOR}}"


def test_un_autore_gia_redatto_non_si_conta_di_nuovo(tmp_path):
    """Redigere un file gia' redatto non deve trovarci un dato nuovo."""
    dentro = _pdf_con_proprieta(tmp_path / "dentro.pdf", Author="{{AUTHOR_1}}")
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())
    assert _proprieta(fuori)["/Author"] == "{{AUTHOR_1}}"
    assert esito.metadati_tolti == 0, esito
    assert verifica_redazione(dentro, fuori, PrivacyOptions())["sopravvissuti"] == 0


def test_il_programma_che_ha_creato_il_file_non_e_un_autore(tmp_path):
    """La riga che impedisce di svuotare tutte le proprieta' per prudenza.

    `/Creator` e' il programma, `/Title` e' il titolo: testo libero, passano
    dal filtro come prima e restano se il filtro non ci trova niente.
    """
    dentro = _pdf_con_proprieta(tmp_path / "dentro.pdf", Author="mario.rossi",
                                Creator="Elaboratore di testi 12.4",
                                Title="Verbale della riunione di ottobre")
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())
    proprieta = _proprieta(fuori)
    assert proprieta["/Creator"] == "Elaboratore di testi 12.4"
    assert proprieta["/Title"] == "Verbale della riunione di ottobre"


def test_l_autore_non_resta_nemmeno_nell_xmp(tmp_path):
    """Il blocco XMP duplica le proprieta': l'autore sta scritto anche li'.

    Con gli URL spenti il filtro non trova niente nell'XMP — di solito a
    farlo buttare sono gli indirizzi degli spazi dei nomi — e il blocco
    restava, con `mario.rossi` dentro.
    """
    pdf = pikepdf.Pdf.new()
    _pagina(pdf)
    with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
        meta["dc:creator"] = ["mario.rossi"]
    pdf.docinfo["/Author"] = "mario.rossi"
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions(urls=False))
    with pikepdf.open(str(fuori)) as redatto:
        xmp = ""
        if "/Metadata" in redatto.Root:
            xmp = bytes(redatto.Root["/Metadata"].read_bytes()).decode("utf-8", "replace")
    assert "mario.rossi" not in xmp, "il nome utente e' ancora nel blocco XMP"


def test_la_verifica_dice_di_no_su_un_autore_rimasto(tmp_path):
    """Qui non c'e' un valore che il motore riconosce: c'e' un campo.

    La verifica cercava nel redatto i valori che il motore trova
    nell'originale. `mario.rossi` il motore non lo trova, quindi non lo
    cercava nessuno: un autore rimasto usciva verde per costruzione.
    """
    dentro = _pdf_con_proprieta(tmp_path / "dentro.pdf", Author="mario.rossi")
    male = tmp_path / "male.pdf"
    shutil.copyfile(dentro, male)

    esito = verifica_redazione(dentro, male, PrivacyOptions())
    assert esito["sopravvissuti"] >= 1, esito
    assert esito["identita_rimaste"] == 1, esito
    # L'autore non sta su nessun foglio: vale come la «pagina» dei metadati.
    assert esito["pagine_con_superstiti"] == [1], esito

    bene = tmp_path / "bene.pdf"
    redigi_pdf(dentro, bene, PrivacyOptions())
    pulito = verifica_redazione(dentro, bene, PrivacyOptions())
    assert pulito["sopravvissuti"] == 0, pulito
    assert pulito["identita_rimaste"] == 0, pulito

    # E a nomi spenti non e' un superstite: nessuno aveva chiesto di toglierlo.
    spenti = verifica_redazione(dentro, male, PrivacyOptions(names=False))
    assert spenti["identita_rimaste"] == 0, spenti


# ------------------------------------------------------ 1. l'autore di una nota


def _pdf_con_nota(percorso, autore: str = "mario.rossi", campo: bool = False):
    """Una nota a margine con il suo autore; o un campo modulo, che ha `/T` anche lui."""
    pdf = pikepdf.Pdf.new()
    pagina = _pagina(pdf)
    aspetto = pdf.make_stream(b"0.9 0.9 0.2 rg 0 0 20 20 re f")
    aspetto.Type = pikepdf.Name("/XObject")
    aspetto.Subtype = pikepdf.Name("/Form")
    aspetto.BBox = pikepdf.Array([0, 0, 20, 20])
    if campo:
        annotazione = pikepdf.Dictionary(
            Type=pikepdf.Name("/Annot"), Subtype=pikepdf.Name("/Widget"),
            FT=pikepdf.Name("/Tx"), Rect=pikepdf.Array([50, 700, 400, 730]),
            T=pikepdf.String(autore))
    else:
        annotazione = pikepdf.Dictionary(
            Type=pikepdf.Name("/Annot"), Subtype=pikepdf.Name("/Text"),
            Rect=pikepdf.Array([500, 780, 520, 800]),
            Contents=pikepdf.String("Da ricontrollare prima della firma."),
            T=pikepdf.String(autore),
            AP=pikepdf.Dictionary(N=aspetto))
    pagina["/Annots"] = pikepdf.Array([pdf.make_indirect(annotazione)])
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _nota(percorso) -> dict[str, str]:
    with pikepdf.open(str(percorso)) as pdf:
        annotazione = pdf.pages[0].obj["/Annots"][0]
        fuori = {str(k): str(v) for k, v in annotazione.items()
                 if isinstance(v, pikepdf.String)}
        fuori["aspetto"] = "c'e'" if "/AP" in annotazione else "tolto"
        return fuori


def test_l_autore_di_una_nota_esce_col_segnaposto(tmp_path):
    dentro = _pdf_con_nota(tmp_path / "dentro.pdf")
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    nota = _nota(fuori)
    assert nota["/T"] == "{{AUTHOR_1}}", nota
    assert nota["/Contents"] == "Da ricontrollare prima della firma.", nota
    assert esito.valori_da_togliere >= 1, esito
    # Il disegno della nota resta: l'autore non e' nel disegno, e buttarlo
    # vorrebbe dire far sparire un timbro o una nota per cambiare un nome.
    assert nota["aspetto"] == "c'e'", "tolto l'aspetto di una nota di cui e' cambiato solo l'autore"


def test_il_segnaposto_dell_autore_non_e_quello_dei_nomi(tmp_path):
    """Chi ha scritto non e' una delle persone di cui si parla.

    Con il segnaposto dei nomi, in un documento che nomina Mario Rossi e che
    Mario Rossi ha scritto, il redatto diceva due volte la stessa cosa — e in
    uno scritto da un altro i numeri dell'autore e delle persone nel testo si
    mescolavano senza che niente lo dicesse.
    """
    pdf = pikepdf.Pdf.new()
    _pagina(pdf, "Il sig. Mario Rossi firma per accettazione.")
    pdf.docinfo["/Author"] = "luigi.bianchi"
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())
    autore = _proprieta(fuori)["/Author"]
    assert autore == "{{AUTHOR_1}}", autore
    assert "NAME" not in autore


def _pdf_con_note(percorso, autori: list[str], autore_del_documento: str = ""):
    """Piu' note, ognuna col suo autore, su due pagine."""
    pdf = pikepdf.Pdf.new()
    pagine = [_pagina(pdf), _pagina(pdf)]
    for indice, autore in enumerate(autori):
        nota = pikepdf.Dictionary(
            Type=pikepdf.Name("/Annot"), Subtype=pikepdf.Name("/Text"),
            Rect=pikepdf.Array([500, 780 - 30 * indice, 520, 800 - 30 * indice]),
            Contents=pikepdf.String("Da ricontrollare."),
            T=pikepdf.String(autore))
        pagina = pagine[indice % 2]
        if "/Annots" not in pagina:
            pagina["/Annots"] = pikepdf.Array()
        pagina["/Annots"].append(pdf.make_indirect(nota))
    if autore_del_documento:
        pdf.docinfo["/Author"] = autore_del_documento
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _autori_delle_note(percorso) -> list[str]:
    with pikepdf.open(str(percorso)) as pdf:
        return [str(nota["/T"]) for pagina in pdf.pages
                for nota in pagina.obj.get("/Annots", [])]


def test_due_autori_diversi_due_numeri_lo_stesso_autore_lo_stesso_numero(tmp_path):
    """La regola dei segnaposto numerati vale anche qui.

    In un documento rivisto da due persone, sapere **quali note sono della
    stessa mano** e' cio' che resta da leggere dopo aver tolto i nomi: con un
    numero solo per tutti le revisioni diventano un coro. E l'autore del
    documento, quando e' anche uno dei revisori, e' la stessa persona:
    maiuscole e punteggiatura non ne fanno due, come nel testo.
    """
    # Pagina 1: mario.rossi e ancora Mario Rossi. Pagina 2: luigi.bianchi, che
    # ha anche scritto il documento. Il numero 1 e' suo perche' le proprieta'
    # si leggono prima delle pagine: se le note contassero per conto loro, il
    # primo revisore sarebbe lui il numero 1, e in questo documento il numero
    # 1 vorrebbe dire due persone.
    dentro = _pdf_con_note(tmp_path / "dentro.pdf",
                           ["mario.rossi", "luigi.bianchi", "Mario Rossi"],
                           autore_del_documento="LUIGI BIANCHI")
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())

    assert _proprieta(fuori)["/Author"] == "{{AUTHOR_1}}"
    assert _autori_delle_note(fuori) == [
        "{{AUTHOR_2}}", "{{AUTHOR_2}}", "{{AUTHOR_1}}"], _autori_delle_note(fuori)
    assert verifica_redazione(dentro, fuori, PrivacyOptions())["sopravvissuti"] == 0


def test_senza_numeri_tutti_gli_autori_hanno_lo_stesso_segnaposto(tmp_path):
    dentro = _pdf_con_note(tmp_path / "dentro.pdf", ["mario.rossi", "luigi.bianchi"])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions(numerati=False))
    assert _autori_delle_note(fuori) == ["{{AUTHOR}}", "{{AUTHOR}}"]


def test_il_nome_di_un_campo_modulo_non_si_tocca(tmp_path):
    """Su un campo modulo `/T` e' il **nome del campo**, non chi l'ha scritto.

    Cambiarlo romperebbe il modulo: i calcoli e gli script lo cercano per
    nome. E' la ragione per cui `/T` non poteva entrare fra le chiavi di
    testo delle annotazioni, e per cui l'autore delle note restava fuori.
    """
    dentro = _pdf_con_nota(tmp_path / "dentro.pdf", autore="mario.rossi", campo=True)
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())
    assert _nota(fuori)["/T"] == "mario.rossi"
    assert verifica_redazione(dentro, fuori, PrivacyOptions())["sopravvissuti"] == 0


def test_la_verifica_dice_di_no_sull_autore_di_una_nota(tmp_path):
    dentro = _pdf_con_nota(tmp_path / "dentro.pdf")
    male = tmp_path / "male.pdf"
    shutil.copyfile(dentro, male)

    esito = verifica_redazione(dentro, male, PrivacyOptions())
    assert esito["identita_rimaste"] == 1, esito
    assert esito["pagine_con_superstiti"] == [0], esito

    bene = tmp_path / "bene.pdf"
    redigi_pdf(dentro, bene, PrivacyOptions())
    assert verifica_redazione(dentro, bene, PrivacyOptions())["sopravvissuti"] == 0


def test_l_argomento_di_una_nota_passa_dal_filtro(tmp_path):
    """`/Subj` e' testo scritto da una persona, come `/Contents`."""
    pdf = pikepdf.Pdf.new()
    pagina = _pagina(pdf)
    pagina["/Annots"] = pikepdf.Array([pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Annot"), Subtype=pikepdf.Name("/Text"),
        Rect=pikepdf.Array([500, 780, 520, 800]),
        Subj=pikepdf.String(f"Posizione di {CF}")))])
    dentro = tmp_path / "dentro.pdf"
    pdf.save(str(dentro))
    pdf.close()

    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())
    assert CF not in _nota(fuori)["/Subj"]

    male = tmp_path / "male.pdf"
    shutil.copyfile(dentro, male)
    assert verifica_redazione(dentro, male, PrivacyOptions())["sopravvissuti"] >= 1


# ------------------------------------- 2. i dati privati delle applicazioni


def _pdf_con_dati_privati(percorso):
    """`/PieceInfo` nei tre posti in cui puo' stare: pagina, catalogo, form."""
    pdf = pikepdf.Pdf.new()
    pagina = _pagina(pdf, f"Codice fiscale {CF}")

    def privati(testo: str):
        return pikepdf.Dictionary(Programma=pikepdf.Dictionary(
            LastModified=pikepdf.String("D:20260101120000"),
            Private=pdf.make_stream(testo.encode("latin-1"))))

    pagina["/PieceInfo"] = privati(f"copia di lavoro: IBAN {IBAN}")
    pdf.Root["/PieceInfo"] = privati(f"documento originale di {CF}")
    form = pdf.make_stream(b"")
    form.Type = pikepdf.Name("/XObject")
    form.Subtype = pikepdf.Name("/Form")
    form.BBox = pikepdf.Array([0, 0, 10, 10])
    form.PieceInfo = privati("livelli del disegno, con le note a margine")
    pagina["/Resources"]["/XObject"] = pikepdf.Dictionary(Fm0=form)
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _dati_privati_nel_file(percorso) -> tuple[int, bool]:
    """(oggetti con `/PieceInfo`, c'e' ancora un flusso con dentro l'IBAN)."""
    with pikepdf.open(str(percorso)) as pdf:
        oggetti = list(pdf.objects)
        quanti = sum(1 for o in oggetti
                     if isinstance(o, (pikepdf.Dictionary, pikepdf.Stream))
                     and "/PieceInfo" in o)
        resta = any(IBAN.encode() in bytes(o.read_bytes())
                    for o in oggetti if isinstance(o, pikepdf.Stream))
        return quanti, resta


def test_i_dati_privati_delle_applicazioni_escono_dal_file(tmp_path):
    dentro = _pdf_con_dati_privati(tmp_path / "dentro.pdf")
    assert _dati_privati_nel_file(dentro) == (3, True), "il file di prova non li ha"

    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    quanti, resta = _dati_privati_nel_file(fuori)
    assert quanti == 0, f"/PieceInfo ancora su {quanti} oggetti"
    assert not resta, "tolta la chiave, il flusso con la copia di lavoro e' rimasto nel file"
    assert esito.dati_privati_tolti == 3, esito


def test_la_verifica_dice_di_no_sui_dati_privati_rimasti(tmp_path):
    dentro = _pdf_con_dati_privati(tmp_path / "dentro.pdf")
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())
    pulito = verifica_redazione(dentro, fuori, PrivacyOptions())
    assert pulito["sopravvissuti"] == 0, pulito
    assert pulito["dati_privati_rimasti"] == 0, pulito

    # La stessa redazione, con i dati privati rimessi al loro posto.
    male = tmp_path / "male.pdf"
    with pikepdf.open(str(fuori)) as pdf:
        pdf.pages[0].obj["/PieceInfo"] = pikepdf.Dictionary(
            Programma=pikepdf.Dictionary(Private=pdf.make_stream(b"copia di lavoro")))
        pdf.save(str(male))
    esito = verifica_redazione(dentro, male, PrivacyOptions())
    assert esito["dati_privati_rimasti"] == 1, esito
    assert esito["sopravvissuti"] >= 1, esito


# ------------------------------------------------ 3. l'avviso, sullo schermo


def _client():
    from mr_rao.app_factory import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _anteprima(dati: bytes) -> dict:
    r = _client().post("/api/pdf/anteprima", base_url=BASE, data={
        "file": (io.BytesIO(dati), "atto.pdf"), "lang": "it",
    }, content_type="multipart/form-data")
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def test_l_anteprima_dice_cosa_e_uscito_dal_file(tmp_path):
    """Il PDF consegnato ha dei pezzi in meno: chi lo consegna deve saperlo."""
    dentro = _pdf_con_dati_privati(tmp_path / "dentro.pdf")
    dati = _anteprima(dentro.read_bytes())
    assert dati["dati_privati_rimossi"] == 3, dati
    assert dati["allegati_rimossi"] == 0, dati
    assert dati["pagine_coperte_sull_ocr"] == [], dati


def test_il_pannello_mostra_le_pagine_da_guardare_e_cio_che_e_stato_tolto():
    """Parita' GUI: un campo che l'interfaccia non legge non esiste.

    `pagine_coperte_sull_ocr` e `allegati_rimossi` uscivano dalla rotta dalla
    1.30.0, con accanto il commento «chi consegna il documento le guarda» —
    e il pannello non li leggeva. L'avviso esisteva nel JSON e non sullo
    schermo.
    """
    js = (RADICE / "static" / "js" / "app.js").read_text(encoding="utf-8")
    from mr_rao.i18n import TESTI

    coppie = {
        "pagine_coperte_sull_ocr": "pdf_coperte_sull_ocr",
        "allegati_rimossi": "pdf_allegati_rimossi",
        "dati_privati_rimossi": "pdf_dati_privati_rimossi",
    }
    for campo, frase in coppie.items():
        assert campo in js, f"il pannello non legge {campo}"
        assert frase in js, f"il pannello non mostra {frase}"
        voce = TESTI.get(frase)
        assert voce, f"manca la frase {frase}"
        # Le pagine vanno nominate una per una; i pezzi tolti si contano.
        campo_atteso = "{elenco}" if campo.startswith("pagine_") else "{n}"
        for lingua in ("it", "en"):
            assert len(voce.get(lingua, "")) > 30, (frase, lingua)
            assert campo_atteso in voce[lingua], (frase, lingua)
