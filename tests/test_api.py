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
