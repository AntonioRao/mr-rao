"""Il PDF redatto, dall'interfaccia: l'anteprima e il file da scaricare.

Perché queste due rotte esistono
--------------------------------

Il motore c'era da prima, ma **una funzione che dalla GUI non esiste, per chi
usa il programma non esiste**. Chi deve depositare un atto vuole indietro il
documento, non un Markdown — e vuole *vedere* cosa è sparito prima di
consegnarlo, perché un numero che dice «74 sostituzioni» non fa distinguere il
nome tolto dal nome che era già lì.

Le tre cose che qui non devono rompersi
---------------------------------------

* il PDF che esce **non ha i dati coperti, li ha tolti**: si riestrae il testo
  e si guarda, perché un rettangolo nero passerebbe qualunque altro controllo;
* una **scansione** viene rifiutata dicendolo. Disegnarci sopra dei rettangoli
  sembrerebbe una redazione e non lo sarebbe, ed è il modo peggiore di
  sbagliare in questo prodotto;
* le **pagine non trattate** si dichiarano sempre, anche quando sono zero: una
  pagina finita nel ripiego non è stata redatta.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import io

import pytest

pikepdf = pytest.importorskip("pikepdf")
pytest.importorskip("pypdfium2")

from mr_rao.app_factory import create_app  # noqa: E402
# Rinominato nell'import: pytest raccoglie come test qualunque nome importato
# che cominci per `test`, e `testo_per_pagina` cominciava.
from mr_rao.redazione_pdf import testo_per_pagina as _testo_per_pagina  # noqa: E402


BASE = "http://127.0.0.1:5000"


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _pdf(righe: list[str]) -> bytes:
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
    pdf.pages.append(pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font)),
        Contents=pdf.make_stream("\n".join(comandi).encode("latin-1"))))))
    fuori = io.BytesIO()
    pdf.save(fuori)
    pdf.close()
    return fuori.getvalue()


def _scansione() -> bytes:
    pdf = pikepdf.Pdf.new()
    pdf.pages.append(pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=pikepdf.Dictionary(),
        Contents=pdf.make_stream(b"0.2 0.2 0.2 rg 80 500 400 200 re f")))))
    fuori = io.BytesIO()
    pdf.save(fuori)
    pdf.close()
    return fuori.getvalue()


CON_DATI = ["Il cliente Mario Rossi ha scritto a mario.rossi@example.it",
            "e questa riga non contiene nessun dato personale."]


# ------------------------------------------------------------- lo scaricamento


def test_il_pdf_scaricato_non_contiene_piu_il_dato(client, tmp_path):
    """**La riga che tiene tutto.** Non «coperto»: assente.

    Si riestrae il testo dal file che il server ha restituito. Un rettangolo
    nero disegnato sopra passerebbe qualunque controllo sui conteggi, e questo
    è l'unico che direbbe di no.
    """
    r = client.post("/api/export/pdf", base_url=BASE, data={
        "file": (io.BytesIO(_pdf(CON_DATI)), "atto.pdf"),
        "lang": "it",
    }, content_type="multipart/form-data")

    assert r.status_code == 200, r.data[:300]
    assert r.mimetype == "application/pdf"
    assert "atto-redatto.pdf" in r.headers["Content-Disposition"]

    uscita = tmp_path / "uscita.pdf"
    uscita.write_bytes(r.data)
    testo = "\n".join(_testo_per_pagina(uscita))
    assert "Mario Rossi" not in testo, testo
    assert "mario.rossi@example.it" not in testo, testo
    assert "nessun dato personale" in testo, "il resto del documento è sparito"


def test_lo_scaricamento_dichiara_le_pagine_non_trattate(client):
    """Anche quando sono zero, e l'intestazione c'è sempre.

    Chi scarica deve poter sapere quali pagine **non** sono state redatte senza
    aprire il file: una pagina finita nel ripiego non è stata trattata, e
    presentarla come tale sarebbe il modo peggiore di sbagliare.
    """
    r = client.post("/api/export/pdf", base_url=BASE, data={
        "file": (io.BytesIO(_pdf(CON_DATI)), "atto.pdf"),
    }, content_type="multipart/form-data")

    assert r.status_code == 200
    assert "X-MrRao-Pagine-Non-Trattate" in r.headers
    assert r.headers["X-MrRao-Pagine-Non-Trattate"] == ""
    assert int(r.headers["X-MrRao-Sostituzioni"]) >= 2


# ------------------------------------------------------------------ l'anteprima


def test_l_anteprima_da_le_due_pagine(client):
    r = client.post("/api/pdf/anteprima", base_url=BASE, data={
        "file": (io.BytesIO(_pdf(CON_DATI)), "atto.pdf"),
        "pagina": "0",
    }, content_type="multipart/form-data")

    assert r.status_code == 200, r.data[:300]
    dati = r.get_json()
    assert dati["pagine"] == 1
    assert dati["sostituzioni"] >= 2
    assert dati["pagine_non_trattate"] == []
    for lato in ("prima", "dopo"):
        assert dati[lato].startswith("data:image/png;base64,"), lato
        assert len(dati[lato]) > 2000, f"{lato}: immagine sospettosamente vuota"
    assert dati["prima"] != dati["dopo"], (
        "prima e dopo sono identiche: l'anteprima non sta mostrando la redazione"
    )


def test_l_anteprima_non_esce_dal_documento(client):
    """Una pagina che non esiste non deve far cadere la richiesta: si dà
    l'ultima. Le frecce dell'interfaccia si disabilitano da sole, ma una rotta
    che si fida di quello è una rotta che si rompe al primo aggiornamento."""
    r = client.post("/api/pdf/anteprima", base_url=BASE, data={
        "file": (io.BytesIO(_pdf(CON_DATI)), "atto.pdf"),
        "pagina": "99",
    }, content_type="multipart/form-data")
    assert r.status_code == 200
    assert r.get_json()["prima"].startswith("data:image/png;base64,")


# ---------------------------------------------------- quello che si rifiuta


def test_una_scansione_viene_rifiutata_dicendolo(client):
    """**Non si finge.** Un PDF senza testo non ha glifi da togliere:
    disegnarci sopra dei rettangoli sembrerebbe una redazione e non lo
    sarebbe, e chi lo consegnasse crederebbe di aver protetto qualcosa."""
    r = client.post("/api/export/pdf", base_url=BASE, data={
        "file": (io.BytesIO(_scansione()), "scansione.pdf"),
        "lang": "it",
    }, content_type="multipart/form-data")

    assert r.status_code == 422
    messaggio = r.get_json()["error"]
    assert "scansione" in messaggio.lower()
    assert r.mimetype != "application/pdf", "ha restituito un file spacciandolo per redatto"


def test_da_un_documento_che_non_e_un_pdf_no(client):
    r = client.post("/api/export/pdf", base_url=BASE, data={
        "file": (io.BytesIO(b"non sono un pdf"), "appunti.txt"),
        "lang": "it",
    }, content_type="multipart/form-data")
    assert r.status_code == 400
    assert "PDF" in r.get_json()["error"]


def test_senza_file_no(client):
    r = client.post("/api/export/pdf", base_url=BASE, data={},
                    content_type="multipart/form-data")
    assert r.status_code == 400


# ------------------------------------------------------ le opzioni contano


def test_le_opzioni_della_pagina_valgono_anche_qui(client, tmp_path):
    """Il pannello manda le stesse opzioni della conversione.

    Se non le mandasse, il PDF scaricato sarebbe redatto **in modo diverso** da
    quello che l'utente ha appena visto sullo schermo — e non ci sarebbe niente
    che glielo dica.
    """
    r = client.post("/api/export/pdf", base_url=BASE, data={
        "file": (io.BytesIO(_pdf(["Scrivimi a mario.rossi@example.it grazie."])), "a.pdf"),
        "privacy_emails": "false",
    }, content_type="multipart/form-data")

    assert r.status_code == 200
    uscita = tmp_path / "uscita.pdf"
    uscita.write_bytes(r.data)
    testo = "\n".join(_testo_per_pagina(uscita))
    assert "mario.rossi@example.it" in testo, (
        "l'interruttore delle email era spento e l'email è stata tolta lo stesso"
    )


# ------------------------------------------------ ed è raggiungibile dall'interfaccia


def test_il_pannello_e_nella_pagina(client):
    """Parità GUI: il motore c'era già, e per chi usa il programma non
    esisteva."""
    pagina = client.get("/", base_url=BASE).get_data(as_text=True)
    for pezzo in ('id="pdf-pannello"', 'id="pdf-anteprima-btn"',
                  'id="pdf-scarica-btn"', 'id="pdf-img-prima"',
                  'id="pdf-img-dopo"', 'id="pdf-avviso"'):
        assert pezzo in pagina, pezzo
