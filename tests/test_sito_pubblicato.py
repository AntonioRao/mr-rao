# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il controllo sul sito pubblicato deve saper dire che il sito e' indietro.

Il difetto da cui viene tutto (2026-08-09): la landing inglese corretta,
committata e pushata, e online la vecchia. Il progetto Cloudflare Pages e' a
caricamento diretto, quindi `git push` non pubblica niente e nessuno lo dice.
`scripts/check_sito_pubblicato.py` esiste per dirlo.

Qui si verifica **soprattutto che sappia dire di no**. Un controllo di rete
e' il posto piu' facile del mondo in cui scrivere qualcosa che tace: basta un
`except` largo, e in caso di errore la funzione torna «tutto a posto» proprio
nei momenti in cui non ha guardato niente. Quindi a ogni esito corrisponde
qui un caso costruito apposta, e i tre esiti diversi da «allineato» sono
asseriti come **distinti fra loro**: rete assente non e' allineato.

**Nessun test tocca la rete.** La lettura della pagina e' un parametro
iniettabile (`lettore`), e una fixture automatica fa esplodere `urlopen` se
qualcuno prova lo stesso: senza quella fixture, un test scritto male
passerebbe qui e fallirebbe in CI il giorno che il runner non ha uscita —
oppure, peggio, resterebbe verde interrogando il sito vero e misurando
qualcosa che non c'entra con il codice che sta verificando.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE / "scripts") not in sys.path:
    sys.path.insert(0, str(RADICE / "scripts"))

import check_sito_pubblicato as controllo  # noqa: E402
from check_sito_pubblicato import (  # noqa: E402
    ALLINEATO,
    CIECO,
    DISALLINEATO,
    IRRAGGIUNGIBILE,
    Irraggiungibile,
    confronta_pagina,
    controlla,
    indirizzi_e_attese,
    indirizzi_pubblicati,
    pagine_locali,
    peggiore,
    versioni_dichiarate,
)
from config import APP_VERSION  # noqa: E402

VECCHIA = "1.7.2"
FUTURA = "99.0.0"
assert VECCHIA != APP_VERSION, "la versione usata come 'vecchia' e' quella corrente"

URL = "https://esempio.invalid/"


@pytest.fixture(autouse=True)
def rete_vietata(monkeypatch):
    """Se un test di questo file apre una connessione, e' un difetto del test.

    Non e' pignoleria: e' l'unica cosa che rende ripetibile un banco che
    verifica del codice di rete. Un test che chiama davvero il sito misura lo
    stato del sito, non quello del controllo — e cambia risposta a seconda
    del giorno, che e' il modo in cui un banco smette di essere una prova.
    """
    def vietato(*a, **k):
        raise AssertionError("questo test ha provato a usare la rete davvero")

    monkeypatch.setattr(controllo.urllib.request, "urlopen", vietato)


def _pagina(corpo: str) -> str:
    return f"<!DOCTYPE html><html><body>{corpo}</body></html>"


def _lettore(html: str):
    return lambda url: html


def _muto(url: str):
    raise Irraggiungibile("URLError: [Errno 11001] getaddrinfo failed")


# --- da dove prende gli indirizzi -------------------------------------------


def test_ci_sono_pagine_pubblicate_da_interrogare():
    """Zero pagine vuol dire zero problemi, per sempre e in silenzio: senza
    questo, tutto il resto passerebbe per il motivo sbagliato."""
    pagine = pagine_locali()
    assert pagine, "git non traccia nessuna pagina in docs/landing/publish/"
    assert any(p.name == "index.html" for p in pagine)


def test_gli_indirizzi_arrivano_dal_canonical_delle_pagine_vere():
    """L'indirizzo non e' scritto nello script apposta: una seconda copia e'
    una seconda cosa che puo' restare indietro il giorno che il dominio
    cambia, e il controllo interrogherebbe — verde — un sito non nostro."""
    indirizzi = indirizzi_pubblicati()
    assert indirizzi, "nessun <link rel=canonical> https nelle pagine pubblicate"
    assert all(u.startswith("https://") for u in indirizzi), indirizzi
    assert len(set(indirizzi)) == len(indirizzi), "indirizzi ripetuti"


def test_un_canonical_non_https_viene_ignorato(tmp_path):
    """`urlopen` aprirebbe volentieri un `file://` letto da un file del
    repository, e il controllo direbbe «allineato» confrontando la pagina
    con se stessa: un verde ottenuto senza uscire dal disco."""
    finta = tmp_path / "index.html"
    finta.write_text(
        '<link rel="canonical" href="file:///C:/x/index.html" />'
        '<link rel="canonical" href="http://insicuro.invalid/" />',
        encoding="utf-8",
    )
    assert indirizzi_pubblicati([finta]) == []


# --- come legge il numero ---------------------------------------------------


def test_legge_la_versione_dalla_pagina():
    assert versioni_dichiarate(_pagina(f"<span>v{APP_VERSION}</span>")) == [APP_VERSION]


def test_non_legge_i_numeri_dentro_script_e_style():
    """Dentro `<style>` ci sono numeri a palate e nessuna promessa a nessuno:
    scambiarne uno per una versione renderebbe rosso un sito giusto."""
    html = _pagina(
        f"<style>.x{{transform:translate3d(1.2.3)}}</style>"
        f"<script>const v='v{VECCHIA}';</script><p>v{APP_VERSION}</p>"
    )
    assert versioni_dichiarate(html) == [APP_VERSION]


def test_le_pagine_pubblicate_vere_dichiarano_un_numero_leggibile():
    """Il controllo dev'essere tarato sul formato **vero** delle pagine.

    Con solo HTML finto questo banco resterebbe verde anche se il numero
    online fosse scritto in un modo che la regex non prende: sarebbe un
    controllo che passa i suoi test senza saper guardare il sito.

    Qui si verifica che il numero **si legga**, non che sia `APP_VERSION`:
    quel confronto e' di `landing_invecchiate()` nel gate, e ripeterlo qui
    renderebbe rosso questo file per un motivo che non lo riguarda — in
    particolare nella finestra in cui si bumpa la versione e le pagine non
    sono ancora state rinumerate. Un test che diventa rosso a ogni release
    per un difetto altrui e' il modo piu' rapido per farlo togliere.
    """
    pagine = pagine_locali()
    assert pagine
    for pagina in pagine:
        trovate = versioni_dichiarate(pagina.read_text(encoding="utf-8"))
        assert len(trovate) == 1, (
            f"{pagina.name} dichiara {trovate or 'nessuna versione'}: online il "
            f"controllo leggerebbe la stessa cosa, e con zero numeri direbbe "
            f"«cieco» invece di confrontare"
        )


# --- i quattro esiti --------------------------------------------------------


def test_sito_allineato():
    esito = confronta_pagina(URL, APP_VERSION, _lettore(_pagina(f"v{APP_VERSION}")))
    assert esito.stato == ALLINEATO


def test_sito_indietro_viene_detto():
    """Il caso per cui esiste: online la vecchia, in git la nuova."""
    esito = confronta_pagina(URL, APP_VERSION, _lettore(_pagina(f"v{VECCHIA}")))
    assert esito.stato == DISALLINEATO
    assert VECCHIA in esito.dettaglio and APP_VERSION in esito.dettaglio
    assert "indietro" in esito.dettaglio


def test_il_messaggio_dice_cosa_fare():
    """Un rosso che non dice il comando da lanciare si impara a rimandare."""
    esito = confronta_pagina(URL, APP_VERSION, _lettore(_pagina(f"v{VECCHIA}")))
    assert "_rebuild.py" in esito.dettaglio
    assert "wrangler pages deploy" in esito.dettaglio


def test_sito_avanti_e_comunque_un_disallineamento():
    """Online piu' nuovo del repository vuol dire copia locale indietro, o
    qualcosa pubblicato che non e' mai stato committato. Chiamarlo «a posto»
    perche' il sito non e' vecchio nasconderebbe il secondo caso."""
    esito = confronta_pagina(URL, APP_VERSION, _lettore(_pagina(f"v{FUTURA}")))
    assert esito.stato == DISALLINEATO
    assert "avanti" in esito.dettaglio


def test_rete_assente_non_e_allineato():
    """Il cuore della faccenda. Un controllo di rete che in caso di errore
    tace e' verde proprio quando non ha guardato niente."""
    esito = confronta_pagina(URL, APP_VERSION, _muto)
    assert esito.stato == IRRAGGIUNGIBILE
    assert esito.stato != ALLINEATO
    assert "getaddrinfo" in esito.dettaglio, "il motivo non viene riportato"


def test_pagina_senza_versione_e_un_controllo_cieco():
    """Se il numero sparisce dal sito, il confronto gira a vuoto: non e' una
    buona notizia, e' un controllo spento."""
    esito = confronta_pagina(URL, APP_VERSION, _lettore(_pagina("<p>niente numeri</p>")))
    assert esito.stato == CIECO
    assert "_RE_VERSIONE_LANDING" in esito.dettaglio, "non dice dove intervenire"


def test_nessun_indirizzo_da_guardare_e_cieco():
    esiti = controlla([], APP_VERSION, _lettore(_pagina(f"v{APP_VERSION}")))
    assert [e.stato for e in esiti] == [CIECO]


def test_il_piu_grave_non_e_il_piu_recente():
    """Con piu' pagine si esce con l'esito peggiore, e «cieco» viene prima di
    tutto: mette in dubbio anche i verdi stampati sopra di lui."""
    esiti = [
        controllo.Esito("a", ALLINEATO, ""),
        controllo.Esito("b", IRRAGGIUNGIBILE, ""),
        controllo.Esito("c", DISALLINEATO, ""),
    ]
    assert peggiore(esiti) == DISALLINEATO
    assert peggiore(esiti + [controllo.Esito("d", CIECO, "")]) == CIECO


# --- i codici di uscita -----------------------------------------------------


def _main_iniettando(lettore, argv) -> int:
    """`main()` con la lettura sostituita: il codice di uscita e' cio' che
    legge chi lancia il controllo, e va verificato su quello vero."""
    originale = controllo.scarica
    controllo.scarica = lambda url, timeout=None, tentativi=None: lettore(url)
    try:
        return controllo.main(argv)
    finally:
        controllo.scarica = originale


@pytest.mark.parametrize(
    ("lettore", "atteso"),
    [
        (_lettore(_pagina(f"v{APP_VERSION}")), 0),
        (_lettore(_pagina(f"v{VECCHIA}")), 1),
        (_muto, 2),
        (_lettore(_pagina("<p>niente</p>")), 3),
    ],
    ids=["allineato", "indietro", "irraggiungibile", "cieco"],
)
def test_ogni_esito_ha_il_suo_codice_di_uscita(lettore, atteso):
    """Quattro esiti, quattro codici. Se «irraggiungibile» uscisse con 0,
    una rete giu' passerebbe per un sito aggiornato — ed e' esattamente il
    silenzio che questo controllo esiste per rompere."""
    assert _main_iniettando(lettore, ["--url", URL]) == atteso


def test_tollerare_la_rete_assente_non_e_un_via_libera(capsys):
    """L'opzione serve a chi lancia il controllo offline: dire a una persona
    senza rete che il suo sito e' rotto e' un falso rosso. Ma il messaggio
    deve restare, altrimenti diventa un modo per farlo tacere sempre."""
    codice = _main_iniettando(_muto, ["--url", URL, "--tollera-rete-assente"])
    assert codice == 0
    letto = capsys.readouterr()
    assert "NON e' un via libera" in letto.out
    assert IRRAGGIUNGIBILE in letto.err


def test_tollerare_la_rete_assente_non_nasconde_un_sito_indietro():
    """L'opzione perdona un esito solo. Se perdonasse anche il rosso vero,
    sarebbe un interruttore per spegnere il controllo."""
    codice = _main_iniettando(
        _lettore(_pagina(f"v{VECCHIA}")), ["--url", URL, "--tollera-rete-assente"]
    )
    assert codice == 1


# --- dove gira (e dove non gira) --------------------------------------------


def test_non_sta_nel_gate_bloccante():
    """Non e' una dimenticanza, e' la decisione (P3.17).

    Fra il push del bump di versione e la pubblicazione del sito passa del
    tempo, e in quella finestra il sito **e' legittimamente indietro**: un
    gate rosso per mezz'ora dopo ogni release non segnala un difetto,
    addestra a ignorare il rosso — e il rosso ignorato non e' quello di
    questo controllo, e' quello di tutti gli altri passi del gate.

    Il giorno che qualcuno lo aggiunge, questo test lo dice prima.
    """
    for percorso in ("scripts/quality_gate.bat", ".github/workflows/ci.yml"):
        testo = (RADICE / percorso).read_text(encoding="utf-8")
        assert "check_sito_pubblicato" not in testo, (
            f"{percorso} esegue il controllo sul sito pubblicato. E' un "
            f"controllo periodico, non un cancello: nella finestra fra bump e "
            f"deploy il sito e' indietro per davvero e il gate diventerebbe "
            f"rosso a ogni release"
        )


def test_esiste_il_controllo_programmato():
    """Uno script che non lancia nessuno e' un controllo che non c'e'."""
    workflow = RADICE / ".github" / "workflows" / "sito-pubblicato.yml"
    assert workflow.is_file(), "manca il workflow che esegue il controllo"

    import yaml

    config = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    # In YAML `on:` e' il booleano vero, non la stringa "on".
    eventi = config.get(True) or config.get("on") or {}
    assert "schedule" in eventi, "senza cadenza, il controllo dipende dal ricordarsene"
    assert "workflow_dispatch" in eventi, "deve potersi lanciare a mano dopo un deploy"
    assert "push" not in eventi, (
        "su push il controllo sarebbe rosso in ogni finestra fra bump e deploy"
    )

    comandi = " ".join(
        str(p.get("run", "")) for p in config["jobs"]["controlla"]["steps"]
    )
    assert "scripts/check_sito_pubblicato.py" in comandi
    assert "--tollera-rete-assente" not in comandi, (
        "sul runner «non risponde» e' una notizia vera, non un falso rosso"
    )


# --- ogni pagina sulla sua versione ------------------------------------------


def test_ogni_pagina_porta_la_versione_che_deve_dichiarare():
    """Le pagine della mobile non si confrontano con `APP_VERSION`.

    Prima lo facevano, e il controllo giornaliero le dichiarava disallineate
    **appena pubblicate**: «online c'e' la 0.1.6 (indietro), APP_VERSION e'
    1.27.5». Due righe rosse fisse in un controllo che ne ha quattro.
    """
    attese = indirizzi_e_attese()
    assert attese, "nessun indirizzo canonico"
    assert [u for u, _, _ in attese] == indirizzi_pubblicati(), (
        "le due funzioni non guardano piu' le stesse pagine"
    )

    mobile = [(u, a, c) for u, a, c in attese if "/mobile/" in u]
    altre = [(u, a, c) for u, a, c in attese if "/mobile/" not in u]
    assert mobile, "nessuna pagina della mobile: l'elenco non le prende piu'"
    assert altre, "nessuna pagina del portable"

    for _, attesa, di_chi in altre:
        assert attesa == APP_VERSION and di_chi == "APP_VERSION"
    for url, attesa, di_chi in mobile:
        assert di_chi == "Mr. Rao Mobile", url
        # Il punto della verifica: l'attesa dev'essere **diversa** da
        # APP_VERSION. Se un giorno coincidessero per caso, questo test
        # smetterebbe di dire qualcosa senza diventare rosso.
        assert attesa != APP_VERSION, (
            "l'attesa della mobile coincide con APP_VERSION: questo banco non "
            "distingue piu' il caso che deve distinguere"
        )


def test_una_pagina_ferma_a_una_versione_vecchia_resta_rossa():
    """Cambiare il termine di paragone non e' esentare.

    Il rischio della correzione era questo: una cartella «trattata a parte»
    che finisce per non essere piu' controllata affatto. Qui si verifica che
    il rosso ci sia ancora, e che nomini il prodotto giusto — dire
    «APP_VERSION e' 1.27.5» su una pagina della mobile manda a correggere la
    cosa sbagliata.
    """
    esito = confronta_pagina(
        URL, "0.1.6", _lettore(_pagina("versione 0.1.5")), "Mr. Rao Mobile"
    )
    assert esito.stato == DISALLINEATO
    assert "0.1.5 (indietro)" in esito.dettaglio
    assert "Mr. Rao Mobile" in esito.dettaglio
    assert "APP_VERSION" not in esito.dettaglio
