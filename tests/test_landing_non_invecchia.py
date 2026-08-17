# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Le landing pubblicate devono invecchiare rumorosamente.

Il gate controllava i documenti `.md` e si fermava li'. Le landing in
`docs/landing/` sono `.html`, quindi non le apriva nessuno: `index.html` ha
dichiarato la **1.7.2** mentre `APP_VERSION` era la 1.11.0 — venti release —
e il gate e' stato verde tutte le volte. Non c'era un difetto nel controllo:
c'era una cartella fuori dal suo campo visivo.

Qui si verifica soprattutto una cosa: che il controllo nuovo **sappia dire di
no**. Un test che gli passa una pagina giusta e lo vede tacere non distingue
un controllo che funziona da un controllo che non guarda niente — ed e'
proprio quest'ultimo il caso da cui veniamo. Quindi ad ogni invariante
corrisponde qui una pagina sbagliata apposta, e l'asserzione e' che il
problema venga segnalato **e detto in modo azionabile**.

Il conteggio dei test sui file veri non si verifica qui, per lo stesso motivo
scritto in `test_documenti_pubblicati.py`: il numero vero lo conosce solo chi
ha appena eseguito l'intera suite, e pytest si lancia spesso su un file solo.
Quel confronto sta nel gate; qui si verifica il meccanismo, con numeri finti.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE / "scripts") not in sys.path:
    sys.path.insert(0, str(RADICE / "scripts"))

import check_docs  # noqa: E402
from check_docs import (  # noqa: E402
    _RE_VERSIONE_LANDING,
    _fonti_landing,
    conteggi_incoerenti,
    landing,
    landing_invecchiate,
    versioni_incoerenti,
)
from config import APP_VERSION  # noqa: E402

VECCHIA = "1.7.2"
assert VECCHIA != APP_VERSION, "la versione usata come 'vecchia' e' quella corrente"


def _pagina(corpo: str) -> list[tuple[str, str]]:
    """Una landing finta, nella forma in cui il controllo legge quelle vere."""
    return [("docs/landing/finta.html", f"<!DOCTYPE html><html><body>{corpo}</body></html>")]


# --- i file che il controllo guarda -----------------------------------------


def test_ci_sono_landing_tracciate():
    """Zero file vuol dire zero problemi, per sempre: senza questo, tutto il
    resto passerebbe per il motivo sbagliato."""
    trovate = landing()
    assert trovate, "git non traccia nessuna landing .html"
    nomi = {f.name for f in trovate}
    assert "index.html" in nomi


def test_le_bozze_gitignorate_restano_fuori():
    """Una bozza `02-*.html` nella cartella non dev'essere letta dal gate.

    Le bozze sono scarti di lavoro: dichiarano versioni vecchie e non le
    aggiornera' mai nessuno. Un glob sul disco le pescherebbe e il gate
    diventerebbe rosso per file che chi clona il repository non ha nemmeno —
    il modo piu' rapido per far disattivare un controllo.

    **La bozza se la crea il test.** La prima versione pretendeva invece che
    `02-carta-bianca.html` e `03-motore-vivo.html` esistessero gia' sul
    disco, e in CI e' fallita: sono gitignorate, quindi esistono solo sulla
    macchina di chi le ha scritte. Un test che dipende da un file fuori dal
    repository non prova niente a chiunque altro — ed e' la stessa forma di
    A.1, meta' del lavoro che viveva solo su un disco.
    """
    cartella = RADICE / "docs" / "landing"
    bozza = cartella / "02-bozza-di-prova.html"
    assert not bozza.exists(), f"{bozza.name} esiste gia': il test non lo sovrascrive"
    bozza.write_text(
        "<html lang='it'><body><p>Edizione 0.0.1</p></body></html>",
        encoding="utf-8",
    )
    try:
        # Il nome combacia con `docs/landing/02-*.html` in .gitignore, quindi
        # git non la traccia e `landing()` non deve vederla.
        assert bozza not in set(landing()), (
            f"{bozza.name} non e' tracciata da git ma il controllo la legge"
        )
    finally:
        bozza.unlink(missing_ok=True)


# --- lo stato attuale dei file veri -----------------------------------------


def test_nessuna_landing_dichiara_una_versione_vecchia():
    problemi = versioni_incoerenti(_fonti_landing(), _RE_VERSIONE_LANDING)
    assert not problemi, "\n".join(problemi)


def test_almeno_una_landing_dichiara_la_versione():
    """Se il numero sparisce dalle pagine, il confronto gira a vuoto e il
    controllo diventa una decorazione."""
    dichiarate = [
        v for _, testo in _fonti_landing() for v in _RE_VERSIONE_LANDING.findall(testo)
    ]
    assert dichiarate, "nessuna landing tracciata dichiara una versione"
    assert APP_VERSION in dichiarate


# --- il controllo sa diventare rosso ----------------------------------------


def test_una_versione_vecchia_viene_segnalata():
    """Il caso vero, riprodotto: e' cosi' che era scritto in index.html."""
    problemi = versioni_incoerenti(
        _pagina(f"<p>Stesso prodotto (v{VECCHIA}), toni opposti.</p>"),
        _RE_VERSIONE_LANDING,
    )
    assert len(problemi) == 1, problemi
    assert VECCHIA in problemi[0] and APP_VERSION in problemi[0]
    assert "finta.html" in problemi[0]


@pytest.mark.parametrize(
    "corpo",
    [
        f"<div class='badge'>Motore in ascolto - zero rete - v{VECCHIA}</div>",
        f"<p class='cover-mark'>Edizione {VECCHIA} - Italia</p>",
        f"<meta name='description' content='Mr. Rao versione {VECCHIA}' />",
        f"<small>v{VECCHIA} - offline by design</small>",
    ],
)
def test_le_forme_in_cui_una_pagina_scrive_il_numero(corpo):
    """Le landing non scrivono «versione 1.7.2»: scrivono un distintivo, una
    riga di copertina, un `<meta>`. Una regex che conosce una forma sola
    tacerebbe sulle altre tre — e sono forme prese dai file veri."""
    assert versioni_incoerenti(_pagina(corpo), _RE_VERSIONE_LANDING)


def test_un_conteggio_di_test_vecchio_viene_segnalato():
    problemi = conteggi_incoerenti(880, _pagina("<li>859 test verdi</li>"))
    assert len(problemi) == 1, problemi
    assert "859" in problemi[0] and "880" in problemi[0]


def test_un_conteggio_giusto_non_viene_segnalato():
    assert not conteggi_incoerenti(880, _pagina("<li>880 test verdi</li>"))


def test_l_indirizzo_di_loopback_non_e_una_versione():
    """`127.0.0.1` compare cinque volte nelle landing ed e' la cosa piu' vera
    che ci sia scritta. Un controllo che gridasse su quello verrebbe spento
    entro un giorno, e con lui il controllo sulle versioni."""
    assert not versioni_incoerenti(
        _pagina("<div>bind <strong>127.0.0.1</strong>:5000 - Data: 01.02.2024</div>"),
        _RE_VERSIONE_LANDING,
    )


def test_i_numeri_dentro_style_e_script_non_contano():
    """z-index, durate e coordinate sono codice, non promesse al lettore.

    Il taglio dei blocchi va verificato al contrario di come viene la voglia
    di scriverlo: non «il testo visibile e' rimasto», ma «cio' che era dentro
    <style> e <script> non fa scattare piu' niente». Un `sub` che sbagliasse
    e cancellasse mezza pagina supererebbe il primo controllo e non il secondo.
    """
    grezzo = (
        "<html><head><style>.a{z-index:1000;transform:translate3d(1.7.2)}</style>"
        "<script>const v = 'v1.7.2'; // 859 test</script></head>"
        f"<body><p>Stesso prodotto (v{APP_VERSION})</p></body></html>"
    )
    ripulito = check_docs._RE_CODICE_HTML.sub(" ", grezzo)
    assert not versioni_incoerenti([("finta.html", ripulito)], _RE_VERSIONE_LANDING)
    assert not conteggi_incoerenti(880, [("finta.html", ripulito)])
    # ...e il resto della pagina e' ancora li' da controllare.
    assert _RE_VERSIONE_LANDING.findall(ripulito) == [APP_VERSION]


# --- i messaggi dicono cosa fare --------------------------------------------


def test_per_l_artefatto_rigenerato_il_messaggio_indica_il_sorgente(monkeypatch):
    """`publish/index.html` lo scrive `_rebuild.py`. Dire «correggi questo
    file» significa far fare una modifica che il primo rebuild cancella."""
    monkeypatch.setattr(
        check_docs,
        "_fonti_landing",
        lambda: [("docs/landing/publish/index.html", f"<p>v{VECCHIA}</p>")],
    )
    problemi = landing_invecchiate(880)
    assert len(problemi) == 1, problemi
    assert "_rebuild.py" in problemi[0]
    assert "01-protocollo-zero.html" in problemi[0]


def test_per_una_pagina_scritta_a_mano_il_messaggio_dice_di_correggerla(monkeypatch):
    monkeypatch.setattr(
        check_docs,
        "_fonti_landing",
        lambda: [("docs/landing/index.html", f"<p>v{VECCHIA}</p>")],
    )
    problemi = landing_invecchiate(880)
    assert len(problemi) == 1, problemi
    assert "_rebuild.py" not in problemi[0]
    assert "Aggiorna il numero" in problemi[0]


# --- il controllo si accorge di essere stato spento -------------------------


def test_zero_landing_e_un_problema_non_un_successo(monkeypatch):
    monkeypatch.setattr(check_docs, "_fonti_landing", lambda: [])
    problemi = landing_invecchiate(880)
    assert problemi, "senza file il controllo direbbe verde per sempre"
    assert "check_docs.py" in problemi[0]


def test_landing_senza_nessuna_versione_e_un_problema(monkeypatch):
    """Pagine tutte giuste e pagine dove non c'e' piu' niente da confrontare
    danno lo stesso risultato — nessun problema — e sono cose opposte."""
    monkeypatch.setattr(
        check_docs,
        "_fonti_landing",
        lambda: [("docs/landing/index.html", "<p>nessun numero qui</p>")],
    )
    problemi = landing_invecchiate(880)
    assert problemi
    assert "_RE_VERSIONE_LANDING" in problemi[0]


def test_landing_invecchiate_restituisce_una_lista():
    """Un controllo che tornasse None passerebbe ogni `assert not problemi`
    senza guardare niente."""
    assert isinstance(landing_invecchiate(880), list)
