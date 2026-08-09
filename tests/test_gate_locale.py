"""I due controlli che stanno prima della CI: import reale e hook pre-commit.

`compileall` verifica la sintassi, cioe' che il file sia scritto in Python.
Non verifica che si carichi: un import circolare, un nome sparito dal modulo
da cui lo si prende, una riga a livello di modulo che solleva un'eccezione —
tutta roba che passa il compileall e rompe l'applicazione all'avvio.
`scripts/check_import.py` colma quel buco (P2.7), e l'hook opzionale lo
esegue prima che il difetto entri nella cronologia (P2.4).

Questi test guardano soprattutto che i due controlli **sappiano dire di no**:
un gate che non puo' fallire non e' un gate, e' una decorazione verde.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
SCRIPTS = RADICE / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_import  # noqa: E402

HOOK = RADICE / ".githooks" / "pre-commit"
INSTALLATORE = SCRIPTS / "install_hooks.py"


# --------------------------------------------------------------------------
# scripts/check_import.py
# --------------------------------------------------------------------------


def test_lo_script_esiste_ed_e_quello_che_lancia_la_ci():
    assert (SCRIPTS / "check_import.py").is_file()
    ci = (RADICE / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "check_import.py" in ci, "la CI non lo esegue: esisterebbe per niente"


def test_l_albero_attuale_si_importa():
    esito = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_import.py")],
        cwd=RADICE,
        capture_output=True,
        text=True,
    )
    assert esito.returncode == 0, esito.stdout + esito.stderr


def test_vede_un_modulo_che_non_si_importa(tmp_path, monkeypatch):
    """Il caso per cui esiste: sintassi valida, import rotto."""
    (tmp_path / "modulo_rotto_di_prova.py").write_text(
        "from os import questo_nome_non_esiste\n", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    guasti = check_import.controlla(["modulo_rotto_di_prova"])

    assert len(guasti) == 1
    nome, errore = guasti[0]
    assert nome == "modulo_rotto_di_prova"
    assert "ImportError" in errore


def test_un_modulo_che_esce_da_solo_e_un_guasto(tmp_path, monkeypatch):
    """Un modulo qualunque non deve terminare il processo che lo importa.

    Se `controlla` catturasse solo `Exception`, un `SystemExit` a livello di
    modulo non verrebbe segnalato: farebbe uscire il controllo stesso, con
    codice 0 se il modulo ha scritto 0. Verde per un albero rotto.
    """
    (tmp_path / "modulo_che_esce.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    guasti = check_import.controlla(["modulo_che_esce"])

    assert [n for n, _ in guasti] == ["modulo_che_esce"]


def test_l_entry_point_e_gestito_non_escluso():
    """`mr_rao/__main__.py` lancia la CLI quando lo si importa.

    E' il modulo dove vive l'import di `mr_rao.cli`, cioe' esattamente il tipo
    di riga che questo controllo esiste per sorvegliare: toglierlo dall'elenco
    sarebbe comodo e sbagliato.
    """
    assert "mr_rao.__main__" in check_import.moduli_da_controllare()
    assert "mr_rao.__main__" in check_import.ARGV_INNOCUO


def test_un_entry_point_nuovo_non_passa_inosservato(monkeypatch, capsys):
    """Senza argv innocuo, importarlo lancerebbe un programma vero in CI."""
    finti = [f"finto.modulo_{i}" for i in range(12)] + ["finto.strumento.__main__"]
    monkeypatch.setattr(check_import, "moduli_da_controllare", lambda: finti)

    assert check_import.main() == 1
    assert "senza argv innocuo" in capsys.readouterr().err


def test_una_scoperta_rotta_non_passa_per_verde(monkeypatch, capsys):
    """Se l'elenco dei moduli si svuota, tutto passerebbe a vuoto."""
    monkeypatch.setattr(check_import, "moduli_da_controllare", lambda: ["config"])

    assert check_import.main() == 1
    assert "la scoperta" in capsys.readouterr().err


def test_i_moduli_si_controllano_uno_per_uno(tmp_path, monkeypatch):
    """Il caso che giustifica lo svuotamento di `sys.modules`.

    `x` importa un nome da `y`; `y` importa il modulo `x`. Importando prima
    `x` funziona, importando prima `y` no. Se il controllo lasciasse in cache
    cio' che ha gia' importato, `x` (che viene prima in ordine alfabetico)
    metterebbe `y` in `sys.modules` gia' inizializzato e il guasto di `y`
    diventerebbe invisibile.
    """
    pacchetto = tmp_path / "pacchetto_circolare"
    pacchetto.mkdir()
    (pacchetto / "__init__.py").write_text("", encoding="utf-8")
    (pacchetto / "x.py").write_text(
        "from pacchetto_circolare.y import VALORE\n", encoding="utf-8"
    )
    (pacchetto / "y.py").write_text(
        "from pacchetto_circolare import x\nVALORE = 1\n", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    nomi = ["pacchetto_circolare.x", "pacchetto_circolare.y"]

    def svuota():
        for n in [k for k in sys.modules if k.startswith("pacchetto_circolare")]:
            del sys.modules[n]

    monkeypatch.setattr(check_import, "_svuota_moduli_del_progetto", svuota)
    con_svuotamento = check_import.controlla(nomi)

    svuota()
    monkeypatch.setattr(check_import, "_svuota_moduli_del_progetto", lambda: None)
    senza_svuotamento = check_import.controlla(nomi)
    svuota()

    assert [n for n, _ in con_svuotamento] == ["pacchetto_circolare.y"]
    assert senza_svuotamento == [], (
        "se questo elenco non e' vuoto il caso non e' piu' quello descritto, "
        "e il test non sta piu' misurando lo svuotamento"
    )


def test_controlla_rimette_sys_modules_come_l_ha_trovato():
    """Difetto vero, trovato scrivendo questi test.

    `controlla` svuota `sys.modules` per mestiere. Finche' e' uno script a
    se' non fa danno; chiamata da dentro un processo gia' avviato lasciava
    al chiamante un `mr_rao` reimportato, con oggetti-modulo diversi da
    quelli a cui il resto del programma tiene i riferimenti. Il sintomo era
    un test di conversione immagini, in un altro file, che falliva solo
    quando girava dopo questo — cioe' la causa in un posto e l'effetto in un
    altro, che e' il modo piu' caro di rompersi.
    """
    import mr_rao
    import mr_rao.privacy  # noqa: F401

    prima = {n: m for n, m in sys.modules.items() if n.split(".")[0] == "mr_rao"}
    assert prima, "senza moduli gia' importati il test non misurerebbe niente"

    check_import.controlla(check_import.moduli_da_controllare())

    sostituiti = [n for n, m in prima.items() if sys.modules.get(n) is not m]
    assert not sostituiti, f"oggetti-modulo sostituiti dal controllo: {sostituiti}"
    assert sys.modules["mr_rao"] is mr_rao


# --------------------------------------------------------------------------
# .githooks/pre-commit + scripts/install_hooks.py
# --------------------------------------------------------------------------


def test_l_hook_esiste_ed_e_uno_script_sh():
    contenuto = HOOK.read_bytes()
    assert contenuto.startswith(b"#!/bin/sh"), "senza shebang non lo esegue nessuno"


def test_l_hook_non_ha_terminazioni_windows():
    """Su Linux uno shebang con `\\r` non parte: l'errore e' `not found`,
    che indica il file e non la causa. Su Windows la sh di Git lo tollera,
    quindi chi sviluppa li' non lo vedrebbe mai e lo spedirebbe agli altri."""
    assert b"\r\n" not in HOOK.read_bytes()


def test_gitattributes_impone_lf_sugli_hook():
    """Il file giusto nell'albero di lavoro non basta: senza questa regola
    un clone con `core.autocrlf=true` — l'impostazione consigliata
    dall'installatore di Git su Windows — se lo riconverte da solo."""
    attributi = (RADICE / ".gitattributes").read_text(encoding="utf-8")
    assert ".githooks" in attributi and "eol=lf" in attributi


def test_l_hook_e_documentato_con_istruzioni_per_toglierlo():
    """Opzionale vuol dire anche reversibile, e reversibile va scritto."""
    testo = (RADICE / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "install_hooks.py --install" in testo
    assert "install_hooks.py --uninstall" in testo


def test_l_hook_non_esegue_i_controlli_lenti():
    """La scelta e' «veloce a ogni commit»: se un giorno entra pytest fuori
    da MR_RAO_HOOK_FULL, questo test lo dice invece di lasciar peggiorare il
    commit di venti secondi senza che nessuno decida."""
    testo = HOOK.read_text(encoding="utf-8")
    righe_pytest = [
        r
        for r in testo.splitlines()
        if "pytest" in r and not r.lstrip().startswith("#")
    ]
    assert len(righe_pytest) == 1
    assert "MR_RAO_HOOK_FULL" in testo


@pytest.mark.skipif(shutil.which("git") is None, reason="serve git")
def test_installazione_e_rimozione_su_un_repository_usa_e_getta(tmp_path):
    """Andata e ritorno veri, in un repository finto: la configurazione di
    chi esegue i test non si tocca."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / ".githooks").mkdir()
    shutil.copy2(INSTALLATORE, repo / "scripts" / "install_hooks.py")
    shutil.copy2(HOOK, repo / ".githooks" / "pre-commit")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    def installatore(*argomenti: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "scripts/install_hooks.py", *argomenti],
            cwd=repo,
            capture_output=True,
            text=True,
        )

    def hooks_path() -> str:
        return subprocess.run(
            ["git", "config", "--get", "core.hooksPath"],
            cwd=repo,
            capture_output=True,
            text=True,
        ).stdout.strip()

    assert hooks_path() == ""
    assert installatore("--install").returncode == 0
    assert hooks_path() == ".githooks"
    assert "INSTALLATO" in installatore("--status").stdout
    assert installatore("--uninstall").returncode == 0
    assert hooks_path() == ""


@pytest.mark.skipif(shutil.which("git") is None, reason="serve git")
def test_non_spegne_hook_gia_presenti(tmp_path):
    """`core.hooksPath` sostituisce l'intera cartella: se in .git/hooks c'e'
    un hook vero, installare lo spegnerebbe senza dirlo."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / ".githooks").mkdir()
    shutil.copy2(INSTALLATORE, repo / "scripts" / "install_hooks.py")
    shutil.copy2(HOOK, repo / ".githooks" / "pre-commit")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / ".git" / "hooks" / "commit-msg").write_text("#!/bin/sh\n", encoding="utf-8")

    esito = subprocess.run(
        [sys.executable, "scripts/install_hooks.py", "--install"],
        cwd=repo,
        capture_output=True,
        text=True,
    )

    assert esito.returncode == 1
    assert "commit-msg" in esito.stderr


@pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("sh") is None, reason="servono git e sh"
)
@pytest.mark.skipif(
    shutil.which("python") is None and shutil.which("python3") is None,
    reason="l'hook cerca un interprete sul PATH quando non c'e' il venv",
)
def test_l_hook_ferma_davvero_un_commit(tmp_path):
    """Il solo modo onesto di provare un hook: farlo girare da `git commit`.

    I controlli veri sono sostituiti da un finto che esce con il codice che
    gli diciamo: qui si misura l'impianto dell'hook — riconoscere i `.py` in
    stage, propagare l'errore, fermare il commit — non cio' che controlla.
    """
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / ".githooks").mkdir()
    (repo / "mr_rao").mkdir()
    shutil.copy2(HOOK, repo / ".githooks" / "pre-commit")
    (repo / "app.py").write_text("", encoding="utf-8")
    (repo / "config.py").write_text("", encoding="utf-8")
    (repo / "mr_rao" / "__init__.py").write_text("", encoding="utf-8")

    def git(*argomenti: str) -> subprocess.CompletedProcess:
        ambiente = {
            **os.environ,
            "GIT_AUTHOR_NAME": "prova",
            "GIT_AUTHOR_EMAIL": "prova@example.invalid",
            "GIT_COMMITTER_NAME": "prova",
            "GIT_COMMITTER_EMAIL": "prova@example.invalid",
        }
        return subprocess.run(
            ["git", *argomenti], cwd=repo, capture_output=True, text=True, env=ambiente
        )

    def finto_controllo(codice: int) -> None:
        (repo / "scripts" / "check_import.py").write_text(
            f"import sys\nsys.exit({codice})\n", encoding="utf-8"
        )

    git("init", "-q")
    git("config", "core.hooksPath", ".githooks")

    finto_controllo(1)
    (repo / "mr_rao" / "modulo.py").write_text("VALORE = 1\n", encoding="utf-8")
    git("add", "mr_rao/modulo.py")
    rifiutato = git("commit", "-m", "deve essere rifiutato")
    assert rifiutato.returncode != 0, rifiutato.stdout + rifiutato.stderr
    assert "Commit fermato" in rifiutato.stdout + rifiutato.stderr
    assert git("rev-parse", "--verify", "HEAD").returncode != 0, "non doveva nascere"

    finto_controllo(0)
    accettato = git("commit", "-m", "deve passare")
    assert accettato.returncode == 0, accettato.stdout + accettato.stderr
    assert git("rev-parse", "--verify", "HEAD").returncode == 0
