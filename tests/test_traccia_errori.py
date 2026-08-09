"""P0.4 — una conversione fallita deve lasciare una traccia leggibile dopo.

Il difetto: dal tasto destro la finestra puo' sparire prima che si legga
qualsiasi cosa. `--attendi` (P0.1/P0.2) copre solo il caso in cui c'e'
qualcuno davanti allo schermo *e* stdin e' un terminale vero. Quando il
processo muore prima che Python parli, quando non c'e' console, o quando
l'utente e' andato via, resta un lampo e nient'altro — «shell che flasha e
sparisce = zero fiducia».

La risposta e' un file: `%LOCALAPPDATA%\\Mr Rao\\ultimo-errore.txt`.

Ma un registro, su uno strumento che promette di non far girare i dati
personali, e' esso stesso un dato: un file che elenca
`C:\\clienti\\Rossi\\cartella-clinica.pdf` racconta di chi sono i documenti
che l'utente converte. Meta' di questi test verifica che la traccia ci sia;
l'altra meta' verifica che **non contenga cio' che ha deciso di non
contenere**. La seconda meta' e' quella che vale: una promessa di privacy
senza un test che la contraddica quando viene violata e' un commento.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from mr_rao import cli

RADICE = Path(__file__).resolve().parents[1]
SCRIPT = RADICE / "scripts" / "mr_rao_shell.ps1"

# Il nome dice quello che non deve uscire: cognome, natura del documento e
# cartella del cliente. Se un giorno finisce nella traccia, questi test lo
# dicono con il testo davanti agli occhi.
NOME_PARLANTE = "cartella-clinica Rossi Mario.txt"


@pytest.fixture()
def traccia(tmp_path, monkeypatch) -> Path:
    """La traccia dirottata in una cartella temporanea.

    Senza questo, ogni esecuzione dei test sovrascriverebbe il file vero di
    chi li lancia: un test che sporca i dati dell'utente per verificarli non
    e' accettabile su un programma di questo tipo.
    """
    f = tmp_path / "traccia" / "ultimo-errore.txt"
    monkeypatch.setenv("MR_RAO_TRACCIA", str(f))
    return f


def _documento(tmp_path: Path, nome: str = NOME_PARLANTE) -> Path:
    p = tmp_path / nome
    p.write_text("Contenuto qualunque.\n" * 200, encoding="utf-8")
    return p


# --- dove va a finire, e dove NON va ---------------------------------------


def test_di_default_sta_in_localappdata_non_accanto_all_eseguibile(monkeypatch):
    """`config.WRITABLE_DIR` sarebbe il posto sbagliato.

    Nel pacchetto portable e' la cartella dell'eseguibile: da li' la traccia
    seguirebbe il programma dentro OneDrive, nei backup e nello zip passato a
    un collega. E' lo stesso ragionamento per cui `config.py` tiene la
    SECRET_KEY fuori dal disco.
    """
    import config
    from mr_rao.user_folders import app_data_dir, is_cloud_synced

    monkeypatch.delenv("MR_RAO_TRACCIA", raising=False)
    f = cli.percorso_traccia()
    assert f is not None
    assert f.parent == app_data_dir(), "la traccia deve stare nella cartella dati locale"
    assert not is_cloud_synced(f.parent), "la traccia non deve finire in una cartella sincronizzata"
    assert config.WRITABLE_DIR not in f.parents, (
        "accanto all'eseguibile la traccia entra nello zip e nei backup"
    )


def test_non_finisce_fra_i_documenti_dell_utente(monkeypatch):
    """`folders_root()` puo' essere Documenti\\Mr Rao: un file di errori in
    mezzo ai documenti sembra un documento."""
    from mr_rao.user_folders import folders_root

    monkeypatch.delenv("MR_RAO_TRACCIA", raising=False)
    f = cli.percorso_traccia()
    assert f is not None
    assert folders_root()[0] not in f.parents


@pytest.mark.parametrize("valore", ["0", "no", "off", "none", "false", "", "  "])
def test_si_puo_spegnere(monkeypatch, valore):
    """Chi non vuole nessun file su disco deve poter dire di no, e allora non
    si scrive niente: nemmeno la cartella."""
    monkeypatch.setenv("MR_RAO_TRACCIA", valore)
    assert cli.percorso_traccia() is None
    assert cli.scrivi_traccia("qualunque errore", None) is None


# --- la traccia c'e' e dice qualcosa di utile ------------------------------


def test_un_file_che_non_esiste_lascia_traccia(tmp_path, traccia, capsys):
    """Il caso piu' banale del tasto destro: il file non c'e' piu'."""
    codice = cli.main(["convert", str(tmp_path / "sparito.pdf")])
    assert codice == 1
    assert traccia.is_file(), "nessuna traccia: la finestra si chiude e non resta niente"
    testo = traccia.read_text(encoding="utf-8-sig")
    assert "non trovato" in testo.lower()


def test_la_traccia_dice_cosa_e_successo_e_quando(tmp_path, traccia, monkeypatch):
    """Utile vuol dire: quando, che tipo di file, e perche' e' andata male."""
    doc = _documento(tmp_path)
    monkeypatch.setattr(
        cli, "convert_file", lambda *a, **k: _finto_errore("Formato non riconosciuto")
    )
    assert cli.main(["convert", str(doc)]) == 1

    testo = traccia.read_text(encoding="utf-8-sig")
    assert "Formato non riconosciuto" in testo
    assert ".txt" in testo, "senza il tipo di file la traccia non aiuta a capire quale era"
    assert re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", testo), (
        "senza data e ora non si distingue l'errore di adesso da quello di tre giorni fa"
    )
    assert cli.APP_VERSION in testo, "la versione serve a chi riceve una segnalazione"


def test_il_percorso_della_traccia_viene_detto_a_chi_guarda(tmp_path, traccia, capsys):
    """Una traccia che l'utente non sa dove cercare non e' una traccia."""
    cli.main(["convert", str(tmp_path / "sparito.pdf")])
    err = capsys.readouterr().err
    assert str(traccia) in err


def test_health_dice_dove_cercare_anche_senza_errori(traccia, capsys):
    """Quando serve, la finestra si e' gia' chiusa: il percorso dev'essere
    raggiungibile a freddo, e va detto anche se il file non c'e'."""
    assert not traccia.exists()
    assert cli.main(["health"]) == 0
    uscita = capsys.readouterr().out
    assert str(traccia) in uscita
    assert "nessun errore registrato" in uscita


# --- cio' che la traccia ha deciso di NON contenere ------------------------


def test_la_traccia_non_contiene_nome_ne_percorso_del_documento(
    tmp_path, traccia, monkeypatch
):
    """Il punto delicato di tutta la voce di backlog.

    Il messaggio simula il caso peggiore e reale: un errore di sistema che si
    porta dietro il percorso completo (`[Errno 13] ... 'C:\\...'`). Se la
    ripulitura salta, questo test lo vede.
    """
    doc = _documento(tmp_path)
    motivo = f"[Errno 13] Permission denied: '{doc}' (vedi anche {doc.parent})"
    monkeypatch.setattr(cli, "convert_file", lambda *a, **k: _finto_errore(motivo))
    assert cli.main(["convert", str(doc)]) == 1

    testo = traccia.read_text(encoding="utf-8-sig")
    for vietato in (
        "Rossi",
        "Mario",
        "cartella-clinica",
        doc.name,
        doc.stem,
        str(doc),
        str(doc.parent),
        tmp_path.name,
    ):
        assert vietato not in testo, (
            f"la traccia contiene {vietato!r}: e' un metadato su chi sono i "
            f"documenti dell'utente, ed e' esattamente cio' che questo "
            f"programma esiste per non far girare\n---\n{testo}"
        )
    assert "Permission denied" in testo, "ripulire non deve voler dire non dire niente"


@pytest.mark.parametrize(
    "motivo, resta",
    [
        ("Errore di I/O sul disco", "I/O"),
        ("Il formato non e' supportato e/o e' danneggiato", "e/o"),
        ("Timeout dopo 900 secondi", "900"),
    ],
)
def test_ripulire_non_vuol_dire_rendere_illeggibile(tmp_path, traccia, monkeypatch, motivo, resta):
    """Il verso opposto del test precedente, e vale quanto quello.

    Una ripulitura troppo larga «protegge» cancellando la sola frase utile
    del file: `and/or` diventava `and<percorso>`. Un file che non dice piu'
    niente e' indistinguibile da un file che non c'e'.
    """
    doc = _documento(tmp_path, "documento.txt")
    monkeypatch.setattr(cli, "convert_file", lambda *a, **k: _finto_errore(motivo))
    assert cli.main(["convert", str(doc)]) == 1
    assert resta in traccia.read_text(encoding="utf-8-sig")


def test_la_traccia_non_contiene_il_contenuto_del_documento(tmp_path, traccia, monkeypatch):
    doc = tmp_path / "verbale.txt"
    doc.write_text("IBAN IT60X0542811101000000123456 di Mario Rossi\n", encoding="utf-8")
    monkeypatch.setattr(cli, "convert_file", lambda *a, **k: _finto_errore("Conversione fallita"))
    assert cli.main(["convert", str(doc)]) == 1
    testo = traccia.read_text(encoding="utf-8-sig")
    assert "IT60X0542811101000000123456" not in testo


def test_una_conversione_riuscita_non_lascia_niente(tmp_path, traccia):
    """La traccia registra i fallimenti, non l'attivita'. Se registrasse
    anche i successi sarebbe una cronologia delle conversioni, cioe' proprio
    l'elenco che non deve esistere."""
    doc = _documento(tmp_path, "documento.txt")
    assert cli.main(["convert", str(doc), "-o", str(tmp_path / "out.md")]) == 0
    assert not traccia.exists()


def test_e_una_riga_sola_non_una_cronologia(tmp_path, traccia, monkeypatch):
    """Tre fallimenti di seguito devono lasciare un file solo, con l'ultimo.

    Un file che cresce a ogni errore diventa in fretta l'elenco dei documenti
    che l'utente ha provato a convertire.
    """
    for n, motivo in enumerate(("Primo guasto", "Secondo guasto", "Terzo guasto")):
        doc = _documento(tmp_path, f"pratica-{n}.txt")
        monkeypatch.setattr(cli, "convert_file", lambda *a, m=motivo, **k: _finto_errore(m))
        assert cli.main(["convert", str(doc)]) == 1

    testo = traccia.read_text(encoding="utf-8-sig")
    assert "Terzo guasto" in testo
    assert "Primo guasto" not in testo and "Secondo guasto" not in testo
    assert len(list(traccia.parent.iterdir())) == 1, "un file solo, non uno per errore"


def test_dopo_sette_giorni_sparisce_da_sola(tmp_path, traccia, monkeypatch):
    """La ritenzione dev'essere limitata senza che l'utente faccia niente."""
    doc = _documento(tmp_path, "documento.txt")
    monkeypatch.setattr(cli, "convert_file", lambda *a, **k: _finto_errore("Vecchio guasto"))
    assert cli.main(["convert", str(doc)]) == 1
    assert traccia.is_file()

    vecchio = time.time() - (cli.TRACCIA_GIORNI * 86400 + 60)
    os.utime(traccia, (vecchio, vecchio))
    monkeypatch.undo()  # torna la conversione vera, che su un .txt riesce
    monkeypatch.setenv("MR_RAO_TRACCIA", str(traccia))

    assert cli.main(["convert", str(doc), "-o", str(tmp_path / "out.md")]) == 0
    assert not traccia.exists(), (
        "la traccia scaduta e' rimasta: la ritenzione dichiarata nel file "
        "stesso non e' vera"
    )


def test_una_traccia_fresca_non_viene_cancellata(tmp_path, traccia, monkeypatch):
    """Il verso opposto: se scadesse subito, il controllo di sopra passerebbe
    anche con una regola sbagliata."""
    doc = _documento(tmp_path, "documento.txt")
    monkeypatch.setattr(cli, "convert_file", lambda *a, **k: _finto_errore("Guasto di ieri"))
    assert cli.main(["convert", str(doc)]) == 1

    ieri = time.time() - 86400
    os.utime(traccia, (ieri, ieri))
    monkeypatch.undo()
    monkeypatch.setenv("MR_RAO_TRACCIA", str(traccia))

    assert cli.main(["convert", str(doc), "-o", str(tmp_path / "out.md")]) == 0
    assert traccia.is_file(), "un errore di ieri serve ancora"


# --- il file dev'essere leggibile da un umano ------------------------------


def test_e_utf8_con_bom_perche_lo_apre_il_blocco_note(tmp_path, traccia, monkeypatch):
    """I messaggi contengono accenti («è aperto in un altro programma»).

    Senza BOM il Blocco note di Windows meno recenti li mostra storpiati:
    il testo sembra guasto proprio mentre spiega un guasto.
    """
    doc = _documento(tmp_path, "documento.txt")
    monkeypatch.setattr(
        cli, "convert_file", lambda *a, **k: _finto_errore("Il file è già aperto")
    )
    cli.main(["convert", str(doc)])
    grezzo = traccia.read_bytes()
    assert grezzo.startswith(b"\xef\xbb\xbf"), "manca il BOM"
    assert "Il file è già aperto" in grezzo.decode("utf-8-sig")


def test_il_file_spiega_se_stesso(tmp_path, traccia, monkeypatch):
    """Chi lo trova per caso deve capire cos'e', quanto resta e come
    spegnerlo, senza aprire la documentazione."""
    doc = _documento(tmp_path, "documento.txt")
    monkeypatch.setattr(cli, "convert_file", lambda *a, **k: _finto_errore("Guasto"))
    cli.main(["convert", str(doc)])
    testo = traccia.read_text(encoding="utf-8-sig")
    assert "SOLO l'ultimo errore" in testo
    assert str(cli.TRACCIA_GIORNI) in testo
    assert "MR_RAO_TRACCIA=0" in testo


def test_un_disco_che_non_collabora_non_ferma_la_conversione(tmp_path, monkeypatch, capsys):
    """Non riuscire a scrivere un file di appoggio non e' un buon motivo per
    non convertire un documento — ma va detto, altrimenti l'utente cerchera'
    un file che non c'e' e concludera' che il programma mente."""
    ostacolo = tmp_path / "ostacolo"
    ostacolo.write_text("sono un file, non una cartella", encoding="utf-8")
    monkeypatch.setenv("MR_RAO_TRACCIA", str(ostacolo / "ultimo-errore.txt"))

    doc = _documento(tmp_path, "documento.txt")
    monkeypatch.setattr(cli, "convert_file", lambda *a, **k: _finto_errore("Guasto"))
    assert cli.main(["convert", str(doc)]) == 1
    err = capsys.readouterr().err
    assert "Guasto" in err
    assert "non riesco a scrivere la traccia" in err


# --- il lanciatore: la finestra non deve sparire ---------------------------


def test_il_menu_del_portable_attende_e_si_ferma_sugli_errori():
    """Il comando del tasto destro nel pacchetto portable era
    `"MrRao.exe" "%1"`: niente `--attendi` e niente pause.

    Il primo serve quando Python arriva a parlare; il secondo quando non ci
    arriva (DLL mancante, bundle non estratto, eseguibile spostato), perche'
    in quel caso nessuna cortesia scritta in Python puo' comparire.
    """
    sorgente = SCRIPT.read_text(encoding="utf-8")
    riga = next(
        (r for r in sorgente.splitlines() if "cmd /d /c" in r and "%1" in r), None
    )
    assert riga, "il comando del menu portable non passa piu' da cmd: niente pause"
    assert "convert --attendi" in riga
    assert "|| pause" in riga


def test_lo_script_resta_ascii_dopo_le_modifiche():
    """Ripetuto qui apposta: e' l'invariante piu' facile da rompere quando si
    scrive un commento in italiano dentro il .ps1, e senza BOM Windows
    PowerShell 5.1 non interpreta il file."""
    grezzo = SCRIPT.read_bytes()
    assert not grezzo.startswith(b"\xef\xbb\xbf")
    assert not [b for b in grezzo if b > 127]


@pytest.mark.skipif(sys.platform != "win32", reason="quoting di cmd.exe: solo Windows")
def test_il_quoting_del_comando_regge_percorsi_con_spazi(tmp_path):
    """La riga finisce nel registro e la esegue la shell: se il quoting e'
    sbagliato il menu contestuale non funziona affatto, e nessuno se ne
    accorge finche' non ci clicca sopra un utente.

    Al posto dell'eseguibile c'e' un .bat che riporta gli argomenti ricevuti:
    quello che conta e' come arrivano dall'altra parte.
    """
    finto = tmp_path / "Mr Rao finto.bat"
    finto.write_text(
        "@echo off\r\necho ARG1=[%1]\r\necho ARG2=[%2]\r\necho ARG3=[%3]\r\nexit /b 0\r\n",
        encoding="ascii",
    )
    doc = tmp_path / "un documento con spazi.pdf"
    doc.write_text("x", encoding="utf-8")

    modello = 'cmd /d /c ""{0}" convert --attendi "%1" || pause"'
    riga = modello.format(finto).replace("%1", str(doc))
    r = subprocess.run(riga, capture_output=True, text=True, input="", timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ARG1=[convert]" in r.stdout
    assert "ARG2=[--attendi]" in r.stdout
    assert str(doc) in r.stdout, f"il percorso e' arrivato a pezzi:\n{r.stdout}"


@pytest.mark.skipif(sys.platform != "win32", reason="quoting di cmd.exe: solo Windows")
def test_il_pause_scatta_solo_quando_qualcosa_va_storto(tmp_path):
    """Il verso giusto della misura: se `pause` comparisse sempre, ogni
    conversione riuscita chiederebbe un tasto — e si imparerebbe a premerlo
    senza leggere, che e' peggio di non fermarsi (stessa regola di
    `--attendi`)."""
    finto = tmp_path / "finto.bat"
    finto.write_text("@echo off\r\nexit /b %ESITO%\r\n", encoding="ascii")
    doc = tmp_path / "documento.pdf"
    doc.write_text("x", encoding="utf-8")
    modello = 'cmd /d /c ""{0}" convert --attendi "%1" || pause"'
    riga = modello.format(finto).replace("%1", str(doc))

    ok = subprocess.run(
        riga, capture_output=True, text=True, input="", timeout=60,
        env={**os.environ, "ESITO": "0"},
    )
    ko = subprocess.run(
        riga, capture_output=True, text=True, input="", timeout=60,
        env={**os.environ, "ESITO": "3"},
    )
    assert "premere" not in ok.stdout.lower() and "press" not in ok.stdout.lower(), (
        f"pause su una conversione riuscita:\n{ok.stdout}"
    )
    assert "premere" in ko.stdout.lower() or "press" in ko.stdout.lower(), (
        f"nessun pause su una conversione fallita:\n{ko.stdout}"
    )


# --- documentazione --------------------------------------------------------


def test_la_traccia_e_documentata():
    """Il percorso va detto: e' la meta' della funzione. Una traccia che
    esiste e non si sa dove sta non risolve niente."""
    doc = (RADICE / "docs" / "CLI.md").read_text(encoding="utf-8")
    assert "MR_RAO_TRACCIA" in doc
    assert cli.TRACCIA_NOME in doc
    assert "LOCALAPPDATA" in doc


# --- aiuti -----------------------------------------------------------------


class _FintoRisultato:
    def __init__(self, motivo: str):
        self.error = motivo
        self.markdown = ""
        self.engine_used = "none"


def _finto_errore(motivo: str) -> _FintoRisultato:
    """Un fallimento su comando, senza dipendere da come si rompe un formato.

    Legare questi test a un file .pdf malformato li renderebbe fragili: il
    giorno che la libreria impara a leggerlo, il test smetterebbe di
    verificare la traccia e nessuno se ne accorgerebbe, perche' continuerebbe
    a passare finche' la conversione fallisce per un altro motivo.
    """
    return _FintoRisultato(motivo)
