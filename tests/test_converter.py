from pathlib import Path

from mr_rao.converter import ConvertOptions, convert_file, merge_markdowns, ConvertResult
from mr_rao.privacy import PrivacyOptions, RedactionReport


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
                use_scrubadub=False,
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
                emails=False, phones=False, names=False, fiscal=False, use_scrubadub=False
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
