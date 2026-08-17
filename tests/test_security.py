# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Regressioni sulle difese del server locale.

Un server in ascolto su 127.0.0.1 è raggiungibile da qualunque pagina aperta
nel browser dell'utente. Tre attacchi distinti, tre controlli distinti:
- DNS rebinding: un dominio dell'attaccante che risolve a 127.0.0.1 leggeva
  le risposte → si blocca fissando l'header Host.
- CSRF: una POST cross-site (multipart è CORS-safelisted, quindi niente
  preflight) poteva avviare un hotfolder → si blocca rifiutando Sec-Fetch-Site
  esterni e Origin esterne.
- Vicini di porta: un'altra pagina su 127.0.0.1 con porta diversa ha lo stesso
  hostname, quindi il controllo di Origin la lascia passare → la ferma
  Sec-Fetch-Site, che la classifica "same-site".
"""
from io import BytesIO

import pytest

import config
from mr_rao.app_factory import _hostname


@pytest.mark.parametrize(
    ("grezzo", "atteso"),
    [
        ("127.0.0.1:5000", "127.0.0.1"),
        ("localhost", "localhost"),
        ("[::1]:5000", "[::1]"),
        ("::1", "::1"),
        ("http://evil.com", "evil.com"),
        ("http://evil.com:8080", "evil.com"),
        ("https://Evil.COM/path", "evil.com"),
    ],
)
def test_estrazione_hostname(grezzo, atteso):
    assert _hostname(grezzo) == atteso


def test_host_estraneo_rifiutato(client):
    """Difesa anti DNS-rebinding: l'header Host deve essere in allow-list."""
    r = client.get("/", headers={"Host": "attacco.example.com"})
    assert r.status_code == 403
    assert r.is_json
    assert "non consentito" in r.get_json()["error"]


@pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.1:5000", "localhost:5000"])
def test_host_locali_ammessi(client, host):
    r = client.get("/api/health", headers={"Host": host})
    assert r.status_code == 200


def test_wildcard_ammette_qualunque_host(app):
    """Con MR_RAO_HOST=0.0.0.0 l'esposizione è una scelta esplicita."""
    app.config["ALLOWED_HOSTS"] = {"*"}
    r = app.test_client().get("/api/health", headers={"Host": "server-interno.lan"})
    assert r.status_code == 200


def test_post_cross_site_rifiutata(client):
    """Il caso concreto: un sito qualunque che avvia un hotfolder."""
    r = client.post(
        "/api/watch",
        json={"inbox": "C:/tmp/in", "outbox": "C:/tmp/out"},
        headers={"Origin": "https://sito-malevolo.example"},
    )
    assert r.status_code == 403
    assert "cross-site" in r.get_json()["error"].lower()


def test_upload_cross_site_rifiutato(client):
    r = client.post(
        "/api/convert",
        data={"file": (BytesIO(b"ciao"), "a.txt")},
        content_type="multipart/form-data",
        headers={"Origin": "https://sito-malevolo.example"},
    )
    assert r.status_code == 403


def test_post_stessa_origine_ammessa(client):
    r = client.post(
        "/api/convert",
        data={"file": (BytesIO(b"ciao"), "a.txt")},
        content_type="multipart/form-data",
        headers={"Origin": "http://localhost"},
    )
    assert r.status_code == 202


def test_post_senza_origine_ammessa(client):
    """curl e la CLI non mandano Origin: non vanno bloccati."""
    r = client.post(
        "/api/convert",
        data={"file": (BytesIO(b"ciao"), "a.txt")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 202


def test_get_cross_origin_non_bloccata_dal_controllo_origin(client):
    """Le GET non cambiano stato: le protegge il controllo Host, non Origin."""
    r = client.get("/api/health", headers={"Origin": "https://altro.example"})
    assert r.status_code == 200


# --- Sec-Fetch-Site -------------------------------------------------------
# Il controllo su Origin era condizionato alla *presenza* dell'header:
# `if origin and ...`. Una navigazione da <form> cross-site può arrivare senza
# Origin, e in quel caso non scattava niente. Questi test coprono quel ramo.


def test_post_cross_site_senza_origin_rifiutata(client):
    """Il buco vero: nessun Origin, quindi prima passava indisturbata."""
    r = client.post(
        "/api/convert",
        data={"file": (BytesIO(b"ciao"), "a.txt")},
        content_type="multipart/form-data",
        headers={"Sec-Fetch-Site": "cross-site"},
    )
    assert r.status_code == 403
    assert "cross-site" in r.get_json()["error"].lower()


def test_post_da_vicino_di_porta_rifiutata(client):
    """Un altro programma su 127.0.0.1:8080 ha il *nostro* stesso hostname.

    Origin non lo distingue da noi; il browser sì, e lo chiama "same-site".
    """
    r = client.post(
        "/api/watch",
        json={"inbox": "C:/tmp/in", "outbox": "C:/tmp/out"},
        headers={"Sec-Fetch-Site": "same-site", "Origin": "http://localhost:8080"},
    )
    assert r.status_code == 403


def test_post_same_origin_ammessa(client):
    """Le richieste dell'interfaccia stessa non devono essere toccate."""
    r = client.post(
        "/api/convert",
        data={"file": (BytesIO(b"ciao"), "a.txt")},
        content_type="multipart/form-data",
        headers={"Sec-Fetch-Site": "same-origin", "Origin": "http://localhost"},
    )
    assert r.status_code == 202


def test_get_cross_site_ammessa(client):
    """Le GET restano in sola lettura: non c'è niente da proteggere qui."""
    r = client.get("/api/health", headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 200


def test_post_senza_sec_fetch_site_ricade_su_origin(client):
    """curl e la CLI non mandano Sec-Fetch-Site: il vecchio controllo resta."""
    r = client.post(
        "/api/convert",
        data={"file": (BytesIO(b"ciao"), "a.txt")},
        content_type="multipart/form-data",
        headers={"Origin": "https://sito-malevolo.example"},
    )
    assert r.status_code == 403


# --- Intestazioni ---------------------------------------------------------


@pytest.mark.parametrize(
    ("intestazione", "atteso"),
    [
        (
            "Content-Security-Policy",
            "frame-ancestors 'none'; img-src 'self' data: blob:",
        ),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
    ],
)
def test_intestazioni_di_sicurezza(client, intestazione, atteso):
    r = client.get("/api/health")
    assert r.headers.get(intestazione) == atteso


def test_la_pagina_non_puo_chiedere_immagini_fuori(client):
    """La promessa «non esce niente» non deve dipendere da un solo controllo.

    L'anteprima rende un documento altrui: il renderer non emette mai un
    `<img>` remoto, ma quella e' un'espressione regolare scritta da noi. La
    politica del browser e' la seconda serratura, e vale anche il giorno in
    cui qualcuno tocca il renderer senza accorgersene.
    """
    csp = client.get("/").headers.get("Content-Security-Policy", "")
    assert "img-src" in csp
    direttiva = [p.strip() for p in csp.split(";") if p.strip().startswith("img-src")][0]
    assert "http:" not in direttiva and "https:" not in direttiva and "*" not in direttiva


def test_intestazioni_anche_sugli_errori(client):
    """Un 403 è una risposta come le altre: non deve perderle per strada."""
    r = client.get("/", headers={"Host": "attacco.example.com"})
    assert r.status_code == 403
    assert r.headers.get("X-Content-Type-Options") == "nosniff"


# --- Allow-list quando si ascolta su 0.0.0.0 ------------------------------


def test_ascolto_esposto_non_apre_a_tutti():
    """Prima MR_RAO_HOST=0.0.0.0 metteva "*" in allow-list: la difesa anti
    DNS-rebinding spariva esattamente quando l'app si esponeva."""
    ammessi = {h.lower() for h in config._indirizzi_di_questa_macchina().split(",")}
    assert "*" not in ammessi
    assert "127.0.0.1" in ammessi
    assert "localhost" in ammessi
    assert "attacco.example.com" not in ammessi


def test_ascolto_esposto_ammette_la_macchina_stessa():
    """L'accesso legittimo in LAN passa per IP o nome macchina: quelli restano."""
    import socket

    ammessi = {h.lower() for h in config._indirizzi_di_questa_macchina().split(",")}
    assert socket.gethostname().lower() in ammessi


# --- Chiave di firma ------------------------------------------------------


def test_chiave_non_e_una_costante_pubblicata():
    """Oggi non la usa niente. Il giorno che qualcuno scrive session[...] —
    una riga, in Flask — una costante scritta in un repository pubblico
    diventerebbe la chiave con cui si firmano i cookie, e nulla si romperebbe
    per farlo notare."""
    assert config.SECRET_KEY != "mr-rao-local-dev-only"
    assert len(config.SECRET_KEY) >= 32
