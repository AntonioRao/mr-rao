# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""L'elenco delle licenze dice cosa c'e' nel prodotto, non cosa c'e' nel venv.

Il 3 ottobre 2026 il passo delle licenze del quality gate era rosso sulla
macchina di sviluppo, e non per una dipendenza cambiata: nel venv c'erano
sedici pacchetti in piu' — le dipendenze di uno strumento di audit provato e
poi disinstallato, rimaste li'. `gen_third_party.py` elencava **tutto cio' che
trovava installato**, quindi per lui erano terze parti di Mr. Rao.

Il messaggio d'errore diceva «rigenerare». Rigenerando, sedici pacchetti che
il prodotto non usa sarebbero finiti in un file che si distribuisce e che
dichiara licenze. E' il difetto di un controllo che ha ragione a fermarsi e
da' il rimedio sbagliato.

Adesso l'elenco parte da cio' che Mr. Rao **dichiara** e segue cio' che quei
pacchetti richiedono. Qui si prova quella regola su ambienti inventati, dove
si sa cosa deve uscire.

L'import segue la strada di `test_changelog_versione.py`: `scripts/` non e'
un pacchetto, quindi si aggiunge a `sys.path`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("packaging")
from packaging.requirements import Requirement  # noqa: E402

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE / "scripts") not in sys.path:
    sys.path.insert(0, str(RADICE / "scripts"))

import gen_third_party  # noqa: E402
from gen_third_party import (  # noqa: E402
    RUOLI,
    chiusura,
    dichiarati,
    nome_canonico,
    raccogli,
)


class _Metadati(dict):
    """Quel tanto dei metadati di un pacchetto che lo script va a leggere."""

    def get_all(self, chiave):
        valore = self.get(chiave)
        return [valore] if valore else []


class _Finta:
    """Un pacchetto installato che non esiste."""

    def __init__(self, nome: str, *richiede: str, versione: str = "1.0"):
        self.metadata = _Metadati(Name=nome, License="MIT")
        self.requires = list(richiede)
        self.version = versione


def _ambiente(*pacchetti: _Finta) -> dict:
    return {nome_canonico(p.metadata["Name"]): p for p in pacchetti}


def _radici(*nomi: str) -> list:
    return [Requirement(n) for n in nomi]


def test_un_pacchetto_installato_e_non_richiesto_resta_fuori():
    """Il caso misurato: nel venv c'e', nel prodotto no."""
    ambiente = _ambiente(
        _Finta("flask", "werkzeug>=3"),
        _Finta("werkzeug"),
        _Finta("rich", "markdown-it-py"),      # rimasto da uno strumento tolto
        _Finta("markdown-it-py"),
        _Finta("pip"),
    )
    nomi, mancanti = chiusura(_radici("flask"), ambiente)
    assert nomi == {"flask", "werkzeug"}, nomi
    assert mancanti == set()


def test_le_dipendenze_si_seguono_fino_in_fondo():
    """Chi ridistribuisce deve l'attribuzione anche al terzo livello."""
    ambiente = _ambiente(
        _Finta("a", "b"), _Finta("b", "c>=2"), _Finta("c", "d"), _Finta("d"))
    nomi, _ = chiusura(_radici("a"), ambiente)
    assert nomi == {"a", "b", "c", "d"}


def test_un_giro_di_dipendenze_non_fa_girare_in_tondo():
    ambiente = _ambiente(_Finta("a", "b"), _Finta("b", "a"))
    nomi, _ = chiusura(_radici("a"), ambiente)
    assert nomi == {"a", "b"}


def test_la_dipendenza_di_un_altro_sistema_non_entra_e_non_manca():
    """`; sys_platform == ...` falso qui: non e' del prodotto, e non e' un buco."""
    ambiente = _ambiente(
        _Finta("a", 'solo-altrove; sys_platform == "un-sistema-che-non-esiste"',
               f'solo-qui; sys_platform == "{sys.platform}"'),
        _Finta("solo-altrove"),
        _Finta("solo-qui"),
    )
    nomi, mancanti = chiusura(_radici("a"), ambiente)
    assert nomi == {"a", "solo-qui"}, nomi
    assert mancanti == set(), "una dipendenza di un altro sistema non e' «mancante»"


def test_una_funzione_opzionale_entra_solo_se_qualcuno_la_chiede():
    ambiente = _ambiente(
        _Finta("a", 'opzionale; extra == "ocr"', "sempre"),
        _Finta("opzionale"),
        _Finta("sempre"),
    )
    senza, _ = chiusura(_radici("a"), ambiente)
    assert senza == {"a", "sempre"}, senza
    con, _ = chiusura(_radici("a[ocr]"), ambiente)
    assert con == {"a", "sempre", "opzionale"}, con


def test_i_nomi_si_confrontano_come_li_confronta_pip():
    """`pdfminer.six` installato, `pdfminer_six` richiesto: e' lo stesso."""
    ambiente = _ambiente(_Finta("a", "Pdfminer_Six>=1"), _Finta("pdfminer.six"))
    nomi, mancanti = chiusura(_radici("A"), ambiente)
    assert nomi == {"a", "pdfminer-six"}, nomi
    assert mancanti == set()


def test_cio_che_e_richiesto_e_non_c_e_si_dice():
    """Un elenco incompleto in silenzio e' peggio di uno che lo ammette."""
    ambiente = _ambiente(_Finta("a", "b"))
    nomi, mancanti = chiusura(_radici("a"), ambiente)
    assert nomi == {"a"}
    assert mancanti == {"b"}


def test_l_elenco_che_si_scrive_e_quello_della_chiusura(monkeypatch, tmp_path):
    """Non basta che la regola esista: dev'essere quella che lo script usa.

    Si da' allo script un ambiente inventato con un intruso dentro, e si
    guarda cosa finisce nelle righe che scriverebbe.
    """
    requisiti = tmp_path / "requirements.txt"
    requisiti.write_text("flask>=3  # il server\n-r altro.txt\n\n# un commento\n",
                         encoding="utf-8")
    monkeypatch.setattr(gen_third_party, "REQUISITI", (requisiti.name,))
    monkeypatch.setattr(gen_third_party, "ROOT", tmp_path)
    monkeypatch.setattr(gen_third_party, "distributions", lambda: [
        _Finta("Flask", "Werkzeug>=3"), _Finta("Werkzeug"), _Finta("rich"), _Finta("pip")])

    assert [v["nome"] for v in raccogli()] == ["Flask", "Werkzeug"]


def test_i_requisiti_veri_si_leggono_tutti():
    """`requirements.txt` com'e' adesso: commenti in coda, e un `-r` nel secondo file."""
    nomi = {nome_canonico(r.name) for r in dichiarati()}
    for atteso in ("flask", "pikepdf", "pypdfium2", "pdfminer-six", "pyinstaller"):
        assert atteso in nomi, f"{atteso} non letto dai file dei requisiti: {sorted(nomi)}"
    assert not any(n.startswith("-") or " " in n for n in nomi), nomi


def test_ogni_dipendenza_dichiarata_ha_il_suo_ruolo_e_viceversa():
    """La tabella delle dirette e i file dei requisiti dicono la stessa cosa.

    `RUOLI` decide cosa finisce fra le «dipendenze dirette» del file
    pubblicato. E' scritta a mano, e il commento che la accompagna racconta
    che era gia' scivolata nelle due direzioni: una indiretta fra le dirette,
    otto dirette fra le indirette. Qui il confronto lo fa un test.
    """
    con_un_ruolo = {nome_canonico(n) for n in RUOLI}
    dichiarate = {nome_canonico(r.name) for r in dichiarati()}
    assert con_un_ruolo == dichiarate, (
        f"senza ruolo: {sorted(dichiarate - con_un_ruolo)}; "
        f"con un ruolo ma non dichiarate: {sorted(con_un_ruolo - dichiarate)}")
