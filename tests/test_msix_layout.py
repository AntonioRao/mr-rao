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
