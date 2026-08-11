"""La finestra nera: che non compaia, e che la riga di comando resti viva.

Le due cose vanno insieme
-------------------------

L'eseguibile si costruisce **senza console**, cosi' al doppio click non compare
nessuna shell: prima ne compariva una a ogni avvio, anche quando l'utente
voleva solo l'icona nella barra.

Da sola quella scelta romperebbe la riga di comando. Senza console allegata
l'interprete impacchettato mette `sys.stdout` a `None`, e
`MrRao.exe convert file.pdf` lanciato da un terminale funzionerebbe **senza
stampare niente**: il modo peggiore di rompersi, perche' sembra che non abbia
fatto nulla. Per questo `app.py` aggancia la console del genitore quando ci
sono argomenti, e lo fa **come prima riga**.

Questi test tengono insieme i due pezzi. Separarli, o cambiarne uno solo, e' la
modifica che sembra innocua e lascia la CLI muta.

Dove sta la verita' del flag
----------------------------

**Non in `MrRao.spec`**, che non e' tracciato e viene rigenerato da PyInstaller
a ogni build: correggerlo li' sembra risolvere e non cambia niente. Il punto
unico e' il flag nella riga di comando di `scripts/build_portable.bat`, che e'
anche cio' che lancia la CI — ed e' quello che questi test guardano.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import console_win

RADICE = Path(__file__).resolve().parents[1]


# ------------------------------------------------- il flag, dove conta davvero


def test_il_build_non_chiede_la_console() -> None:
    testo = (RADICE / "scripts" / "build_portable.bat").read_text(
        encoding="utf-8", errors="replace")
    riga = [r for r in testo.splitlines()
            if r.strip().startswith("pyinstaller ")]
    assert riga, "la riga di pyinstaller non c'e' piu': questo test non guarda piu' niente"
    comando = riga[0]
    assert "--noconsole" in comando, comando
    assert "--console" not in comando.replace("--noconsole", ""), comando


def test_app_aggancia_la_console_prima_di_tutto() -> None:
    """L'ordine e' il comportamento.

    Se `console_win.aggancia()` finisse dopo `import config`, o dopo la
    creazione dell'applicazione, le righe stampate prima di quel punto
    andrebbero nel vuoto — e si vedrebbe solo dall'utente, non da qui.
    """
    righe = (RADICE / "app.py").read_text(encoding="utf-8").splitlines()
    codice = [(i, r.strip()) for i, r in enumerate(righe)
              if r.strip() and not r.strip().startswith("#")]
    # Si salta il docstring del modulo e il `from __future__`.
    dopo_future = [x for x in codice if not x[1].startswith(('"""', "'''"))]
    numero_aggancio = next(
        i for i, r in dopo_future if r.startswith("console_win.aggancia("))
    for parola in ("import config", "from mr_rao import", "app = create_app("):
        numero = next((i for i, r in dopo_future if r.startswith(parola)), None)
        assert numero is not None, parola
        assert numero > numero_aggancio, (
            f"«{parola}» sta prima dell'aggancio della console")


# ------------------------------------------------------ quando serve, e quando no


@pytest.mark.parametrize(
    ("argomenti", "atteso"),
    [
        ([], False),                      # doppio click: nessuna finestra
        (["convert", "a.pdf"], True),     # comando da terminale
        (["watch"], True),
        (["health"], True),
        (["--help"], True),
        (["C:/documenti/a.pdf"], True),   # file trascinato sull'icona
    ],
)
def test_quando_serve_una_console(argomenti: list[str], atteso: bool) -> None:
    assert console_win.serve_console(argomenti) is atteso


def test_senza_argomenti_non_tocca_niente() -> None:
    """La riga che protegge l'avvio normale.

    Se `aggancia()` facesse qualcosa anche a mani vuote, il doppio click
    tornerebbe ad aprire una finestra — cioe' esattamente il difetto che tutto
    questo esiste per togliere.
    """
    prima = (sys.stdout, sys.stderr, sys.stdin)
    assert console_win.aggancia([]) == "niente"
    assert (sys.stdout, sys.stderr, sys.stdin) == prima


@pytest.mark.skipif(sys.platform == "win32", reason="qui la console esiste")
def test_fuori_da_windows_non_fa_niente() -> None:
    assert console_win.aggancia(["convert", "a.pdf"]) == "niente"


@pytest.mark.skipif(sys.platform != "win32", reason="serve un eseguibile GUI Windows")
def test_l_output_sopravvive_alla_redirezione() -> None:
    """**La trappola vera, e l'unico test che la vede.**

    La soluzione ovvia — agganciare la console e riaprire `CONOUT$` — sembra
    funzionare e rompe tutto quello che *cattura* l'output: `CONOUT$` scrive
    sulla finestra della console e **scavalca la redirezione**. Con quella
    versione, `MrRao.exe health > esito.txt` lasciava il file **vuoto**, e lo
    stesso valeva per ogni pipe e per lo script che verifica il pacchetto.

    Misurato, non supposto: con il solo `CONOUT$` questa prova cattura zero
    byte; leggendo prima il canale standard ne cattura venticinque.

    Gira su `pythonw.exe`, che ha lo stesso sottosistema GUI dell'eseguibile
    impacchettato e la stessa assenza di console: e' il modo di provarlo senza
    costruire il pacchetto a ogni giro.
    """
    import subprocess

    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        pytest.skip("pythonw.exe non presente in questo ambiente")

    codice = (
        "import sys; sys.path.insert(0, r'" + str(RADICE) + "');"
        "import console_win; console_win.aggancia(['health']);"
        "print('SOPRAVVISSUTO')"
    )
    esito = subprocess.run([str(pythonw), "-c", codice],
                           capture_output=True, timeout=60)
    uscita = (esito.stdout or b"") + (esito.stderr or b"")
    assert b"SOPRAVVISSUTO" in uscita, (
        "l'output non e' arrivato a chi lo cattura: probabile ritorno a "
        f"CONOUT$ senza guardare il canale standard. Catturati {len(uscita)} byte"
    )


def test_la_costante_e_quella_giusta() -> None:
    """`-1` e' `ATTACH_PARENT_PROCESS`. Con qualunque altro valore
    `AttachConsole` cercherebbe un processo con quel numero e fallirebbe, e il
    ripiego aprirebbe **sempre** una finestra nuova: la CLI funzionerebbe, ma
    l'output uscirebbe in una finestra che sparisce invece che in quella dove
    l'utente sta guardando."""
    assert console_win.ATTACH_PARENT_PROCESS == -1
