# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Le invarianti dei documenti che si possono controllare sempre.

Il controllo completo sta in `scripts/check_docs.py` e lo esegue il quality
gate, perche' una delle quattro invarianti — il conteggio dei test — la
conosce solo chi ha appena eseguito l'intera suite, e `pytest` si lancia
spesso su un file solo.

Le altre tre non dipendono da come e' stato invocato pytest, quindi vale la
pena che scattino anche qui: chi lancia i test e basta si accorge lo stesso
di aver rotto un link o duplicato un identificativo.

L'elenco dei file lo da' `git ls-files`, non una lista scritta a mano. E' il
punto dell'intera faccenda: alla domanda «i documenti sono aggiornati?»
avevo risposto di si' guardando quelli che stavo modificando, e due erano
fermi da quindici release. Un controllo che parte da cio' che ho in mano
trova solo cio' che ho gia' guardato.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE / "scripts") not in sys.path:
    sys.path.insert(0, str(RADICE / "scripts"))

from check_docs import (  # noqa: E402
    documenti,
    id_duplicati,
    link_rotti,
    versioni_incoerenti,
)


def test_ci_sono_documenti_da_controllare():
    """Se `git ls-files` smettesse di trovarli, gli altri test passerebbero
    tutti per il motivo sbagliato: zero file, zero problemi."""
    trovati = documenti()
    assert len(trovati) >= 10
    nomi = {f.name for f in trovati}
    for atteso in ("README.md", "SECURITY.md", "BACKLOG.md", "PRIVACY.md"):
        assert atteso in nomi, f"{atteso} non e' fra i documenti tracciati"


def test_nessun_identificativo_duplicato():
    problemi = id_duplicati()
    assert not problemi, "\n".join(problemi)


def test_nessun_link_rotto():
    problemi = link_rotti()
    assert not problemi, "\n".join(problemi)


def test_nessuna_versione_vecchia():
    problemi = versioni_incoerenti()
    assert not problemi, "\n".join(problemi)


@pytest.mark.parametrize(
    "controllo", [id_duplicati, link_rotti, versioni_incoerenti]
)
def test_i_controlli_restituiscono_una_lista(controllo):
    """Un controllo che tornasse None passerebbe ogni assert `not problemi`
    senza guardare niente. E' il modo in cui questi presidi muoiono zitti."""
    assert isinstance(controllo(), list)


def test_claude_md_e_agents_md_restano_identici():
    """Due file con lo stesso contenuto sono due file che divergono.

    E' successo tre volte in questo repository nello stesso giorno:
    quality_gate.ps1 fermo a tre passi su cinque, due script di
    installazione che facevano quasi la stessa cosa, e l'elenco delle
    estensioni scritto in due posti con la disinstallazione che ne conosceva
    uno solo. Qui il rischio e' peggiore del solito, perche' a leggere il
    file sbagliato sarebbe un assistente: seguirebbe regole che nessuno ha
    piu' aggiornato, senza che nessuno se ne accorga.

    Restano due file perche' due strumenti diversi cercano due nomi diversi.
    Se un giorno uno dei due potesse diventare un rimando all'altro, tanto
    meglio -- ma finche' sono copie, la copia va verificata.
    """
    agents = RADICE / "AGENTS.md"
    claude = RADICE / "CLAUDE.md"
    assert agents.is_file() and claude.is_file(), "mancano le regole di lavoro"
    assert agents.read_bytes() == claude.read_bytes(), (
        "AGENTS.md e CLAUDE.md sono diversi: chi legge il secondo seguirebbe "
        "regole vecchie. Copia l'uno sull'altro."
    )


class TestRapportoPerIlBoard:
    """Il controllo sul rapporto non tracciato (invariante 9).

    Vive fuori da git — è un documento interno e il repository è pubblico —
    e quindi nessun altro controllo lo guarda: non compare in un diff quando
    si bumpa la versione, e le sue cifre non vengono confrontate con niente.
    Il 2026-08-14 dichiarava la 1.25.0, 1 999 test e «Plus 0.1.31 sugli
    store» quando lì c'era la 0.1.25.

    Si prova con file finti, non con quello vero: un banco che dipende da un
    file presente solo su una macchina è verde per costruzione altrove.
    """

    def scrivi(self, tmp_path, testo: str):
        import scripts.check_docs as cd

        f = tmp_path / cd.AUDIT
        f.write_text(testo, encoding="utf-8")
        return f

    def test_se_il_file_non_c_e_il_controllo_lo_dice(self, tmp_path, monkeypatch):
        import scripts.check_docs as cd

        monkeypatch.setattr(cd, "ROOT", tmp_path)
        problemi, letto = cd.audit_invecchiato(2133)
        assert problemi == []
        assert letto is False, "il salto va dichiarato, o sembra un controllo passato"

    def test_conteggio_vecchio_bocciato(self, tmp_path, monkeypatch):
        import scripts.check_docs as cd

        monkeypatch.setattr(cd, "ROOT", tmp_path)
        self.scrivi(tmp_path, "<p>1&nbsp;999 test desktop</p>")
        problemi, letto = cd.audit_invecchiato(2133)
        assert letto is True
        assert any("1999 test desktop" in p for p in problemi)

    def test_conteggio_giusto_passa(self, tmp_path, monkeypatch):
        import scripts.check_docs as cd

        monkeypatch.setattr(cd, "ROOT", tmp_path)
        self.scrivi(tmp_path, "<p>2&nbsp;133 test desktop</p>")
        problemi, _ = cd.audit_invecchiato(2133)
        assert problemi == []

    def test_il_numero_di_plus_non_viene_scambiato_per_quello_desktop(
        self, tmp_path, monkeypatch
    ):
        # Il primo giro del controllo bocciava «1 190 test Plus» dicendo che
        # avrebbe dovuto essere il numero del desktop: due numeri veri, e un
        # controllo che ne conosceva uno solo.
        import scripts.check_docs as cd

        monkeypatch.setattr(cd, "ROOT", tmp_path)
        self.scrivi(
            tmp_path, "<p>2&nbsp;133 test desktop · 1&nbsp;190 test Plus</p>"
        )
        problemi, _ = cd.audit_invecchiato(2133)
        assert problemi == []

    def test_se_la_frase_sparisce_il_controllo_lo_dice(self, tmp_path, monkeypatch):
        # Senza questa riga, cambiare il testo del rapporto spegnerebbe il
        # controllo in silenzio: zero conteggi trovati, zero problemi.
        import scripts.check_docs as cd

        monkeypatch.setattr(cd, "ROOT", tmp_path)
        self.scrivi(tmp_path, "<p>nessun numero qui</p>")
        problemi, _ = cd.audit_invecchiato(2133)
        assert any("non puo' piu' fallire" in p for p in problemi)
