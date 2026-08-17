# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Cartelle di lavoro: mai nel cloud, e nessuna scrittura da una GET."""
from pathlib import Path

import pytest

from mr_rao.user_folders import (
    app_data_dir,
    browse_folder,
    default_watch_paths,
    describe_default_folders,
    ensure_default_watch_folders,
    folders_root,
    is_cloud_synced,
    local_documents_dir,
)


@pytest.fixture()
def documenti_locali(tmp_path, monkeypatch):
    """Profilo utente finto, con Documenti NON sincronizzati."""
    docs = tmp_path / "Documents"
    docs.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    for var in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer", "Dropbox"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("MR_RAO_FOLDER_ROOT", raising=False)
    return docs


@pytest.fixture()
def documenti_in_onedrive(tmp_path, monkeypatch):
    """Il caso reale su Windows con Known Folder Move: Documenti È OneDrive."""
    od = tmp_path / "OneDrive - Azienda"
    docs = od / "Documenti"
    docs.mkdir(parents=True)
    (tmp_path / "Documents").mkdir()  # esiste ma è dentro il profilo
    monkeypatch.setenv("USERPROFILE", str(od))  # profilo redirezionato
    monkeypatch.setenv("OneDrive", str(od))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData" / "Local"))
    monkeypatch.delenv("MR_RAO_FOLDER_ROOT", raising=False)
    return od


# ---------------------------------------------------------------------------
# Riconoscimento delle cartelle sincronizzate
# ---------------------------------------------------------------------------


def test_riconosce_percorso_dentro_onedrive(tmp_path, monkeypatch):
    od = tmp_path / "OneDrive - Azienda"
    (od / "Documenti").mkdir(parents=True)
    monkeypatch.setenv("OneDrive", str(od))
    assert is_cloud_synced(od / "Documenti") is True


@pytest.mark.parametrize(
    "nome", ["OneDrive", "OneDrive - Azienda", "Dropbox", "Google Drive", "iCloud Drive"]
)
def test_riconosce_dal_nome_anche_senza_variabile(tmp_path, monkeypatch, nome):
    """Se la variabile d'ambiente non c'è, il nome della cartella basta."""
    for var in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer", "Dropbox"):
        monkeypatch.delenv(var, raising=False)
    p = tmp_path / nome / "Documenti"
    p.mkdir(parents=True)
    assert is_cloud_synced(p) is True


def test_cartella_normale_non_e_cloud(documenti_locali):
    assert is_cloud_synced(documenti_locali) is False


# ---------------------------------------------------------------------------
# Scelta della radice
# ---------------------------------------------------------------------------


def test_usa_documenti_quando_sono_locali(documenti_locali):
    assert local_documents_dir() == documenti_locali
    root, motivo = folders_root()
    assert root == documenti_locali / "Mr Rao"
    assert "locale" in motivo


def test_evita_il_cloud_e_ripiega_su_cartella_locale(documenti_in_onedrive):
    """Il punto centrale: l'app promette «zero cloud», quindi le cartelle di
    lavoro non possono finire dentro OneDrive.

    `USERPROFILE` e `Path.home()` su macOS non coincidono: un candidato in
    più su `Path.home()/Documents` prendeva i Documenti del runner e il
    test (scritto su Windows) diventava rosso senza che il prodotto
    avesse trovato una cartella locale dell'utente.
    """
    assert local_documents_dir() is None
    root, motivo = folders_root()
    assert is_cloud_synced(root) is False, f"radice ancora nel cloud: {root}"
    assert root == app_data_dir()
    assert "cloud" in motivo.lower()

    inbox, outbox = default_watch_paths()
    assert is_cloud_synced(inbox) is False
    assert is_cloud_synced(outbox) is False


def test_override_esplicito_ha_precedenza(tmp_path, monkeypatch):
    monkeypatch.setenv("MR_RAO_FOLDER_ROOT", str(tmp_path / "altrove"))
    root, motivo = folders_root()
    assert root == tmp_path / "altrove"
    assert "MR_RAO_FOLDER_ROOT" in motivo


def test_nomi_delle_cartelle(documenti_locali):
    inbox, outbox = default_watch_paths()
    assert inbox.name == "Da convertire"
    assert outbox.name == "Convertiti"
    assert inbox.parent.name == "Mr Rao"


# ---------------------------------------------------------------------------
# Creazione: solo su richiesta che modifica stato
# ---------------------------------------------------------------------------


def test_describe_non_crea_nulla(documenti_locali):
    info = describe_default_folders()
    assert info["exists"] is False
    assert not Path(info["inbox"]).exists()


def test_ensure_crea(documenti_locali):
    info = ensure_default_watch_folders()
    assert Path(info["inbox"]).is_dir()
    assert Path(info["outbox"]).is_dir()
    assert info["exists"] is True
    assert info["cloud_synced"] is False


def test_get_api_non_scrive_su_disco(client, documenti_locali):
    """Una GET dev'essere sicura: prima bastava un <img src> su una pagina
    qualsiasi per far comparire cartelle nei Documenti dell'utente."""
    r = client.get("/api/folders/defaults")
    assert r.status_code == 200
    dati = r.get_json()
    assert dati["ok"] is True
    assert not Path(dati["inbox"]).exists(), "la GET ha creato la cartella"


def test_post_api_crea(client, documenti_locali):
    r = client.post("/api/folders/defaults", json={})
    assert r.status_code == 200
    dati = r.get_json()
    assert Path(dati["inbox"]).is_dir()
    assert Path(dati["outbox"]).is_dir()


def test_post_api_rifiuta_cross_site(client, documenti_locali):
    r = client.post(
        "/api/folders/defaults",
        json={},
        headers={"Origin": "https://sito-esterno.example"},
    )
    assert r.status_code == 403
    inbox, _ = default_watch_paths()
    assert not inbox.exists()


def test_watch_get_non_crea_cartelle(client, documenti_locali):
    r = client.get("/api/watch")
    assert r.status_code == 200
    # la UI interroga questo endpoint ogni 4 secondi
    assert not Path(r.get_json()["defaults"]["inbox"]).exists()


# ---------------------------------------------------------------------------
# Selettore nativo
# ---------------------------------------------------------------------------


def test_browse_senza_ambiente_grafico_restituisce_none(monkeypatch):
    """In container/headless tkinter fallisce alla creazione della finestra,
    non all'import: va protetta anche quella."""
    import tkinter

    def esplode(*_a, **_k):
        raise tkinter.TclError("no display name and no $DISPLAY environment variable")

    monkeypatch.setattr(tkinter, "Tk", esplode)
    assert browse_folder() is None
