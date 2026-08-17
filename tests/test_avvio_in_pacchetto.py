# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il programma deve **aprirsi** anche dove non può scrivere.

Il difetto, e come è arrivato fin dove è arrivato
--------------------------------------------------

Un pacchetto MSIX si installa in `C:\\Program Files\\WindowsApps\\...`, che è
protetta da ACL e **non è scrivibile nemmeno da un processo elevato**. Fino
alla 1.20.0 la cartella scrivibile era sempre quella dell'eseguibile — cosa
giusta nel portable, dove è proprio ciò che lo rende portable — e
`create_app()` ci creava la cartella degli upload.

`create_app()` viene chiamata **a livello di modulo** in `app.py`, cioè
durante l'importazione. Un'eccezione lì non produce un errore gestito:
produce un processo che muore prima di stampare una riga. La certificazione
del Microsoft Store ha rimandato indietro il pacchetto con *«The product
crashes at launch»*, ed era esattamente questo.

**Perché nessun test l'aveva visto.** Tutti giravano su un albero
sorgente scrivibile, o su un portable in una cartella scrivibile. Nessuno
provava la sola condizione in cui il difetto esiste: una cartella
d'installazione di sola lettura. Il test qui sotto la costruisce.

Le due difese, e perché servono tutte e due
--------------------------------------------

1. **La causa**: `config._writable_dir()` distingue il pacchetto dal
   portable e nel primo caso scrive nel profilo dell'utente;
2. **il presidio**: qualunque cosa accada, il `mkdir` all'importazione non
   deve poter uccidere il programma. Una cartella può risultare non
   scrivibile per ragioni che non prevediamo — profilo su rete, disco
   pieno, criterio aziendale, antivirus — e in tutti quei casi la cosa
   giusta è **aprirsi comunque**: senza cartella degli upload restano rotte
   le conversioni da file, non tutto il programma.

La seconda senza la prima sarebbe un cerotto; la prima senza la seconda
lascerebbe il difetto pronto a tornare da un'altra porta.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]


# --------------------------------------------------- dove si può scrivere


def test_dentro_un_pacchetto_non_si_scrive_nella_cartella_del_programma(monkeypatch):
    """La causa vera, provata sulla funzione che la decide.

    Non si prova il `mkdir`: si prova che la cartella scelta **non sia**
    quella d'installazione. È la condizione che rende il `mkdir` possibile,
    ed è quella che va difesa — un test sul `mkdir` passerebbe anche
    scrivendo in un posto sbagliato ma per caso scrivibile.
    """
    import config

    finta = Path(r"C:\Program Files\WindowsApps\AntonioAndreaRao.Mr.Rao_1.0.0.0_x64__abc\app")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(finta / "MrRao.exe"))
    monkeypatch.setattr(sys, "platform", "win32")

    scrivibile = config._writable_dir()
    assert finta not in scrivibile.parents and scrivibile != finta, (
        f"la cartella scrivibile è dentro il pacchetto: {scrivibile}. "
        "Lì Windows nega la scrittura, e il programma muore all'avvio"
    )


def test_fuori_da_un_pacchetto_il_portable_resta_portable(monkeypatch):
    """L'altra metà, e non è un dettaglio.

    Il portable scrive accanto a sé: è ciò che permette di portarselo su
    una chiavetta con i suoi dati. Se la correzione del pacchetto avesse
    spostato **anche** i dati del portable nel profilo dell'utente, avremmo
    riparato una cosa rompendone un'altra — e in silenzio, perché nessuno
    se ne accorge finché non cerca i propri file.
    """
    import config

    cartella = Path(tempfile.gettempdir()) / "MrRaoPortatile" / "app"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(cartella / "MrRao.exe"))
    monkeypatch.setattr(sys, "platform", "win32")

    # `.resolve()` su tutt'e due i lati, e non e' pignoleria: `_exe_dir()`
    # risolve il percorso dell'eseguibile, e sui runner di GitHub la TEMP
    # arriva in forma corta 8.3 -- `C:\Users\RUNNER~1\...` diventa
    # `C:\Users\runneradmin\...`. Confrontando la forma non risolta il test
    # falliva **solo lassu'**, su due scritture della stessa cartella.
    # Resta capace di dire di no: se la cartella scrivibile finisse nel
    # profilo utente, nessuna delle due forme coinciderebbe.
    assert config._writable_dir().resolve() == cartella.resolve()


def test_gli_asset_restano_accanto_al_programma(monkeypatch):
    """`static/` e `templates/` non seguono i dati nel profilo utente.

    Erano la stessa cartella finché il programma scriveva accanto a sé.
    Da quando non lo sono più, cercare gli asset dove si scrive vorrebbe
    dire cercarli dove non ci sono mai stati: l'interfaccia si aprirebbe
    senza foglio di stile — un guasto che si vede, ma solo dopo.
    """
    import config

    assert config.EXE_DIR is not None
    if config._in_pacchetto():
        assert config.EXE_DIR != config.WRITABLE_DIR


# ---------------------------------------------- il programma si apre lo stesso


def test_create_app_non_muore_se_non_puo_creare_la_cartella(tmp_path, monkeypatch):
    """Il presidio: nessun `mkdir` all'importazione può uccidere l'avvio.

    Si punta `UPLOAD_FOLDER` a un percorso impossibile da creare — un file
    normale usato come se fosse una cartella — e si pretende che
    `create_app()` ritorni comunque un'applicazione.
    """
    import config
    from mr_rao.app_factory import create_app

    ostacolo = tmp_path / "sono-un-file"
    ostacolo.write_text("non sono una cartella", encoding="utf-8")
    monkeypatch.setattr(config, "UPLOAD_FOLDER", ostacolo / "uploads")

    app = create_app()
    assert app is not None, "il programma deve aprirsi comunque"
    assert app.config.get("UPLOAD_FOLDER_ERRORE"), (
        "un avvio che nasconde un guasto è il modo in cui il guasto arriva "
        "all'utente sotto un'altra forma: l'errore va registrato"
    )


def test_il_ripiego_e_una_cartella_scrivibile(tmp_path, monkeypatch):
    """Non basta non morire: la conversione da file deve poter funzionare."""
    import config
    from mr_rao.app_factory import create_app

    ostacolo = tmp_path / "file-non-cartella"
    ostacolo.write_text("x", encoding="utf-8")
    monkeypatch.setattr(config, "UPLOAD_FOLDER", ostacolo / "uploads")

    app = create_app()
    ripiego = Path(app.config["UPLOAD_FOLDER"])
    assert ripiego.is_dir()
    prova = ripiego / "prova-scrittura.txt"
    prova.write_text("ok", encoding="utf-8")
    prova.unlink()


# ------------------------------------------------ il giro completo, davvero


@pytest.mark.skipif(sys.platform != "win32", reason="ACL di Windows")
def test_l_avvio_regge_una_cartella_negata_dalle_acl():
    """La riproduzione fedele: cartella con la scrittura **negata**.

    I test qui sopra simulano; questo nega davvero il permesso con `icacls`
    e importa il programma in un processo separato, che è il modo in cui il
    difetto si manifestava — un'eccezione durante l'importazione, non
    dentro una funzione che qualcuno chiama.
    """
    base = Path(tempfile.mkdtemp())
    cartella = base / "WindowsApps" / "app"
    cartella.mkdir(parents=True)
    (cartella / "MrRao.exe").write_bytes(b"")
    utente = os.environ.get("USERNAME", "")
    negato = subprocess.run(
        ["icacls", str(cartella), "/deny", f"{utente}:(W)"],
        capture_output=True, text=True,
    )
    if negato.returncode != 0:
        pytest.skip(f"icacls non ha potuto negare la scrittura: {negato.stderr[:80]}")
    try:
        codice = (
            "import sys, pathlib;"
            "sys.frozen=True;"
            f"sys.executable=r'{cartella / 'MrRao.exe'}';"
            f"sys.path.insert(0, r'{RADICE}');"
            "from mr_rao import create_app;"
            "a=create_app();"
            "print('APERTO')"
        )
        r = subprocess.run(
            [sys.executable, "-c", codice],
            capture_output=True, text=True, cwd=str(RADICE), timeout=120,
        )
        assert "APERTO" in r.stdout, (
            "il programma non si è aperto con la cartella d'installazione in "
            f"sola lettura.\nstdout: {r.stdout[-400:]}\nstderr: {r.stderr[-600:]}"
        )
    finally:
        subprocess.run(
            ["icacls", str(cartella), "/remove:d", utente], capture_output=True
        )


def test_il_pacchetto_non_porta_una_cartella_upload_inutilizzabile():
    """L'altra metà della correzione, dal lato di chi confeziona.

    Nel portable `uploads/` sta accanto all'eseguibile ed è scrivibile.
    Dentro un MSIX finisce in `Program Files\\WindowsApps`, dove non si
    scrive: non è un posto dove caricare qualcosa, è un posto che **sembra**
    pronto e non lo è.

    Si prova il filtro, non la costante: `shutil.ignore_patterns` è ciò che
    decide davvero, e una costante giusta con un filtro che non la usa
    sarebbe verde e inutile.
    """
    import shutil
    import sys as _sys

    _sys.path.insert(0, str(RADICE / "scripts"))
    import make_msix

    assert "uploads" in make_msix.ESCLUSI
    filtro = shutil.ignore_patterns(*make_msix.ESCLUSI)
    ignorati = filtro("/finta/app", ["MrRao.exe", "_internal", "uploads"])
    assert "uploads" in ignorati
    assert "MrRao.exe" not in ignorati, "il filtro sta buttando via il programma"


def test_la_rilevazione_del_pacchetto_non_dice_si_a_caso():
    """Se dicesse sempre «impacchettato», il portable scriverebbe nel profilo.

    E se dicesse sempre «no», tornerebbe il crash. Qui si verifica il verso
    innocuo: su questo albero sorgente, che pacchetto non è, la risposta
    dev'essere no.
    """
    import config

    importlib.reload(config)
    assert config._in_pacchetto() is False
