"""L'integrazione col sistema operativo, finalmente sotto test (P2.3).

E' il pezzo di prodotto rimasto piu' a lungo senza rete: collegamenti,
menu contestuale e disinstallazione vivono in PowerShell, e i test Python
non potevano toccarli. Non per pigrizia — per un motivo strutturale: quello
script *scrive davvero* sul Desktop e nel registro, e un test che lo esegue
davvero sporca la macchina di chi lo lancia.

Il passaggio `-Prova` aggiunto oggi scioglie il nodo: lo script sa dire cosa
farebbe senza farlo. Da li' in poi e' verificabile come tutto il resto.

Due famiglie di controlli:

* quelli che leggono lo script come testo, e girano ovunque — anche nel
  container Linux, dove PowerShell non esiste;
* quelli che lo eseguono con `-Prova`, che hanno senso solo su Windows.

Il caso che questi test esistono per non far tornare e' scritto nel
commento in cima allo script: l'elenco delle estensioni viveva in due file,
sono andati fuori sincrono, e la disinstallazione lasciava voci di menu che
puntavano a un eseguibile non piu' esistente.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from config import ALLOWED_EXTENSIONS

RADICE = Path(__file__).resolve().parents[1]
SCRIPT = RADICE / "scripts" / "mr_rao_shell.ps1"

WINDOWS = sys.platform == "win32" and shutil.which("powershell") is not None
solo_windows = pytest.mark.skipif(
    not WINDOWS, reason="serve Windows PowerShell: lo script non e' eseguibile altrove"
)


@pytest.fixture(scope="module")
def sorgente() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def estensioni_del_menu(sorgente: str) -> list[str]:
    blocco = re.search(r"\$Estensioni = @\((.*?)\)", sorgente, re.DOTALL)
    assert blocco, "non trovo piu' l'elenco delle estensioni nello script"
    return re.findall(r"'(\.[a-z0-9]+)'", blocco.group(1))


# --- controlli sul testo: girano ovunque -----------------------------------


def test_lo_script_esiste():
    assert SCRIPT.is_file(), f"manca {SCRIPT}"


def test_ogni_estensione_del_menu_e_convertibile(sorgente):
    """«Apri con Mr. Rao» su un formato che l'app rifiuta e' una promessa
    rotta nel punto peggiore: l'utente ha gia' cliccato."""
    estensioni = estensioni_del_menu(sorgente)
    assert estensioni, "elenco vuoto: il menu non comparirebbe da nessuna parte"
    fuori = [e for e in estensioni if e not in ALLOWED_EXTENSIONS]
    assert not fuori, (
        f"il menu si offre su {fuori}, che convert_file non accetta. "
        f"Formati ammessi: {sorted(ALLOWED_EXTENSIONS)}"
    )


def test_installazione_e_disinstallazione_leggono_lo_stesso_elenco(sorgente):
    """La regressione che ha dato origine a questo file: due elenchi, uno
    per installare e uno per togliere, andati fuori sincrono."""
    for funzione in ("function Install-Shell", "function Remove-Shell"):
        inizio = sorgente.index(funzione)
        fine = sorgente.find("\nfunction ", inizio + 1)
        corpo = sorgente[inizio : fine if fine != -1 else len(sorgente)]
        assert "Get-VerbKeys" in corpo, (
            f"{funzione} non usa Get-VerbKeys: se si riscrive l'elenco a mano "
            f"le due strade tornano a divergere"
        )


def test_lo_script_resta_ascii():
    """Un .ps1 con caratteri accentati e senza BOM Windows PowerShell 5.1
    non lo interpreta correttamente. E' gia' costato una serata."""
    grezzo = SCRIPT.read_bytes()
    assert not grezzo.startswith(b"\xef\xbb\xbf"), "BOM inatteso"
    non_ascii = [b for b in grezzo if b > 127]
    assert not non_ascii, f"{len(non_ascii)} byte non-ASCII: servirebbe il BOM"


def test_i_bat_puntano_a_uno_script_che_esiste():
    """Il pacchetto e' gia' uscito una volta senza questo file: l'installa-
    zione arrivava fino ai collegamenti e non ne creava nessuno."""
    chiamanti = [
        p
        for p in RADICE.rglob("*.bat")
        if "venv" not in p.parts and "dist" not in p.parts and "build" not in p.parts
    ]
    trovati = 0
    for bat in chiamanti:
        testo = bat.read_text(encoding="utf-8", errors="replace")
        # Contare i file che *nominano* lo script non basta: il nome compare
        # anche nei commenti, e un .bat riscritto per lanciare altro
        # continuerebbe a contare. Conta solo chi lo invoca davvero.
        if not re.search(r'-File\s+"[^"]*mr_rao_shell\.ps1"', testo):
            continue
        trovati += 1
        # Solo le invocazioni, cioe' `-File "<percorso>"`. Il build cita lo
        # stesso nome come *destinazione* di una copia, e quel file non
        # esiste finche' il pacchetto non e' stato assemblato: cercare ogni
        # occorrenza del nome faceva fallire il test su una riga corretta.
        #
        # Del percorso si controlla il nome finale, non la stringa intera:
        # nei .bat i percorsi si compongono con variabili (`%~dp0`, `%RADICE%`,
        # `%INSTALL_DIR%`) che qui non si possono risolvere davvero. La prima
        # versione ci provava e falliva su un percorso corretto.
        for m in re.finditer(r'-File\s+"([^"]*mr_rao_shell\.ps1)"', testo):
            # Via le variabili del .bat (%~dp0, %RADICE%, %INSTALL_DIR%) prima
            # di prendere il nome finale: senza separatore dopo la variabile,
            # `Path(...).name` restituirebbe "%~dp0mr_rao_shell.ps1".
            pulito = re.sub(r"%[^%]*%|%~dp0", "", m.group(1))
            nome = Path(pulito.replace("\\", "/")).name
            assert list(RADICE.rglob(nome)), (
                f"{bat.name} invoca {nome}, che non esiste da nessuna parte "
                f"nel repository"
            )
    assert trovati >= 2, "mi aspetto almeno l'installazione da sorgente e quella portable"


def test_nessun_argomento_finisce_con_una_barra_dentro_le_virgolette():
    """La trappola che ha fatto fallire davvero l'installazione.

    `%~dp0` termina con una barra rovescia. Per il parser della riga di
    comando di Windows la sequenza `\\"` e' una virgoletta **protetta**, non
    la chiusura della stringa: scrivendo `-InstallDir "%~dp0"` l'intera riga
    collassa e il programma chiamato riceve gli argomenti a pezzi.

    Misurato sul caso vero: `-Avvio` arrivava valorizzato `Mr`, il file non
    esisteva, e lo script usciva in errore **senza creare niente**. Non se n'e'
    accorto nessun test, perche' guardavo se il percorso esistesse invece di
    guardare come veniva passato.

    Il rimedio nel .bat e' mettere la radice in una variabile e toglierle la
    barra finale prima di usarla.

    Vale **solo per le righe che invocano powershell**: `xcopy "%OUT%\\app\\"`
    e' corretto — li' la barra finale dice «e' una cartella» e xcopy non usa
    quelle regole di quoting. Un controllo su tutte le righe segnalava sei
    punti giusti e uno sbagliato, cioe' era rumore.
    """
    colpevoli = []
    for bat in RADICE.rglob("*.bat"):
        if {"venv", "dist", "build"} & set(bat.parts):
            continue
        for n, riga in enumerate(
            bat.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            if riga.lstrip().upper().startswith(("REM ", "::")):
                continue
            if "powershell" not in riga.lower():
                continue
            for m in re.finditer(r'"[^"]*\\"', riga):
                colpevoli.append(f"{bat.name}:{n}  {m.group(0)}")
    assert not colpevoli, (
        "argomenti che finiscono con una barra dentro le virgolette — la "
        "riga di comando collassa:\n  " + "\n  ".join(colpevoli)
    )


def test_il_readme_non_promette_un_numero_sbagliato(sorgente):
    """Il README diceva «undici tipi di file». Le estensioni sono dieci:
    l'undici era il numero di chiavi di registro, che include quella per
    *tutti* i file — un dettaglio interno diventato una promessa."""
    quante = len(estensioni_del_menu(sorgente))
    for nome in ("README.it.md", "README.md"):
        testo = (RADICE / nome).read_text(encoding="utf-8")
        assert "undici tipi di file" not in testo
        assert "eleven file types" not in testo
    assert quante == 10, (
        f"le estensioni sono {quante}: aggiorna anche i due README, che "
        f"dicono «dieci formati»"
    )


# --- controlli che eseguono lo script: solo Windows ------------------------


def _prova(*argomenti: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            *argomenti,
            "-Prova",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )


@solo_windows
def test_layout_pacchetto_risolve_tutto_sull_eseguibile(tmp_path):
    """Senza i parametri nuovi lo script deve comportarsi come prima:
    collegamento, menu e icona tutti sull'eseguibile."""
    finto = tmp_path / "app"
    finto.mkdir()
    (finto / "MrRao.exe").write_bytes(b"finto")

    r = _prova("-InstallDir", str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    for riga in ("avvio:", "apri:", "icona:"):
        assert str(finto / "MrRao.exe") in r.stdout, f"{riga} non punta all'eseguibile"
    assert "11 voci di menu" in r.stdout.replace("avrei scritto ", "")


@solo_windows
def test_layout_da_sorgente_usa_tre_bersagli_diversi(tmp_path):
    """Da sorgente non c'e' un eseguibile: il collegamento va al .bat di
    avvio, il menu a quello che accetta un file, l'icona al .ico."""
    avvio = tmp_path / "Avvia Mr Rao.bat"
    apri = tmp_path / "open_with.bat"
    icona = tmp_path / "mr-rao.ico"
    for f in (avvio, apri, icona):
        f.write_bytes(b"finto")

    r = _prova(
        "-InstallDir", str(tmp_path),
        "-Avvio", str(avvio),
        "-ApriCon", str(apri),
        "-Icona", str(icona),
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"avvio:  {avvio}" in r.stdout
    assert f"apri:   {apri}" in r.stdout
    assert f"icona:  {icona}" in r.stdout
    # Il menu deve lanciare il .bat che accetta un argomento, non il .lnk.
    assert f'"{apri}" "%1"' in r.stdout


@solo_windows
def test_la_prova_non_scrive_niente(tmp_path):
    """Se `-Prova` scrivesse davvero, questi test sporcherebbero il registro
    e il Desktop di chi li lancia — e nessuno se ne accorgerebbe subito."""
    finto = tmp_path / "app"
    finto.mkdir()
    (finto / "MrRao.exe").write_bytes(b"finto")
    prima = sorted(p.name for p in tmp_path.rglob("*"))

    r = _prova("-InstallDir", str(tmp_path))
    assert "nessun collegamento creato" in r.stdout
    assert sorted(p.name for p in tmp_path.rglob("*")) == prima


@solo_windows
def test_bersaglio_mancante_ferma_tutto(tmp_path):
    """Meglio uscire con un errore che creare un collegamento a un file che
    non c'e': quello si scopre cliccandoci sopra, giorni dopo."""
    r = _prova("-InstallDir", str(tmp_path))
    assert r.returncode == 1
    assert "manca" in r.stdout.lower()
