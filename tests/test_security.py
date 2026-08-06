"""Regressioni sulle difese del server locale.

Un server in ascolto su 127.0.0.1 è raggiungibile da qualunque pagina aperta
nel browser dell'utente. Due attacchi distinti, due controlli distinti:
- DNS rebinding: un dominio dell'attaccante che risolve a 127.0.0.1 leggeva
  le risposte → si blocca fissando l'header Host.
- CSRF: una POST cross-site (multipart è CORS-safelisted, quindi niente
  preflight) poteva avviare un hotfolder → si blocca rifiutando Origin esterne.
"""
from io import BytesIO

import pytest

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
