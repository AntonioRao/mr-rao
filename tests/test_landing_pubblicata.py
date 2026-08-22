# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Le pagine pubblicate devono venire dai sorgenti, e gli hash CSP da loro.

Il sito e' due file HTML con `<style>` e `<script>` scritti dentro la
pagina, e una CSP che li ammette **per impronta**. Basta cambiare uno spazio
nel blocco inline e l'impronta in `_headers` non corrisponde piu': il
browser blocca lo stile e il codice, e il sito va online **bianco**. Nessun
errore, nessun log, nessuno se ne accorge finche' non ci passa qualcuno.

Il rigeneratore (`docs/landing/rigenera_pubblicato.py`) e' scritto con cura e
si ferma su ogni passaggio che non trova niente. Il buco non era li': era
che **nessuno lo obbligava a girare**. Si modificava il sorgente, si faceva
commit, e la pagina pubblicata restava quella di prima con le sue impronte
di prima -- coerenti fra loro, e diverse da cio' che si era scritto.

Questo test non ricalcola le impronte per conto suo: **rilancia il
rigeneratore** su una copia di lavoro e pretende che non cambi niente. Cosi'
copre in un colpo i tre modi di sbagliare, che sono tre e non uno:

* sorgente modificato e rigeneratore mai lanciato;
* pagina pubblicata modificata a mano;
* impronte in `_headers` rimaste indietro.

Un test che si limitasse a ricalcolare gli hash dai file pubblicati direbbe
«tutto a posto» in tutti e tre i casi: i file pubblicati sarebbero coerenti
con se stessi. E' esattamente un controllo che non puo' fallire.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
LANDING = RADICE / "docs" / "landing"
PUBBLICA = LANDING / "publish"
# Il rigeneratore sta **fuori** dalla cartella pubblicata: finche' stava
# dentro, `wrangler pages deploy` lo spediva online insieme al sito.
RIGENERATORE = LANDING / "rigenera_pubblicato.py"

SORGENTI = ("01-protocollo-zero.html", "01-protocollo-zero.en.html")
GENERATI = ("index.html", "en/index.html", "_headers")

pytestmark = pytest.mark.skipif(
    not RIGENERATORE.exists(),
    reason="la landing non fa parte di questa copia",
)


@pytest.fixture(scope="module")
def rigenerata(tmp_path_factory) -> Path:
    """Una copia di lavoro con il rigeneratore appena lanciato.

    Si copia solo cio' che serve -- i due sorgenti, gli asset, `_headers` --
    e non i font: un megabyte di woff2 non entra nel calcolo delle impronte,
    e copiarlo a ogni giro renderebbe questo test abbastanza lento da
    invogliare a spegnerlo.
    """
    lavoro = tmp_path_factory.mktemp("landing")
    (lavoro / "publish" / "assets").mkdir(parents=True)
    for nome in SORGENTI:
        shutil.copyfile(LANDING / nome, lavoro / nome)
    shutil.copyfile(RIGENERATORE, lavoro / RIGENERATORE.name)
    shutil.copyfile(PUBBLICA / "_headers", lavoro / "publish" / "_headers")
    for asset in (PUBBLICA / "assets").iterdir():
        if asset.is_file():
            shutil.copyfile(asset, lavoro / "publish" / "assets" / asset.name)

    esito = subprocess.run(
        [sys.executable, str(lavoro / RIGENERATORE.name)],
        capture_output=True,
        text=True,
    )
    assert esito.returncode == 0, esito.stdout + esito.stderr
    return lavoro / "publish"


@pytest.mark.parametrize("nome", GENERATI)
def test_il_file_pubblicato_e_quello_che_il_rigeneratore_produce(rigenerata, nome):
    atteso = (rigenerata / nome).read_text(encoding="utf-8")
    reale = (PUBBLICA / nome).read_text(encoding="utf-8")
    assert reale == atteso, (
        f"{nome} non corrisponde ai sorgenti.\n"
        "Rilancia:  python docs/landing/rigenera_pubblicato.py"
    )


def test_le_impronte_csp_coprono_i_blocchi_inline_delle_due_pagine():
    """La riga che spiega *perche'* il confronto qui sopra e' quello giusto.

    Non ricalcola: legge `_headers` e conta. Due pagine, un blocco `<style>`
    e uno `<script>` ciascuna, una CSP sola per tutto il sito: se le
    impronte per direttiva non sono due, una delle due pagine e' scoperta e
    andra' online bianca -- e il confronto file-per-file qui sopra non se ne
    accorgerebbe, perche' il rigeneratore produrrebbe lo stesso `_headers`
    monco che c'e' gia'.
    """
    import re

    hdr = (PUBBLICA / "_headers").read_text(encoding="utf-8")
    for direttiva in ("script-src", "style-src"):
        trovate = re.search(rf"{direttiva} 'self'((?: 'sha256-[^']+')+)", hdr)
        assert trovate, f"nessuna impronta per {direttiva}"
        assert len(re.findall(r"sha256-", trovate.group(1))) == 2, (
            f"{direttiva}: attese 2 impronte, una per pagina"
        )


# --- cosa finisce online ----------------------------------------------------

# Tutto cio' che sta in `publish/` viene **pubblicato**: `wrangler pages
# deploy` spedisce la cartella, non l'elenco dei file tracciati da git.
#
# Il 22/08/2026 una verifica del sito ha trovato online due file che nessuno
# voleva pubblicare: `_rebuild.py` -- lo script che costruisce il sito,
# 8423 byte identici a quelli su disco -- e `test-results/.last-run.json`,
# un residuo di una corsa di Playwright mai tracciato da git. Nessuno dei due
# conteneva segreti. Il punto e' il meccanismo: al loro posto puo' esserci
# qualunque cosa qualcuno appoggi li' dentro, e nessuno se ne accorge.
#
# `.assetsignore` non serve: provato lo stesso giorno, Pages lo ignora e
# pubblica anche quello. L'unico modo di non pubblicare un file e' non
# tenerlo nella cartella, e questo elenco e' cio' che se ne accorge.
ESTENSIONI_AMMESSE = {".html", ".css", ".svg", ".ico", ".woff2", ".apk", ".txt"}
FILE_AMMESSI = {"_headers", "_redirects"}


def test_nella_cartella_pubblicata_non_ci_sono_file_di_troppo():
    inattesi = []
    for percorso in sorted(PUBBLICA.rglob("*")):
        if not percorso.is_file():
            continue
        relativo = percorso.relative_to(PUBBLICA)
        # `.wrangler/` e' la cache locale dello strumento: Pages salta le
        # cartelle che cominciano per punto, ed e' stato verificato online
        # (il suo contenuto risponde con la pagina 404, non con il file).
        if any(parte.startswith(".") for parte in relativo.parts):
            continue
        if percorso.name in FILE_AMMESSI:
            continue
        if percorso.suffix.lower() in ESTENSIONI_AMMESSE:
            continue
        inattesi.append(relativo.as_posix())

    assert inattesi == [], (
        "questi file finirebbero online al prossimo 'wrangler pages deploy':\n  "
        + "\n  ".join(inattesi)
        + "\nSpostali fuori da docs/landing/publish/, oppure — se devono "
        "davvero stare sul sito — aggiungili a FILE_AMMESSI qui sopra."
    )


def test_la_pagina_404_esiste_e_non_ha_inline_da_firmare():
    """Senza `404.html`, Pages rispondeva **200 con la homepage** a qualunque
    indirizzo inventato: `/​.git/HEAD`, `/​.env`, `/admin`. Non era un
    repository esposto — il corpo era la homepage — ma ogni scanner lo
    segnala come critico, e chi legge il rapporto di fretta ci crede.

    L'assenza di inline non e' pignoleria: la CSP del sito ammette
    `<style>` e `<script>` solo per impronta, e le impronte le calcola il
    rigeneratore sulle **due** pagine principali. Un inline qui verrebbe
    bloccato, e la pagina d'errore comparirebbe senza stile.
    """
    pagina = PUBBLICA / "404.html"
    assert pagina.is_file(), "manca docs/landing/publish/404.html"
    # I commenti si tolgono prima di guardare: dentro c'e' scritto **perche'**
    # un `<style>` qui non si puo' mettere, e un controllo che inciampa nella
    # propria spiegazione misura il testo, non la pagina. (Successo subito:
    # la prima versione di questo banco falliva su questo file.)
    testo = re.sub(r"<!--.*?-->", " ", pagina.read_text(encoding="utf-8"), flags=re.S).lower()
    assert "<style" not in testo, "un <style> qui verrebbe bloccato dalla CSP"
    assert "<script" not in testo, "uno <script> qui verrebbe bloccato dalla CSP"
    assert (PUBBLICA / "404.css").is_file(), "manca il foglio di stile della 404"


def test_il_security_txt_e_valido_e_non_sta_per_scadere():
    """RFC 9116, e soprattutto la data.

    **Un `security.txt` scaduto è peggio di uno assente**: chi lo legge crede
    di avere un canale che invece nessuno sta più guardando. La scadenza è
    l'unico campo di questo file che marcisce da solo, e non c'è niente altro
    nel repository che se ne accorgerebbe.

    Trenta giorni di margine e non zero: un banco che diventa rosso **il
    giorno dopo** la scadenza segnala un danno già fatto.

    Il file sta in `/security.txt` e non in `/.well-known/`, e non è una
    scelta: **Cloudflare Pages non pubblica le cartelle che cominciano per
    punto** — misurato il 22/08/2026, il file al suo posto standard rispondeva
    404. All'indirizzo di RFC 9116 ci arriva una riscrittura in `_redirects`,
    ed è per questo che quella riga va verificata insieme al file.
    """
    from datetime import datetime, timedelta, timezone

    percorso = PUBBLICA / "security.txt"
    assert percorso.is_file(), "manca docs/landing/publish/security.txt"
    testo = percorso.read_text(encoding="utf-8")

    campi = dict(
        riga.split(":", 1)
        for riga in testo.splitlines()
        if riga and not riga.startswith("#") and ":" in riga
    )
    for obbligatorio in ("Contact", "Expires"):
        assert obbligatorio in campi, f"RFC 9116 richiede il campo {obbligatorio}"

    scadenza = datetime.fromisoformat(campi["Expires"].strip().replace("Z", "+00:00"))
    fra_un_mese = datetime.now(timezone.utc) + timedelta(days=30)
    assert scadenza > fra_un_mese, (
        f"security.txt scade il {scadenza:%d/%m/%Y}: aggiorna `Expires` in "
        "docs/landing/publish/security.txt e ripubblica il sito. Un file "
        "scaduto promette un canale che nessuno guarda."
    )

    atteso = "https://rao.valor-cyber.com/.well-known/security.txt"
    assert campi.get("Canonical", "").strip() == atteso, (
        "`Canonical` deve essere l'indirizzo di RFC 9116, non quello reale del file"
    )

    riscrittura = (PUBBLICA / "_redirects").read_text(encoding="utf-8")
    assert "/.well-known/security.txt" in riscrittura and "200" in riscrittura, (
        "senza la riscrittura in _redirects l'indirizzo di RFC 9116 risponde 404"
    )


def test_tutte_le_pagine_hanno_un_menu_a_scomparsa():
    """La stessa barra deve comportarsi allo stesso modo su tutto il sito.

    Non era così: le pagine con `sito-nav.css` nascondevano le voci dentro un
    `<details class="menu">` sotto i 72rem, la home e la sua versione inglese
    no — tenevano tutte e undici le voci, che su 375 px andavano a capo tre
    volte. La barra diventava alta 187 px contro i 96 riservati dall'hero:
    novanta pixel di titolo sotto al vetro. Misurato sul sito pubblicato.

    Qui si verifica la **presenza** del menu in ogni pagina, che è la parte
    che si può verificare senza un browser. Che la soglia scatti davvero, e a
    che altezza finisca la barra, si guarda sul sito con gli strumenti del
    browser: un file HTML non ha un layout.
    """
    pagine = [p for p in PUBBLICA.rglob("index.html")]
    assert len(pagine) >= 6, f"pagine trovate: {len(pagine)}"
    senza = [
        p.relative_to(PUBBLICA).as_posix()
        for p in pagine
        if 'class="menu"' not in p.read_text(encoding="utf-8")
    ]
    assert senza == [], (
        "queste pagine non hanno il menu a scomparsa: su un telefono le voci "
        "restano nella barra e la fanno crescere sopra al contenuto\n  "
        + "\n  ".join(senza)
    )


def test_il_foglio_condiviso_e_la_sua_versione_vanno_insieme():
    """Cambiare `sito-nav.css` senza alzare il `?v=` non si vede subito.

    La cartella è servita con `Cache-Control: max-age=14400`: chi ha visitato
    il sito nelle ultime quattro ore continua a usare il foglio vecchio. È
    già successo due volte in un giorno — la prima con `mobile/stile.css`, la
    seconda proprio con questo file, e in mezzo c'è stata una misura che
    diceva «la correzione non funziona» mentre online il file nuovo c'era.

    L'impronta qui sotto è la sola cosa che lega le due modifiche: se il
    foglio cambia e questa non viene aggiornata, il banco si ferma e ricorda
    di alzare anche il numero nelle pagine.
    """
    import hashlib

    IMPRONTA = "f84522513f40c52568eff5e05c9df258a3241e24329334baed80c0c54716f2d0"
    VERSIONE = "sito-nav.css?v=4"

    foglio = PUBBLICA / "sito-nav.css"
    reale = hashlib.sha256(foglio.read_bytes()).hexdigest()
    assert reale == IMPRONTA, (
        "sito-nav.css è cambiato: alza il `?v=` nelle pagine che lo linkano e "
        "aggiorna IMPRONTA qui sopra. Senza il bump, chi è passato di recente "
        "vede il foglio vecchio per quattro ore."
    )

    # Chi lo **linka**, non chi lo nomina: la home lo cita in un commento
    # (spiega di usare la sua stessa soglia) e finiva fra le pagine da
    # correggere pur non caricandolo affatto.
    usano = [
        p
        for p in PUBBLICA.rglob("*.html")
        if 'href="/sito-nav.css' in p.read_text(encoding="utf-8")
        or 'href="sito-nav.css' in p.read_text(encoding="utf-8")
        or 'href="../sito-nav.css' in p.read_text(encoding="utf-8")
        or 'href="../../sito-nav.css' in p.read_text(encoding="utf-8")
    ]
    assert usano, "nessuna pagina usa il foglio condiviso: l'elenco si è svuotato"
    sbagliate = [
        p.relative_to(PUBBLICA).as_posix()
        for p in usano
        if VERSIONE not in p.read_text(encoding="utf-8")
    ]
    assert sbagliate == [], f"queste pagine non chiedono {VERSIONE}:\n  " + "\n  ".join(sbagliate)
