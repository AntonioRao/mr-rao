from pathlib import Path

from mr_rao.user_folders import default_watch_paths, ensure_default_watch_folders


def test_ensure_default_watch_folders(tmp_path, monkeypatch):
    docs = tmp_path / "Documents"
    docs.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("OneDrive", raising=False)
    monkeypatch.delenv("OneDriveConsumer", raising=False)

    paths = ensure_default_watch_folders()
    inbox = Path(paths["inbox"])
    outbox = Path(paths["outbox"])
    assert inbox.is_dir()
    assert outbox.is_dir()
    assert inbox.name == "Da convertire"
    assert outbox.name == "Convertiti"
    assert inbox.parent.name == "Mr Rao"
    assert "Mr Rao" in paths["app_root"]


def test_default_watch_paths_names():
    inbox, outbox = default_watch_paths()
    assert inbox.name == "Da convertire"
    assert outbox.name == "Convertiti"


def test_api_folders_defaults(client):
    r = client.get("/api/folders/defaults")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert Path(data["inbox"]).is_dir()
    assert Path(data["outbox"]).is_dir()
