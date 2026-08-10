"""L'installer .exe non deve diventare la terza copia delle stesse regole.

Perche' esiste
--------------

Le confezioni sono tre -- zip portable, installer `.exe`, MSIX -- e ognuna
deve mettere gli stessi collegamenti, le stesse voci di menu contestuale e
le stesse dieci estensioni. Il modo naturale di sbagliare non e' scrivere
male una di queste liste: e' scriverla **tre volte**, e scoprire fra sei mesi
che una delle tre e' rimasta indietro.

Non e' un timore astratto. `scripts/mr_rao_shell.ps1` esiste proprio perche'
era gia' successo: il suo commento in testa racconta che quando l'elenco
delle estensioni viveva in due file separati, i due sono andati fuori
sincrono e la disinstallazione lasciava voci di menu che puntavano a un
eseguibile non piu' esistente.

Percio' l'installer non riscrive niente: chiama lo script. Questi test
tengono in piedi quella scelta, che altrimenti e' solo un commento.

Cosa NON prova
--------------

Non installa niente e non lancia `iscc`: il compilatore non c'e' su tutte le
macchine, e un test che si salta dove manca lo strumento sarebbe verde
proprio dove nessuno guarda. Legge il copione e verifica le proprieta' che
si possono leggere -- che sono anche quelle che si perdono per distrazione.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
COPIONE = RADICE / "packaging" / "mr-rao.iss"
SHELL = RADICE / "scripts" / "mr_rao_shell.ps1"


@pytest.fixture(scope="module")
def iss() -> str:
    return COPIONE.read_text(encoding="utf-8")


def estensioni_dello_script() -> list[str]:
    """Le dieci estensioni, lette dall'unico posto che le dichiara."""
    testo = SHELL.read_text(encoding="utf-8")
    blocco = re.search(r"\$Estensioni\s*=\s*@\((.*?)\)", testo, re.S)
    assert blocco, "l'elenco delle estensioni non si trova piu' in mr_rao_shell.ps1"
    return re.findall(r"'(\.[a-z0-9]+)'", blocco.group(1))


# ------------------------------------------------- la guardia della guardia


def test_ci_sono_estensioni_da_confrontare() -> None:
    """Se l'estrazione smettesse di trovarle, il test sotto passerebbe
    sempre: nessuna estensione da cercare, nessuna estensione trovata,
    verde e cieco."""
    assert len(estensioni_dello_script()) >= 10, estensioni_dello_script()


def test_il_copione_esiste_ed_e_un_copione_inno(iss: str) -> None:
    """Tutto il resto legge questo file: se un giorno fosse vuoto o
    rinominato, i test che cercano l'assenza di qualcosa la troverebbero."""
    for sezione in ("[Setup]", "[Files]", "[Run]", "[UninstallRun]"):
        assert sezione in iss, f"manca la sezione {sezione}"


# ------------------------------------------------------- niente terza copia


def test_l_installer_non_riscrive_l_elenco_delle_estensioni(iss: str) -> None:
    """La ragione per cui questo file esiste.

    Se qualcuno domani mettesse le associazioni in una sezione `[Registry]`
    del copione, l'elenco tornerebbe a vivere in due posti. Il momento in cui
    ci si accorge della divergenza, senza questo test, e' quando un utente
    dice che il tasto destro apre un programma che non c'e' piu'.
    """
    # L'estensione conta quando e' **usata come tale** -- `\.pdf\`, `".pdf"`,
    # cioe' preceduta da qualcosa che non e' una lettera -- non quando e' la
    # coda di un nome di file. Il primo giro di questo test ha bocciato il
    # copione per il `.txt` di `LEGGIMI.txt`: era il test a guardare la
    # stringa invece dell'uso, e un test che grida al lupo insegna a
    # ignorarlo esattamente come uno che tace.
    dentro = [
        e
        for e in estensioni_dello_script()
        if re.search(rf"(?<![A-Za-z0-9_-]){re.escape(e)}(?![A-Za-z0-9])", iss)
    ]
    assert not dentro, (
        f"il copione dell'installer nomina {dentro}: quelle estensioni le "
        "dichiara mr_rao_shell.ps1, e averle in due posti e' il difetto che "
        "quello script e' nato per chiudere"
    )
    assert "[Registry]" not in iss, (
        "sezione [Registry] nel copione: il menu contestuale lo scrive "
        "mr_rao_shell.ps1, non l'installer"
    )


def test_installazione_e_disinstallazione_chiamano_lo_stesso_script(iss: str) -> None:
    quante = iss.count("mr_rao_shell.ps1")
    # Tre: la copia fra i file installati, la chiamata all'installazione,
    # quella alla disinstallazione. Meno di tre vuol dire che uno dei tre
    # momenti fa qualcosa di suo.
    assert quante >= 3, f"mr_rao_shell.ps1 compare {quante} volte, attese almeno 3"
    assert "-InstallDir" in iss
    assert "-Remove" in iss, (
        "la disinstallazione non chiama -Remove: i collegamenti e le voci di "
        "menu resterebbero a puntare a un eseguibile cancellato"
    )


def test_la_disinstallazione_toglie_prima_di_cancellare(iss: str) -> None:
    """Lo script serve a se stesso: se i file sparissero prima, la voce
    [UninstallRun] chiamerebbe un file che non c'e'."""
    sezione = iss[iss.index("[UninstallRun]"):]
    assert "RunOnceId" in sezione, "senza RunOnceId Inno non esegue il passo"
    assert "mr_rao_shell.ps1" in sezione


# --------------------------------------------------- dove installa, e come


def test_installa_nel_profilo_utente_e_non_chiede_l_elevazione(iss: str) -> None:
    """La lezione della 1.20.0, applicata a una confezione diversa.

    Dentro un pacchetto MSIX la cartella d'installazione e' protetta da ACL
    e il programma moriva creando la cartella degli upload. Mettere gli
    stessi file in `Program Files` sarebbe lo stesso esperimento con un altro
    nome -- piu' l'elevazione chiesta a chi vuole solo convertire un file.
    """
    assert re.search(r"^DefaultDirName=\{localappdata\}\\MrRao\s*$", iss, re.M), (
        "la destinazione non e' %LOCALAPPDATA%\\MrRao, la stessa di "
        "'Installa Mr Rao.bat'"
    )
    assert re.search(r"^PrivilegesRequired=lowest\s*$", iss, re.M)
    assert "{pf}" not in iss and "{commonpf}" not in iss and "{autopf}" not in iss, (
        "il copione nomina Program Files"
    )


def test_la_versione_precedente_viene_rimossa_non_sovrascritta(iss: str) -> None:
    """120 MB misurati, non temuti.

    Aggiornando dalla 1.3.2 alla 1.3.3 sono rimasti sul disco 120 MB di
    librerie non piu' incluse: una copia sovrascrive cio' che trova e non
    tocca cio' che non c'e' piu'. `Installa Mr Rao.bat` rimuove la cartella
    `app` prima di copiare, e l'installer deve fare lo stesso.
    """
    assert "[InstallDelete]" in iss
    sezione = iss[iss.index("[InstallDelete]"):iss.index("[Files]")]
    assert "{app}\\app" in sezione, sezione


def test_l_identita_non_cambia_fra_le_versioni(iss: str) -> None:
    """Un AppId diverso lascerebbe due voci in «App installate», e la
    prima punterebbe a file cancellati."""
    riga = re.search(r"^AppId=\{\{([0-9A-F-]{36})\}\s*$", iss, re.M | re.I)
    assert riga, "AppId assente o non e' un GUID letterale"


# ------------------------------------- il copione e lo script si aspettano
#                                        gli stessi file


def test_i_file_richiesti_sono_quelli_che_il_copione_impacchetta() -> None:
    """Due elenchi che devono coincidere, in due file diversi.

    `make_installer.mancanti()` controlla il pacchetto **prima** di lanciare
    `iscc`, che altrimenti fallisce dopo aver compresso 400 MB con un
    messaggio che nomina un percorso temporaneo. Serve a poco se controlla
    file diversi da quelli che il copione poi cerca davvero.
    """
    import importlib.util

    percorso = RADICE / "scripts" / "make_installer.py"
    spec = importlib.util.spec_from_file_location("make_installer", percorso)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    iss = COPIONE.read_text(encoding="utf-8")
    for richiesto in modulo.RICHIESTI:
        nome = Path(richiesto).name
        assert nome in iss, (
            f"make_installer pretende {nome}, ma il copione non lo nomina: "
            "uno dei due elenchi e' rimasto indietro"
        )


def test_mancanti_sa_dire_di_no(tmp_path: Path) -> None:
    """Un controllo che non puo' fallire non e' una verifica: su una
    cartella vuota deve elencare cosa manca, non tacere."""
    import importlib.util

    percorso = RADICE / "scripts" / "make_installer.py"
    spec = importlib.util.spec_from_file_location("make_installer2", percorso)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    vuota = tmp_path / "MrRao-Portable"
    vuota.mkdir()
    fuori = modulo.mancanti(vuota)
    assert "app\\MrRao.exe" in fuori or "app/MrRao.exe" in fuori, fuori
    assert "licenses/" in fuori
    # E sul pacchetto vero, se c'e', non deve inventarsi mancanze.
    if (RADICE / "dist" / "MrRao-Portable" / "app" / "MrRao.exe").is_file():
        assert modulo.mancanti() == []
