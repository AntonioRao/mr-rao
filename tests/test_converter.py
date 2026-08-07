from pathlib import Path

import pytest

from mr_rao.converter import (
    ConvertOptions,
    ConvertResult,
    _frontmatter,
    convert_file,
    merge_markdowns,
)
from mr_rao.privacy import PrivacyOptions, RedactionReport


def _parse_frontmatter(blocco: str) -> dict:
    """Estrae e valida il blocco YAML tra i due '---'."""
    yaml = pytest.importorskip("yaml")
    righe = blocco.strip().splitlines()
    assert righe[0] == "---" and righe[-1] == "---"
    return yaml.safe_load("\n".join(righe[1:-1]))


def test_frontmatter_e_yaml_valido_senza_redazioni():
    dati = _parse_frontmatter(
        _frontmatter("nota.txt", ".txt", "markitdown", "abc123", RedactionReport())
    )
    assert dati["source"] == "nota.txt"
    assert dati["format"] == "txt"
    assert dati["engine"] == "markitdown"


def test_frontmatter_e_yaml_valido_con_redazioni():
    """'redactions: 5' seguito da chiavi indentate non è YAML valido:
    va annidato come mappa."""
    report = RedactionReport()
    report.add("emails", 2)
    report.add("phones", 3)
    dati = _parse_frontmatter(_frontmatter("a.pdf", ".pdf", "markitdown", "h", report))
    assert dati["redactions"] == {"total": 5, "emails": 2, "phones": 3}


@pytest.mark.parametrize(
    "nome",
    [
        "verbale: seduta 12.pdf",
        'preventivo "definitivo".pdf',
        "#bozza.pdf",
        "note - 50% sconto.pdf",
        "C:\\percorso\\file.pdf",
    ],
)
def test_frontmatter_regge_nomi_file_ostili(nome):
    dati = _parse_frontmatter(_frontmatter(nome, ".pdf", "markitdown", "h", RedactionReport()))
    assert dati["source"] == nome


def test_frontmatter_nel_markdown_resta_parsabile(tmp_path):
    """Controllo end-to-end: il documento prodotto ha un frontmatter valido."""
    p = tmp_path / "contatti.txt"
    p.write_text("scrivi a mario.rossi@example.com", encoding="utf-8")
    r = convert_file(
        p,
        options=ConvertOptions(
            include_frontmatter=True,
            privacy=PrivacyOptions(),
        ),
    )
    assert r.redaction.total >= 1
    fine = r.markdown.index("\n---", 3)
    dati = _parse_frontmatter(r.markdown[: fine + 4])
    assert dati["redactions"]["total"] == r.redaction.total


def test_convert_txt(tmp_path):
    p = tmp_path / "note.txt"
    p.write_text("Hello Mr. Rao\nLine 2", encoding="utf-8")
    r = convert_file(
        p,
        options=ConvertOptions(
            privacy=PrivacyOptions(
                emails=False,
                phones=False,
                names=False,
                fiscal=False,
                
            ),
            include_frontmatter=True,
        ),
    )
    assert r.error is None
    assert "Hello Mr. Rao" in r.markdown
    assert "generator:" in r.markdown
    assert r.engine_used in ("markitdown", "none") or r.markdown


def test_convert_clean_output(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("solo testo", encoding="utf-8")
    r = convert_file(
        p,
        options=ConvertOptions(
            include_frontmatter=False,
            clean_output=True,
            privacy=PrivacyOptions(
                emails=False, phones=False, names=False, fiscal=False
            ),
        ),
    )
    assert "solo testo" in r.markdown


def test_merge_markdowns():
    a = ConvertResult(
        markdown="---\ngenerator: x\n---\n\n# A\nbody a",
        engine_used="t",
        source_name="a.txt",
        source_ext=".txt",
        redaction=RedactionReport(),
    )
    b = ConvertResult(
        markdown="# B\nbody b",
        engine_used="t",
        source_name="b.txt",
        source_ext=".txt",
        redaction=RedactionReport(),
    )
    merged = merge_markdowns([a, b], title="Unito")
    assert "Unito" in merged
    assert "body a" in merged
    assert "body b" in merged
    assert "a.txt" in merged


def test_un_file_aperto_in_word_lo_dice_invece_di_esplodere(tmp_path, monkeypatch):
    """Convertire un documento che si ha aperto e' normalissimo, e Word lo
    tiene bloccato in lettura. Prima usciva un traceback Python con dentro
    PermissionError: a chi usa il programma non dice niente, non nomina il
    colpevole, e dalla web app arrivava come «failed to fetch».

    Trovato dal vivo il 2026-08-07, su un .docx aperto sul desktop.
    """
    from mr_rao import converter as modulo
    from mr_rao.converter import ConvertOptions, convert_file

    percorso = tmp_path / "verbale.docx"
    percorso.write_bytes(b"contenuto qualunque")

    def bloccato(_p):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(modulo, "_file_sha256", bloccato)

    r = convert_file(percorso, options=ConvertOptions(include_frontmatter=False))

    assert r.empty
    assert "aperto in un altro programma" in r.error
    assert "Chiudilo e riprova" in r.markdown
    # Il nome del file dev'esserci: chi ne converte dieci deve sapere quale.
    assert "verbale.docx" in r.markdown
