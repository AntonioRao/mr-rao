# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Le due guardie della tutela del codice: intestazioni e impronte.

Nessuna delle due misure impedisce la copia -- questo repository e' pubblico
sotto AGPL, e la copia e' gia' legale. Servono a rendere visibile, con un
comando, se un obbligo della licenza (attribuzione) o un segnale di
provenienza (le impronte) sono ancora al loro posto dopo un refactoring.

Un test che non puo' fallire non e' un test. Per questo ogni guardia qui sotto
ha anche una versione "in negativo": costruisce un caso apposta rotto (un
file senza intestazione, un'impronta rimossa dal codice) e verifica che la
guardia lo dica. Se quella versione non fallisse mai con l'input rotto, la
guardia positiva sarebbe verde per costruzione, non per merito.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
SCRIPTS = RADICE / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import impronte  # noqa: E402
import marca_copyright  # noqa: E402


# --------------------------------------------------------------------------
# intestazioni: ogni sorgente di prima parte porta il marcatore
# --------------------------------------------------------------------------


def test_ci_sono_sorgenti_di_prima_parte_da_controllare():
    """Controllo positivo: se questo elenco fosse vuoto, il test sotto
    sarebbe verde perche' non ha esaminato niente, non perche' tutto e' a posto."""
    assert len(marca_copyright.sorgenti()) > 100


def test_tutte_le_sorgenti_di_prima_parte_sono_marcate():
    non_marcati = [p for p in marca_copyright.sorgenti()
                  if marca_copyright.applica(p, scrivi=False) == "marcato"]
    assert not non_marcati, (
        f"{len(non_marcati)} sorgenti senza intestazione di copyright: {non_marcati}. "
        f"Rimedio: python scripts/marca_copyright.py --scrivi"
    )


def test_un_file_senza_intestazione_viene_segnalato_come_da_marcare(tmp_path, monkeypatch):
    """Mutazione: un file di prima parte a cui manca l'intestazione DEVE
    tornare 'marcato' (cioe' 'ancora da fare'), non 'gia' marcato'."""
    monkeypatch.setattr(marca_copyright, "ROOT", tmp_path)
    (tmp_path / "nudo.py").write_text("x = 1\n", encoding="utf-8")

    assert marca_copyright.applica("nudo.py", scrivi=False) == "marcato"


def test_un_file_gia_marcato_non_viene_segnalato_due_volte(tmp_path, monkeypatch):
    """L'altra faccia della stessa mutazione: applicare l'intestazione e poi
    ricontrollare non deve tornare 'marcato' una seconda volta -- altrimenti
    lo strumento duplicherebbe l'intestazione a ogni rilancio."""
    monkeypatch.setattr(marca_copyright, "ROOT", tmp_path)
    (tmp_path / "nudo.py").write_text("x = 1\n", encoding="utf-8")
    marca_copyright.applica("nudo.py", scrivi=True)

    assert marca_copyright.applica("nudo.py", scrivi=False) == "gia' marcato"


def test_una_nota_agpl_in_prosa_non_viene_duplicata(tmp_path, monkeypatch):
    """Il caso reale di app.py e mr_rao/__init__.py: nota AGPL gia' in prosa,
    non in formato SPDX. Trovato controllando a mano l'esito su questo
    repository prima del primo --scrivi: senza questo controllo lo strumento
    avrebbe inserito una seconda intestazione sopra la prima."""
    monkeypatch.setattr(marca_copyright, "ROOT", tmp_path)
    (tmp_path / "con_prosa.py").write_text(
        '"""Modulo.\n\nCopyright (C) 2026 Qualcuno\n\n'
        "This program is free software: ... GNU Affero General Public License ...\n"
        '"""\nx = 1\n',
        encoding="utf-8",
    )

    assert marca_copyright.applica("con_prosa.py", scrivi=False) == "gia' marcato (prosa)"


# --------------------------------------------------------------------------
# impronte: il catalogo di provenienza punta ancora a codice vivo
# --------------------------------------------------------------------------


def _catalogo_reale_o_salta():
    if not impronte.CATALOGO.exists():
        pytest.skip(
            "provenance/impronte.json assente (CI, o clone senza materiale privato): salto. "
            "Il catalogo si genera con: python scripts/impronte.py raccogli"
        )
    return impronte.carica()


def test_provenance_e_ignorata_da_git():
    """Verifica su un PERCORSO dentro la cartella, non sulla cartella: un
    controllo su 'provenance/' che desse falso positivo per un motivo diverso
    dal .gitignore (per esempio la cartella non esiste ancora) non
    dimostrerebbe che il file che conta davvero e' escluso."""
    esito = subprocess.run(
        ["git", "check-ignore", "-q", "provenance/impronte.json"],
        cwd=RADICE,
    )
    assert esito.returncode == 0, "provenance/impronte.json non risulta ignorato da .gitignore"


def test_il_catalogo_reale_non_e_vuoto():
    cat = _catalogo_reale_o_salta()
    assert len(cat.get("impronte", [])) >= 20


def test_tutte_le_impronte_reali_sono_ancora_nel_codice():
    cat = _catalogo_reale_o_salta()
    presenti, mancanti = impronte.verifica_catalogo(cat)

    assert presenti, "controllo positivo: zero impronte trovate vorrebbe dire lettore rotto, non codice pulito"
    assert not mancanti, (
        f"{len(mancanti)} impronte non piu' nel codice: {[m['id'] for m in mancanti]}. "
        f"Se la riga e' cambiata di proposito: python scripts/impronte.py raccogli --rifai"
    )


def test_una_impronta_rimossa_dal_codice_risulta_mancante(tmp_path, monkeypatch):
    """Mutazione: la stessa frase, prima presente e poi tolta dal sorgente,
    deve spostarsi da 'presenti' a 'mancanti'. E' il cuore della guardia --
    se questo non fallisse con la frase tolta, `verifica` direbbe sempre 'ok'."""
    monkeypatch.setattr(impronte, "ROOT", tmp_path)
    (tmp_path / "modulo.py").write_text(
        "# una frase caratteristica di prova che non compare altrove\n", encoding="utf-8"
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "modulo.py"], cwd=tmp_path, check=True)
    catalogo = {"impronte": [{
        "id": "imp-prova", "tipo": "commento", "area": "core",
        "testo": "una frase caratteristica di prova che non compare altrove",
        "file": "modulo.py", "riga": 1,
    }]}

    presenti, mancanti = impronte.verifica_catalogo(catalogo)
    assert presenti and not mancanti, "la frase c'e' ancora: la mutazione non e' partita dal caso giusto"

    (tmp_path / "modulo.py").write_text("# la frase e' stata riscritta\n", encoding="utf-8")
    presenti2, mancanti2 = impronte.verifica_catalogo(catalogo)

    assert mancanti2 and not presenti2, "l'impronta rimossa non e' stata segnalata come mancante"
