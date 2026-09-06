# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Un campo modulo tiene il suo valore in piu' di un posto.

La 1.24.0 ha chiuso il difetto grosso: annotazioni e campi modulo non stavano
nel flusso di contenuto, quindi uscivano interi da un file chiamato
`-redatto.pdf`. Si guardavano tre chiavi (`/Contents`, `/RC`, `/V`) sul widget
e sul suo primo genitore.

Restavano fuori tre strade, tutte con dentro il **valore vero**:

* `/DV` — il valore predefinito, quello a cui il modulo torna col comando
  «azzera». In un modulo precompilato e' una seconda copia del dato;
* `/TU` — il testo del suggerimento, che i lettori mostrano passandoci sopra
  col mouse. Nei moduli veri contiene spesso un esempio compilato;
* `/Opt` — l'elenco delle scelte di una tendina. In un modulo generato da un
  gestionale sono i nomi dei clienti.

E una quarta, di forma diversa: la catena dei genitori si fermava al **primo**.
Un modulo con i campi raggruppati (`/Parent` che ha a sua volta `/Parent`)
teneva il valore due livelli sopra, e li' non si guardava.

Il modo di sbagliare e' sempre quello: **testo che non passa dalla strada dove
vive il filtro**, come i metadati chiusi nella 1.28.0.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import pytest

pikepdf = pytest.importorskip("pikepdf")
pytest.importorskip("pypdfium2")

from mr_rao.privacy import PrivacyOptions  # noqa: E402
from mr_rao.redazione_pdf import redigi_pdf  # noqa: E402

CF = "RSSMRA85M01H501Z"


def _pdf_con_annotazione(percorso, campi: dict, *, nonni: bool = False,
                         testo_in_pagina: bool = True):
    """Una pagina con un campo modulo, e le chiavi che gli si passano.

    `testo_in_pagina` mette una riga disegnata nel flusso. Serve quasi sempre:
    senza, il documento e' fatto di soli campi, e quello e' un caso a parte —
    vedi `test_un_modulo_di_soli_campi_non_e_una_scansione`.
    """
    pdf = pikepdf.Pdf.new()
    if testo_in_pagina:
        font = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name("/Font"), Subtype=pikepdf.Name("/Type1"),
            BaseFont=pikepdf.Name("/Helvetica"),
            Encoding=pikepdf.Name("/WinAnsiEncoding")))
        risorse = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
        flusso = b"BT /F1 11 Tf 1 0 0 1 60 780 Tm (Modulo di richiesta) Tj ET"
    else:
        risorse = pikepdf.Dictionary()
        flusso = b"BT ET"
    pagina = pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=risorse,
        Contents=pdf.make_stream(flusso),
    ))
    annotazione = pikepdf.Dictionary(
        Type=pikepdf.Name("/Annot"),
        Subtype=pikepdf.Name("/Widget"),
        FT=pikepdf.Name("/Tx"),
        Rect=pikepdf.Array([50, 700, 400, 730]),
    )
    if nonni:
        # Il valore due livelli sopra: il gruppo del gruppo.
        #
        # Le chiavi si assegnano **con l'indice**, non con i nomi degli
        # argomenti: `pikepdf.Dictionary(**{"/V": ...})` produce `//V`, cioe'
        # una chiave che non esiste. La prima stesura lo faceva, e il banco era
        # rosso accusando il prodotto di un difetto che non aveva.
        nonno_d = pikepdf.Dictionary()
        for k, v in campi.items():
            nonno_d[k] = (pikepdf.Array([pikepdf.String(x) for x in v])
                          if isinstance(v, list) else pikepdf.String(v))
        nonno = pdf.make_indirect(nonno_d)
        padre_d = pikepdf.Dictionary()
        padre_d["/Parent"] = nonno
        padre = pdf.make_indirect(padre_d)
        annotazione["/Parent"] = padre
    else:
        for k, v in campi.items():
            if isinstance(v, list):
                annotazione[k] = pikepdf.Array([pikepdf.String(x) for x in v])
            else:
                annotazione[k] = pikepdf.String(v)

    pagina["/Annots"] = pikepdf.Array([pdf.make_indirect(annotazione)])
    pdf.pages.append(pikepdf.Page(pagina))
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _tutto_il_testo(percorso) -> str:
    """Ogni stringa dentro il documento, da qualunque chiave venga."""
    pezzi: list[str] = []
    with pikepdf.open(str(percorso)) as pdf:
        for oggetto in pdf.objects:
            if isinstance(oggetto, pikepdf.Dictionary):
                for valore in oggetto.values():
                    if isinstance(valore, pikepdf.String):
                        pezzi.append(str(valore))
                    elif isinstance(valore, pikepdf.Array):
                        pezzi += [str(x) for x in valore
                                  if isinstance(x, pikepdf.String)]
    return "\n".join(pezzi)


@pytest.mark.parametrize("chiave", ["/V", "/DV", "/TU"])
def test_il_valore_sparisce_da_ogni_chiave_di_testo(tmp_path, chiave):
    dentro = _pdf_con_annotazione(tmp_path / "modulo.pdf", {chiave: f"CF {CF}"})
    fuori = tmp_path / "modulo-redatto.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())
    assert CF not in _tutto_il_testo(fuori), f"{chiave} conserva il dato"


def test_le_scelte_di_una_tendina_non_restano(tmp_path):
    """`/Opt` in un modulo generato da un gestionale sono i nomi dei clienti."""
    dentro = _pdf_con_annotazione(
        tmp_path / "tendina.pdf",
        {"/Opt": ["Mario Rossi", "Luigi Bianchi", "Nessuno"]},
    )
    fuori = tmp_path / "tendina-redatta.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())
    testo = _tutto_il_testo(fuori)
    assert "Mario Rossi" not in testo, testo
    assert "Luigi Bianchi" not in testo, testo


def test_il_valore_due_livelli_sopra_non_resta(tmp_path):
    """La catena dei genitori si fermava al primo: in un modulo con i campi
    raggruppati il valore sta piu' su."""
    dentro = _pdf_con_annotazione(
        tmp_path / "gruppo.pdf", {"/V": f"CF {CF}"}, nonni=True
    )
    fuori = tmp_path / "gruppo-redatto.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())
    assert CF not in _tutto_il_testo(fuori)


def test_un_modulo_di_soli_campi_non_e_una_scansione(tmp_path):
    """Trovato scrivendo questi banchi, ed e' piu' grosso di loro.

    Un PDF le cui pagine non hanno testo **disegnato** — un modulo in cui tutto
    sta nei campi — usciva dichiarato «scansione»: il ritorno anticipato guarda
    solo il testo estratto dalle pagine, e le annotazioni non le conta nessuno.
    Il file redatto non veniva nemmeno scritto, e la rotta rispondeva che il
    documento e' una scansione. Non lo e': il testo c'e' ed e' redigibile, sta
    in un altro posto.

    Dire «e' una scansione» di un documento che non lo e' manda l'utente a
    cercare l'OCR per un file che invece si poteva trattare.
    """
    dentro = _pdf_con_annotazione(
        tmp_path / "solo-campi.pdf",
        {"/V": f"CF {CF}"},
        testo_in_pagina=False,
    )
    fuori = tmp_path / "solo-campi-redatto.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    assert not esito.scansione, "un modulo di soli campi non e' una scansione"
    assert fuori.exists(), "il file redatto non e' stato scritto"
    assert CF not in _tutto_il_testo(fuori)


def test_una_scansione_vera_resta_una_scansione(tmp_path):
    """La riga che impedisce di «correggere» dicendo mai piu' «scansione».

    Una pagina senza testo e senza campi e' esattamente cio' che quel ritorno
    anticipato esiste per riconoscere, e deve continuare a farlo.
    """
    pdf = pikepdf.Pdf.new()
    pdf.pages.append(pikepdf.Page(pdf.make_indirect(pikepdf.Dictionary(
        Type=pikepdf.Name("/Page"),
        MediaBox=pikepdf.Array([0, 0, 595, 842]),
        Resources=pikepdf.Dictionary(),
        Contents=pdf.make_stream(b"0.2 0.2 0.2 rg 80 500 400 200 re f"),
    ))))
    dentro = tmp_path / "scansione.pdf"
    pdf.save(str(dentro))
    pdf.close()

    esito = redigi_pdf(dentro, tmp_path / "scansione-redatta.pdf", PrivacyOptions())
    assert esito.scansione


def test_un_modulo_senza_dati_personali_resta_intero(tmp_path):
    """La riga che impedisce di «correggere» svuotando ogni annotazione.

    Un'etichetta e un suggerimento innocui servono a chi compila il modulo, e
    buttarli renderebbe il documento peggiore senza proteggere nessuno.
    """
    dentro = _pdf_con_annotazione(
        tmp_path / "vuoto.pdf",
        {"/V": "Scrivi qui la data", "/TU": "Formato giorno/mese/anno"},
    )
    fuori = tmp_path / "vuoto-redatto.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())
    testo = _tutto_il_testo(fuori)
    assert "Scrivi qui la data" in testo, testo
    assert "Formato giorno/mese/anno" in testo, testo
