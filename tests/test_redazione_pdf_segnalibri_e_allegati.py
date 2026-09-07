# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Le altre due stanze del PDF: i **segnalibri** e gli **allegati**.

## Come e' saltato fuori

Confrontando Mr. Rao con `rizzo-pii` il 7 settembre 2026. Il loro
`pdf_export.py` pulisce cinque posti — metadati, annotazioni, campi modulo,
**segnalibri**, **allegati** — e noi ne coprivamo tre. Provato su un PDF con lo
stesso codice fiscale in tutti e tre i posti:

    esito: valori_da_togliere 1, pagine_in_ripiego []
    segnalibri nel PDF redatto : ['Scheda di RSSMRA85M01H501Z']
    allegati nel PDF redatto   : {'nota.txt': contiene il codice fiscale}
    verifica_redazione         : sopravvissuti 0

Il flusso della pagina era pulito, il motore dichiarava un valore tolto, e la
verifica diceva **zero superstiti** guardando due posti in cui quel dato non
era mai stato. E' esattamente la forma dei difetti dei metadati e delle
annotazioni: testo che non sta nel flusso di contenuto, quindi la chirurgia
dei glifi non lo vede e nemmeno la rete che dovrebbe accorgersene.

## Perche' gli allegati si tolgono invece di redigerli

Un allegato e' **un altro documento**, non un pezzo di questo: puo' essere un
`.docx`, un `.jpg`, un PDF a sua volta. Redigerlo vorrebbe dire far girare
tutto il motore dentro un file che non sappiamo aprire, e ripiegare su
«guardo dentro solo se e' testo» lascerebbe passare intero proprio il caso
peggiore, cioe' l'allegato binario. Si tolgono tutti, si contano, e il
rapporto lo dice: e' l'unica risposta che non promette piu' di quel che fa.

I segnalibri invece sono stringhe corte, come le proprieta' del documento:
si redigono con lo stesso motore, e uno senza dati personali resta dov'e'.

Tutti i valori sono inventati.
"""

from __future__ import annotations

import pytest

pikepdf = pytest.importorskip("pikepdf")
pytest.importorskip("pypdfium2")

from mr_rao.privacy import PrivacyOptions  # noqa: E402
from mr_rao.redazione_pdf import redigi_pdf, verifica_redazione  # noqa: E402

CF = "RSSMRA85M01H501Z"
NOME = "Mario Rossi"


def _pdf(percorso, righe: list[str], segnalibri: list[str] = (),
         allegati: dict[str, str] | None = None):
    """Un PDF con testo di pagina, segnalibri e allegati."""
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

    if segnalibri:
        with pdf.open_outline() as sommario:
            for titolo in segnalibri:
                sommario.root.append(pikepdf.OutlineItem(titolo, 0))
    for nome, contenuto in (allegati or {}).items():
        pdf.attachments[nome] = pikepdf.AttachedFileSpec(
            pdf, contenuto.encode("utf-8"), mime_type="text/plain")
    pdf.save(str(percorso))
    pdf.close()
    return percorso


def _titoli(percorso) -> list[str]:
    with pikepdf.open(str(percorso)) as pdf:
        with pdf.open_outline() as sommario:
            return [voce.title for voce in sommario.root]


def _allegati(percorso) -> dict[str, str]:
    with pikepdf.open(str(percorso)) as pdf:
        return {nome: bytes(spec.get_file().read_bytes()).decode("utf-8", "replace")
                for nome, spec in pdf.attachments.items()}


# ------------------------------------------------------------- i segnalibri


def test_il_codice_fiscale_nel_titolo_di_un_segnalibro_non_esce(tmp_path):
    """Il sommario si apre con un click e prima usciva intero."""
    dentro = _pdf(tmp_path / "dentro.pdf",
                  [f"Il contribuente C.F. {CF} dichiara."],
                  segnalibri=[f"Scheda di {CF}", f"Pratica {NOME}"])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())

    titoli = _titoli(fuori)
    assert titoli, "il sommario e' sparito: si redige, non si cancella"
    for titolo in titoli:
        assert CF not in titolo, f"codice fiscale ancora nel segnalibro: {titolo!r}"
        assert NOME not in titolo, f"nome ancora nel segnalibro: {titolo!r}"


def test_un_segnalibro_pulito_resta_com_era(tmp_path):
    """La riga che impedisce di «correggere» buttando via il sommario.

    Un documento senza dati personali nei titoli deve uscire con i suoi
    segnalibri identici: qui si redige, non si rade al suolo.
    """
    dentro = _pdf(tmp_path / "dentro.pdf", ["Una riga qualunque."],
                  segnalibri=["Capitolo primo", "Allegato tecnico"])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())

    assert _titoli(fuori) == ["Capitolo primo", "Allegato tecnico"]


def test_la_verifica_guarda_anche_i_segnalibri(tmp_path):
    """Un controllo che non puo' dire di no non e' una verifica.

    Si sabota il documento redatto rimettendo il codice fiscale nel titolo:
    la verifica deve accorgersene. Senza questo caso, la correzione sopra
    potrebbe rompersi domani e nessuno se ne accorgerebbe.
    """
    dentro = _pdf(tmp_path / "dentro.pdf",
                  [f"Il contribuente C.F. {CF} dichiara."],
                  segnalibri=[f"Scheda di {CF}"])
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())

    with pikepdf.open(str(fuori), allow_overwriting_input=True) as pdf:
        with pdf.open_outline() as sommario:
            sommario.root[0].title = f"Scheda di {CF}"
        pdf.save(str(fuori))

    esito = verifica_redazione(dentro, fuori, PrivacyOptions())
    assert esito["sopravvissuti"] >= 1, (
        "la verifica non guarda i segnalibri: " f"{esito}")


# -------------------------------------------------------------- gli allegati


def test_un_allegato_non_viaggia_dentro_il_pdf_redatto(tmp_path):
    """Un allegato e' un documento che non abbiamo redatto.

    Lasciarlo dentro vuol dire consegnare un file «-redatto.pdf» con dentro
    un secondo documento intatto.
    """
    dentro = _pdf(tmp_path / "dentro.pdf",
                  [f"Il contribuente C.F. {CF} dichiara."],
                  allegati={"nota.txt": f"Codice fiscale {CF}\n"})
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    assert _allegati(fuori) == {}, "l'allegato e' ancora dentro il PDF redatto"
    assert esito.allegati_tolti == 1, (
        f"il rapporto non dice che l'allegato e' stato tolto: {esito.allegati_tolti}")


def test_un_pdf_senza_allegati_non_cambia_il_conto(tmp_path):
    """La riga che impedisce di dichiarare rimozioni che non ci sono state."""
    dentro = _pdf(tmp_path / "dentro.pdf", [f"Il contribuente C.F. {CF} dichiara."])
    fuori = tmp_path / "fuori.pdf"
    esito = redigi_pdf(dentro, fuori, PrivacyOptions())

    assert esito.allegati_tolti == 0


def test_la_verifica_guarda_anche_gli_allegati(tmp_path):
    """Come per i segnalibri: si sabota e si pretende il rosso."""
    dentro = _pdf(tmp_path / "dentro.pdf",
                  [f"Il contribuente C.F. {CF} dichiara."],
                  allegati={"nota.txt": f"Codice fiscale {CF}\n"})
    fuori = tmp_path / "fuori.pdf"
    redigi_pdf(dentro, fuori, PrivacyOptions())

    with pikepdf.open(str(fuori), allow_overwriting_input=True) as pdf:
        pdf.attachments["nota.txt"] = pikepdf.AttachedFileSpec(
            pdf, f"Codice fiscale {CF}\n".encode("utf-8"), mime_type="text/plain")
        pdf.save(str(fuori))

    esito = verifica_redazione(dentro, fuori, PrivacyOptions())
    assert esito["sopravvissuti"] >= 1, (
        f"la verifica non guarda gli allegati: {esito}")
