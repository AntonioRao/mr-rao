# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert "Mr" in data["app"] or data["app"]


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Mr" in r.data or b"Rao" in r.data
    assert b"favicon" in r.data or b"logo" in r.data


def test_convert_sync_txt(client):
    from io import BytesIO

    data = {
        "engine": "auto",
        "privacy_filter": "false",
        "include_frontmatter": "true",
        "include_tables": "false",
        "file": (BytesIO(b"Hello from API test"), "hello.txt"),
    }
    r = client.post(
        "/api/convert/sync",
        data=data,
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    body = r.get_json()
    assert "markdown" in body
    assert "Hello from API test" in body["markdown"]


def test_convert_rejects_bad_ext(client):
    from io import BytesIO

    data = {"file": (BytesIO(b"xxx"), "malware.exe")}
    r = client.post("/api/convert/sync", data=data, content_type="multipart/form-data")
    assert r.status_code == 400


def test_job_not_found(client):
    r = client.get("/api/jobs/doesnotexist")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Regressioni: il frontend fa sempre res.json(), quindi ogni errore deve essere JSON
# ---------------------------------------------------------------------------


def test_richiesta_troppo_grande_risponde_json(app):
    """Flask taglia la richiesta prima della view: senza errorhandler
    tornava HTML e il frontend moriva su res.json()."""
    from io import BytesIO

    app.config["MAX_CONTENT_LENGTH"] = 1024
    client = app.test_client()
    r = client.post(
        "/api/convert",
        data={"file": (BytesIO(b"x" * 5000), "grande.txt")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 413
    assert r.is_json, r.data[:80]
    body = r.get_json()
    assert body["max_mb"] == 0  # 1024 byte
    assert "troppo grande" in body["error"].lower()


def test_endpoint_api_inesistente_risponde_json(client):
    r = client.get("/api/non-esiste")
    assert r.status_code == 404
    assert r.is_json
    assert "error" in r.get_json()


def test_metodo_non_consentito_risponde_json(client):
    r = client.get("/api/convert")  # è POST-only
    assert r.status_code == 405
    assert r.is_json


def test_job_non_resta_appeso_se_il_worker_esplode(app, monkeypatch):
    """Senza try/except nel thread il job restava 'running' per sempre
    e la UI continuava a pollare all'infinito."""
    import time
    from io import BytesIO

    from mr_rao import routes

    def boom(*_a, **_k):
        raise RuntimeError("errore simulato nel worker")

    monkeypatch.setattr(routes, "convert_bytes", boom)

    client = app.test_client()
    r = client.post(
        "/api/convert",
        data={"file": (BytesIO(b"ciao"), "a.txt")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 202
    job_id = r.get_json()["job_id"]

    deadline = time.time() + 5
    stato = None
    while time.time() < deadline:
        stato = client.get(f"/api/jobs/{job_id}").get_json()
        if stato["status"] not in ("pending", "running"):
            break
        time.sleep(0.05)

    assert stato["status"] == "error", f"job rimasto {stato['status']}"
    assert stato["error"]


def test_sync_redige_per_default(client):
    """Nessun campo privacy_filter nella richiesta: il default è redigere."""
    from io import BytesIO

    r = client.post(
        "/api/convert/sync",
        data={"file": (BytesIO(b"scrivi a mario.rossi@example.com"), "contatti.txt")},
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    markdown = r.get_json()["markdown"]
    assert "mario.rossi@example.com" not in markdown
    # Numerato: dalla 1.20.0 e' la forma che esce davvero dall'API, e
    # pretenderla qui e' il modo di accorgersi se l'opzione smettesse di
    # arrivare fin qui.
    assert "{{EMAIL_1}}" in markdown
