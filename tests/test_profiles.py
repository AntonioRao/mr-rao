# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
from mr_rao.profiles import list_profiles, options_from_profile
from mr_rao.converter import merge_markdowns, ConvertResult
from mr_rao.privacy import RedactionReport


def test_list_profiles():
    profiles = list_profiles()
    assert len(profiles) >= 4
    ids = {p["id"] for p in profiles}
    assert "default" in ids
    assert "solo_ocr" in ids


def test_options_from_profile_solo_ocr():
    opts = options_from_profile("solo_ocr")
    assert opts is not None
    assert opts.engine == "rapidocr"
    assert opts.force_ocr_pdf is True


def test_compare_merge():
    a = ConvertResult(
        markdown="# A\nbody a",
        engine_used="t",
        source_name="a.pdf",
        source_ext=".pdf",
        redaction=RedactionReport(),
    )
    b = ConvertResult(
        markdown="# B\nbody b",
        engine_used="t",
        source_name="b.pdf",
        source_ext=".pdf",
        redaction=RedactionReport(),
    )
    md = merge_markdowns([a, b], title="Confronto", compare_mode=True)
    assert "Documento A" in md
    assert "Documento B" in md
    assert "body a" in md and "body b" in md
