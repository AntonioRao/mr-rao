"""Regressioni su scelta del motore e isolamento delle opzioni.

Copre due bug che i test per-modulo non potevano vedere, perché nascono
dalla *combinazione* profilo × formato:

1. engine=rapidocr + .pdf finiva in ocr_image() ("cannot identify image file"),
   perché il ramo .pdf era codice morto: il profilo "Solo OCR" falliva su
   tutte le scansioni PDF, cioè il suo caso d'uso.
2. un .eml riscriveva opts.privacy sull'oggetto del chiamante: ignorava la
   scelta esplicita dell'utente e la propagava ai file successivi del batch.
"""
from email.message import EmailMessage

import pytest

from mr_rao import converter
from mr_rao.converter import ConvertOptions, convert_file
from mr_rao.privacy import PrivacyOptions
from mr_rao.profiles import PROFILES, options_from_profile

NO_PRIVACY = PrivacyOptions(
    emails=False, phones=False, names=False, fiscal=False,
    amounts=False,
)


@pytest.fixture()
def engines(monkeypatch):
    """Sostituisce i motori reali con registratori: verifichiamo *quale*
    motore viene scelto senza caricare i modelli ONNX."""
    calls: list[str] = []

    def fake_ocr_image(path, language="it"):
        calls.append("ocr_image")
        return "testo da immagine"

    def fake_ocr_pdf(path, language="it", progress=None, should_cancel=None,
                     max_pages=None, include_tables=True):
        calls.append("ocr_pdf")
        return "testo da OCR pdf"

    class _FakeMarkItDown:
        def convert(self, path):
            calls.append("markitdown")
            return type("Res", (), {"text_content": "testo da documento"})()

    monkeypatch.setattr(converter, "ocr_image", fake_ocr_image)
    monkeypatch.setattr(converter, "ocr_pdf_fallback", fake_ocr_pdf)
    monkeypatch.setattr(converter, "extract_pdf_tables", lambda path: "")
    monkeypatch.setattr(converter, "get_markitdown", lambda: _FakeMarkItDown())
    return calls


def _make_file(tmp_path, ext: str):
    path = tmp_path / f"campione{ext}"
    if ext == ".eml":
        msg = EmailMessage()
        msg["Subject"] = "Oggetto di prova"
        msg["From"] = "mittente@example.com"
        msg["To"] = "destinatario@example.com"
        msg.set_content("scrivi a mario.rossi@example.com")
        path.write_bytes(msg.as_bytes())
    elif ext == ".txt":
        path.write_text("contenuto di prova", encoding="utf-8")
    else:
        path.write_bytes(b"\x00binario")
    return path


@pytest.mark.parametrize(
    ("engine", "ext", "atteso"),
    [
        # Il bug: prima finiva in ocr_image e sollevava.
        ("rapidocr", ".pdf", "ocr_pdf"),
        ("auto", ".pdf", "markitdown"),
        ("markitdown", ".pdf", "markitdown"),
        ("rapidocr", ".png", "ocr_image"),
        ("auto", ".png", "ocr_image"),
        ("markitdown", ".png", "markitdown"),
        # Né immagine né PDF: l'OCR non deve mai entrare in gioco.
        ("rapidocr", ".docx", "markitdown"),
        ("auto", ".txt", "markitdown"),
    ],
)
def test_scelta_motore(engines, tmp_path, engine, ext, atteso):
    path = _make_file(tmp_path, ext)
    r = convert_file(
        path,
        options=ConvertOptions(engine=engine, privacy=NO_PRIVACY, include_frontmatter=False),
    )
    assert r.error is None
    assert engines == [atteso], f"engine={engine} ext={ext}: chiamato {engines}"


@pytest.mark.parametrize("profile_id", sorted(PROFILES))
@pytest.mark.parametrize("ext", [".pdf", ".png", ".txt", ".eml"])
def test_ogni_profilo_su_ogni_formato(engines, tmp_path, profile_id, ext):
    """Matrice di fumo: nessuna combinazione supportata deve andare in errore."""
    path = _make_file(tmp_path, ext)
    opts = options_from_profile(profile_id)
    assert opts is not None
    r = convert_file(path, options=opts)
    assert r.error is None, f"profilo={profile_id} ext={ext} -> {r.error}"
    assert r.engine_used != "none"
    if ext == ".eml":
        assert r.engine_used == "eml_parser"


def test_solo_ocr_su_pdf_usa_ocr_pdf(engines, tmp_path):
    """Il profilo 'Solo OCR' esiste per le scansioni PDF: deve arrivarci."""
    path = _make_file(tmp_path, ".pdf")
    r = convert_file(path, options=options_from_profile("solo_ocr"))
    assert r.error is None
    assert engines == ["ocr_pdf"]
    assert r.engine_used == "rapidocr_pdf"


def test_eml_non_muta_le_opzioni_del_chiamante(tmp_path):
    """Privacy OFF esplicita: va rispettata sull'EML e non deve restare
    appiccicata all'oggetto opzioni condiviso dal batch."""
    eml = _make_file(tmp_path, ".eml")
    txt = tmp_path / "dopo.txt"
    txt.write_text("contatto: luigi.verdi@example.com", encoding="utf-8")

    opts = ConvertOptions(privacy=NO_PRIVACY, include_frontmatter=False)

    r_eml = convert_file(eml, options=opts)
    assert r_eml.error is None
    assert "mario.rossi@example.com" in r_eml.markdown, "scelta dell'utente ignorata"

    # l'oggetto del chiamante è intatto...
    assert opts.privacy is NO_PRIVACY
    assert opts.privacy.emails is False

    # ...e il file successivo dello stesso batch non viene contaminato
    r_txt = convert_file(txt, options=opts)
    assert "luigi.verdi@example.com" in r_txt.markdown


def test_opzioni_riusate_restano_stabili_con_privacy_on(tmp_path):
    """Simmetrico: privacy ON esplicita resta ON su tutta la sequenza."""
    opts = ConvertOptions(privacy=PrivacyOptions(), include_frontmatter=False)
    eml = _make_file(tmp_path, ".eml")
    txt = tmp_path / "dopo.txt"
    txt.write_text("contatto: luigi.verdi@example.com", encoding="utf-8")

    r_eml = convert_file(eml, options=opts)
    r_txt = convert_file(txt, options=opts)
    assert "{{EMAIL}}" in r_eml.markdown
    assert "{{EMAIL}}" in r_txt.markdown
    assert opts.privacy.emails is True
