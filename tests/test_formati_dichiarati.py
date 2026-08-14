"""Ogni formato che dichiariamo di leggere deve essere leggibile.

Regressione del difetto piu' grave trovato finora: DOCX, XLSX, XLS e PPTX
non hanno mai funzionato. I formati di Office in MarkItDown vivono dietro
degli "extra" che non erano installati; senza, MarkItDown alza
MissingDependencyException, il testo estratto e' vuoto e l'utente riceve
«Il file caricato non contiene testo riconoscibile» — cioe' la colpa data
al suo documento.

Erano annunciati nella tabella del README, nei badge della finestra di
caricamento, nell'elenco del selettore file e nelle voci del menu
contestuale. Il primo che se ne e' accorto e' stato un utente, con un
verbale di collaudo pieno di testo.

I test precedenti non lo vedevano perche' usavano file finti: nessuno
aveva mai convertito un .docx vero.
"""
import io
import zipfile

import pytest

from config import ALLOWED_EXTENSIONS
from mr_rao.converter import (
    FORMAT_DEPENDENCIES,
    ConvertOptions,
    convert_file,
    missing_dependency_for,
)


@pytest.mark.parametrize("ext", sorted(FORMAT_DEPENDENCIES))
def test_la_dipendenza_del_formato_e_installata(ext):
    mancante = missing_dependency_for(ext)
    assert mancante is None, (
        f"{ext} e' dichiarato fra i formati supportati ma manca {mancante}. "
        f"Con questa dipendenza assente il file sembra vuoto e l'errore da' "
        f"la colpa al documento."
    )


def test_ogni_formato_office_dichiarato_ha_una_dipendenza_nota():
    """Se domani si aggiunge .odt all'elenco, deve entrare anche qui."""
    office = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}
    scoperti = (office & ALLOWED_EXTENSIONS) - set(FORMAT_DEPENDENCIES)
    assert not scoperti, f"formati senza dipendenza dichiarata: {sorted(scoperti)}"


def _docx_minimo(testo: str) -> bytes:
    """Un .docx valido, costruito a mano: niente file finti."""
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


def test_un_docx_vero_produce_testo(tmp_path):
    p = tmp_path / "verbale.docx"
    p.write_bytes(_docx_minimo("Consuntivazione giornate lavorate"))
    r = convert_file(p, options=ConvertOptions(include_frontmatter=False))
    assert "Consuntivazione" in r.markdown, r.markdown[:200]
    assert r.engine_used == "markitdown"
    assert not r.empty


def test_un_docx_vero_viene_anonimizzato(tmp_path):
    p = tmp_path / "lettera.docx"
    p.write_bytes(_docx_minimo("Contatta mario.rossi@example.it al 335 123 4567"))
    r = convert_file(p, options=ConvertOptions(include_frontmatter=False))
    assert "{{EMAIL_1}}" in r.markdown and "{{PHONE_1}}" in r.markdown


def test_la_dipendenza_mancante_non_diventa_colpa_del_documento(monkeypatch, tmp_path):
    """Il messaggio deve dire cosa manca, non che il file e' vuoto."""
    from mr_rao import converter

    class Rotto:
        def convert(self, _):
            raise RuntimeError("DocxConverter threw MissingDependencyException")

    monkeypatch.setattr(converter, "get_markitdown", lambda: Rotto())
    monkeypatch.setattr(converter, "missing_dependency_for", lambda ext: "python-docx")

    p = tmp_path / "verbale.docx"
    p.write_bytes(_docx_minimo("qualcosa"))
    r = convert_file(p, options=ConvertOptions(include_frontmatter=False))

    assert "python-docx" in r.markdown
    assert "Non dipende dal documento" in r.markdown
    assert "non contiene testo riconoscibile" not in r.markdown


def test_senza_causa_nota_resta_il_messaggio_di_prima(tmp_path):
    """Un file davvero vuoto deve continuare a dire che e' vuoto."""
    from mr_rao.converter import _empty_message

    assert "non contiene testo riconoscibile" in _empty_message(None)


def test_ogni_dipendenza_dichiarata_e_anche_nel_requirements():
    """Chi arriva col repo pulito installa da requirements.txt e basta.

    Se FORMAT_DEPENDENCIES nomina un pacchetto che quel file non chiede, il
    formato funziona solo sulle macchine dove qualcosa l'ha portato per
    conto suo -- ed e' quello che e' successo con `mammoth`: c'era nel venv
    di sviluppo da un'installazione precedente, non nel requirements. In
    locale tutto verde, sulla CI (che parte pulita) Word non si apriva.
    """
    from pathlib import Path

    requisiti = (
        Path(__file__).resolve().parents[1] / "requirements.txt"
    ).read_text(encoding="utf-8").lower()

    mancanti = sorted(
        {
            pacchetto
            for dipendenze in FORMAT_DEPENDENCIES.values()
            for _modulo, pacchetto in dipendenze
            if pacchetto.lower() not in requisiti
        }
    )
    assert not mancanti, (
        f"dichiarati come necessari ma non richiesti in requirements.txt: "
        f"{mancanti}. Su una macchina pulita quel formato non funziona."
    )


# ---------------------------------------------------------------------------
# Il Markdown: il formato che Mr. Rao **produce** e non accettava
# ---------------------------------------------------------------------------
#
# Trovato passando i documenti veri di una scrivania: dodici file su
# trentadue rifiutati con un `400`, tutti `.md`. Il resto del programma il
# Markdown lo conosceva gia' — sta fra le estensioni di prosa del motore e
# fra quelle del ripiego a testo semplice — e `docs/PRIVACY.md` lo elencava
# fra i formati leggibili. Mancava **solo** in `ALLOWED_EXTENSIONS`, che e'
# la porta.
#
# Il difetto e' peggiore di una mancanza qualunque: un documento gia'
# redatto da Mr. Rao esce in Markdown, e Mr. Rao non lo riprendeva. Il
# formato che produce era l'unico che rifiutava.
def test_il_markdown_e_accettato():
    assert ".md" in ALLOWED_EXTENSIONS
    assert ".markdown" in ALLOWED_EXTENSIONS


def test_un_markdown_vero_si_converte_e_si_redige(tmp_path):
    p = tmp_path / "verbale.md"
    p.write_text(
        "# Verbale\n\nPresenti: Mario Rossi (mario.rossi@esempio.it).\n",
        encoding="utf-8",
    )
    r = convert_file(p, ConvertOptions())
    assert "{{NAME" in r.markdown
    assert "{{EMAIL" in r.markdown
    assert "mario.rossi@esempio.it" not in r.markdown


def test_il_selettore_file_offre_esattamente_i_formati_ammessi():
    """**Il controllo che sarebbe servito.**

    L'elenco `accept=` del selettore e `ALLOWED_EXTENSIONS` sono due copie
    della stessa verita', scritte in due file diversi: e' la forma in cui
    questo difetto e' nato, ed e' la stessa di `test_integrazione_shell.py`
    per il menu contestuale. Qui si pretende che coincidano **nei due
    versi** — un formato offerto e non accettato e' una promessa rotta dopo
    il clic; un formato accettato e non offerto e' una funzione che nessuno
    trova.
    """
    import re
    from pathlib import Path

    html = (Path(__file__).resolve().parents[1] / "templates" / "index.html").read_text(
        encoding="utf-8"
    )
    m = re.search(r'accept="([^"]+)"', html)
    assert m, "nessun accept= nel selettore: il controllo non guarderebbe niente"
    offerti = {e.strip().lower() for e in m.group(1).split(",") if e.strip()}
    assert offerti == ALLOWED_EXTENSIONS, (
        f"solo nel selettore: {sorted(offerti - ALLOWED_EXTENSIONS)}; "
        f"solo fra gli ammessi: {sorted(ALLOWED_EXTENSIONS - offerti)}"
    )
