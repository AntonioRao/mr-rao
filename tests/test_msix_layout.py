# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il montaggio del pacchetto MSIX.

`MakeAppx` sta nel Windows SDK e non c'e' su una macchina di sviluppo
qualunque: l'impacchettamento vero si prova solo in CI. Il **montaggio**
pero' e' Python puro, e sbagliarlo significa un pacchetto respinto venti
minuti dopo, o peggio accettato con dentro cose che non dovevano esserci.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))


def _modulo():
    percorso = RADICE / "scripts" / "make_msix.py"
    spec = importlib.util.spec_from_file_location("make_msix", percorso)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture()
def finto_portable(tmp_path):
    """Un pacchetto portable finto, della forma giusta."""
    pacchetto = tmp_path / "MrRao-Portable"
    (pacchetto / "app").mkdir(parents=True)
    (pacchetto / "app" / "MrRao.exe").write_bytes(b"non e' un eseguibile vero")
    (pacchetto / "app" / "_internal").mkdir()
    (pacchetto / "app" / "_internal" / "base_library.zip").write_bytes(b"x")
    # Ci sono davvero nel portable, e nell'MSIX non devono finire.
    (pacchetto / "Installa Mr Rao.bat").write_text("@echo off", encoding="utf-8")
    (pacchetto / "Disinstalla Mr Rao.bat").write_text("@echo off", encoding="utf-8")
    (pacchetto / "mr_rao_shell.ps1").write_text("# ...", encoding="utf-8")
    return pacchetto


def test_il_layout_contiene_l_eseguibile_dove_lo_cerca_il_manifesto(
    finto_portable, tmp_path
):
    """Il manifesto dichiara `app\\MrRao.exe`. Se il layout lo mette altrove
    il pacchetto si costruisce lo stesso e non parte."""
    mod = _modulo()
    layout = mod.monta(finto_portable, tmp_path / "layout")
    assert (layout / "app" / "MrRao.exe").is_file()
    assert (layout / "app" / "_internal" / "base_library.zip").is_file()


def test_il_manifesto_e_le_immagini_ci_sono(finto_portable, tmp_path):
    mod = _modulo()
    layout = mod.monta(finto_portable, tmp_path / "layout")
    assert (layout / "AppxManifest.xml").is_file()
    assert (layout / "Assets" / "StoreLogo.png").is_file()
    assert (layout / "Assets" / "Square44x44Logo.png").is_file()


def test_gli_script_di_installazione_restano_fuori(finto_portable, tmp_path):
    """Nello Store l'installazione la fa Windows e le voci di menu le
    dichiara il manifesto. Uno script che scrive nel registro, dentro un
    pacchetto sotto certificazione, nella migliore delle ipotesi e' codice
    morto."""
    mod = _modulo()
    layout = mod.monta(finto_portable, tmp_path / "layout")
    rimasti = [p.name for p in layout.rglob("*") if p.suffix in (".bat", ".ps1")]
    assert not rimasti, rimasti


def test_le_licenze_entrano_nel_pacchetto(finto_portable, tmp_path):
    """pystray e' LGPL: gli obblighi di redistribuzione valgono per ogni
    confezione, non solo per lo zip."""
    mod = _modulo()
    layout = mod.monta(finto_portable, tmp_path / "layout")
    assert (layout / "LICENSE.txt").is_file()
    assert (layout / "THIRD_PARTY.md").is_file()
    assert (layout / "licenses").is_dir()


def test_senza_eseguibile_si_ferma_invece_di_montare_un_guscio(tmp_path):
    """Un MSIX senza il programma dentro si costruisce benissimo."""
    mod = _modulo()
    vuoto = tmp_path / "MrRao-Portable"
    (vuoto / "app").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        mod.monta(vuoto, tmp_path / "layout")


def test_rimontare_non_lascia_avanzi(finto_portable, tmp_path):
    """Il layout si ricostruisce da zero: un file di un giro precedente
    finirebbe nel pacchetto senza che nessuno lo abbia messo."""
    mod = _modulo()
    layout = tmp_path / "layout"
    mod.monta(finto_portable, layout)
    (layout / "avanzo.txt").write_text("resto di ieri", encoding="utf-8")
    mod.monta(finto_portable, layout)
    assert not (layout / "avanzo.txt").exists()


def test_le_immagini_dichiarate_nel_manifesto_esistono_tutte():
    """Un `Logo` che punta a un file assente e' un pacchetto respinto."""
    import re
    import xml.etree.ElementTree as ET

    manifesto = RADICE / "packaging" / "AppxManifest.xml"
    testo = manifesto.read_text(encoding="utf-8")
    # Si guardano gli attributi, non il testo: un percorso citato in un
    # commento non e' un'immagine dichiarata.
    radice = ET.parse(manifesto).getroot()
    citate = set()
    for elemento in radice.iter():
        for chiave, valore in elemento.attrib.items():
            if valore.startswith("Assets\\"):
                citate.add(valore)
        if elemento.tag.endswith("Logo") and elemento.text:
            citate.add(elemento.text.strip())

    assert citate, "il manifesto non cita nessuna immagine"
    for percorso in sorted(citate):
        atteso = RADICE / "packaging" / percorso.replace("\\", "/")
        assert atteso.is_file(), f"il manifesto cita {percorso}, che non esiste"


def test_il_residuo_di_python_docx_resta_fuori(finto_portable, tmp_path):
    """`[Content_Types].xml` e' un nome riservato da MSIX.

    python-docx spedisce il proprio modello anche **scompattato**, e dentro
    c'e' quel nome. La libreria non lo apre mai — `docx/api.py` carica
    `templates/default.docx`, cioe' lo zip — quindi escluderlo dal pacchetto
    Store non toglie niente a nessuno. Con dentro, MakeAppx enumera duemila
    file e poi risponde `0x8007007b` senza dire quale: venti minuti di CI
    per sapere che qualcosa non va.
    """
    mod = _modulo()
    modello = finto_portable / "app" / "_internal" / "docx" / "templates"
    (modello / "default-docx-template").mkdir(parents=True)
    (modello / "default-docx-template" / "[Content_Types].xml").write_text(
        "<Types/>", encoding="utf-8"
    )
    (modello / "default.docx").write_bytes(b"PK\x03\x04")

    layout = mod.monta(finto_portable, tmp_path / "layout")

    assert not list(layout.rglob("[[]Content_Types[]].xml")), "residuo nel pacchetto"
    assert (
        layout / "app" / "_internal" / "docx" / "templates" / "default.docx"
    ).is_file(), "il modello vero deve restare: senza, l'export .docx non parte"


def test_il_rilevatore_nomina_il_file_invece_di_dare_un_codice(finto_portable, tmp_path):
    """La ragione per cui esiste: MakeAppx dice *che* c'e' un nome illegale,
    non *quale*. Un controllo che si limitasse a fallire non varrebbe la
    fatica."""
    mod = _modulo()
    layout = mod.monta(finto_portable, tmp_path / "layout")
    assert mod.nomi_illegali(layout) == []

    (layout / "app" / "[Content_Types].xml").write_text("x", encoding="utf-8")
    problemi = mod.nomi_illegali(layout)
    assert len(problemi) == 1
    assert "Content_Types" in problemi[0]
    assert "riservato" in problemi[0]


def test_il_manifesto_alla_radice_non_e_un_errore(finto_portable, tmp_path):
    """Il rilevatore non deve segnalare la cosa che ci deve stare."""
    mod = _modulo()
    layout = mod.monta(finto_portable, tmp_path / "layout")
    assert (layout / "AppxManifest.xml").is_file()
    assert mod.nomi_illegali(layout) == []
