# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Gli archivi di release e la loro impronta.

Due cose che si rompono in silenzio e se ne accorge solo chi scarica:

- se manca l'archivio a **nome fisso**, `/releases/latest/download/...` da'
  404 e tutti i link di scaricamento nei README smettono di funzionare senza
  che nessuno riceva un avviso;
- se l'impronta pubblicata non corrisponde al file, chi la controlla conclude
  che il pacchetto e' stato manomesso — cioe' l'esatto contrario di quello
  per cui e' stata pubblicata.
"""
from __future__ import annotations

import hashlib
import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))


def _modulo():
    percorso = RADICE / "scripts" / "make_release_zip.py"
    spec = importlib.util.spec_from_file_location("make_release_zip", percorso)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture()
def finto_pacchetto(tmp_path, monkeypatch):
    """Un pacchetto finto ma della forma giusta, sotto una radice usa e getta."""
    mod = _modulo()
    pacchetto = tmp_path / "dist" / "MrRao-Portable"
    (pacchetto / "app").mkdir(parents=True)
    (pacchetto / "app" / "MrRao.exe").write_bytes(b"non e' un eseguibile vero")
    (pacchetto / "LEGGIMI.txt").write_text("ciao", encoding="utf-8")
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    return mod, tmp_path


def test_produce_i_due_archivi_e_le_impronte(finto_pacchetto, capsys):
    mod, radice = finto_pacchetto
    assert mod.main() == 0

    fisso = radice / "dist" / mod.NOME_FISSO
    versionati = list((radice / "dist").glob("MrRao-Portable-*.zip"))
    impronte = radice / "dist" / mod.NOME_IMPRONTE

    assert fisso.is_file(), "senza il nome fisso i link nei README danno 404"
    assert len(versionati) == 1, "manca l'archivio versionato"
    assert impronte.is_file()

    # Gli archivi devono contenere davvero il pacchetto.
    with zipfile.ZipFile(fisso) as z:
        nomi = z.namelist()
    assert any(n.endswith("app/MrRao.exe") for n in nomi), nomi


def test_l_impronta_e_quella_vera_del_file(finto_pacchetto):
    """Non basta che il file esista: deve dire il numero giusto."""
    mod, radice = finto_pacchetto
    assert mod.main() == 0

    righe = (radice / "dist" / mod.NOME_IMPRONTE).read_text(encoding="utf-8").splitlines()
    assert len(righe) == 2, righe

    for riga in righe:
        atteso, nome = riga.split("  ", 1)
        f = radice / "dist" / nome
        assert f.is_file(), f"l'impronta cita {nome}, che non esiste"
        vera = hashlib.sha256(f.read_bytes()).hexdigest()
        assert atteso == vera, f"impronta sbagliata per {nome}"


def test_le_due_copie_sono_identiche(finto_pacchetto):
    """Una sola impronta le copre entrambe solo se sono gli stessi byte."""
    mod, radice = finto_pacchetto
    assert mod.main() == 0
    fisso = radice / "dist" / mod.NOME_FISSO
    versionato = next((radice / "dist").glob("MrRao-Portable-*.zip"))
    assert fisso.read_bytes() == versionato.read_bytes()


def test_il_formato_e_quello_di_sha256sum(finto_pacchetto):
    """Due spazi fra impronta e nome: e' cio' che rende leggibile il file a
    `sha256sum -c`, che e' il motivo per cui si usa quel formato invece di
    inventarne uno."""
    mod, radice = finto_pacchetto
    assert mod.main() == 0
    testo = (radice / "dist" / mod.NOME_IMPRONTE).read_text(encoding="utf-8")
    for riga in testo.splitlines():
        impronta, separatore, nome = riga.partition("  ")
        assert separatore == "  ", repr(riga)
        assert len(impronta) == 64 and all(c in "0123456789abcdef" for c in impronta)
        assert nome.endswith(".zip")


def test_senza_pacchetto_si_ferma_e_lo_dice(tmp_path, monkeypatch, capsys):
    """Meglio nessun archivio che un archivio vuoto pubblicato per sbaglio."""
    mod = _modulo()
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    assert mod.main() == 1
    assert "ERRORE" in capsys.readouterr().err
