"""La console su Windows: agganciarla quando serve, non aprirla sempre.

Il problema
-----------

L'eseguibile impacchettato era costruito con `console=True`, e quello vuol dire
una cosa sola: **una finestra di shell nera a ogni avvio**, anche al doppio
click, anche quando l'unica cosa che l'utente voleva era l'icona nella barra e
la pagina nel browser. Non e' un effetto collaterale, e' letteralmente cio' che
quell'opzione fa.

La correzione ovvia — `console=False` — da sola rompe la riga di comando: senza
una console allegata l'interprete impacchettato mette `sys.stdout` a `None`, e
`MrRao.exe convert file.pdf` lanciato da un terminale non stamperebbe piu'
niente. Il comando funzionerebbe e sembrerebbe non aver fatto nulla, che e' il
modo peggiore di rompersi.

La soluzione
------------

`console=False` nello spec, e la console **ci si aggancia solo quando c'e'
qualcosa da dire**:

  * doppio click senza argomenti  -> nessuna finestra, nessun aggancio;
  * lanciato da `cmd.exe` con un comando -> ci si attacca a **quella** finestra
    (`ATTACH_PARENT_PROCESS`), e l'output esce dove l'utente sta guardando;
  * file trascinato sull'icona -> nessun genitore con una console, quindi se ne
    apre una nuova. E' quello che succede anche oggi.

Perche' sta in un modulo alla radice e non dentro `mr_rao/`
-----------------------------------------------------------

Perche' `mr_rao/__init__.py` importa `config`, e l'aggancio deve avvenire
**prima** di qualunque altra cosa del progetto: un modulo che stampasse o
configurasse un handler di logging prima dell'aggancio scriverebbe nel vuoto, e
il difetto si vedrebbe solo dall'utente. Qui dentro si importano `sys` e
`ctypes`, e nient'altro.
"""
from __future__ import annotations

import sys

#: `AttachConsole` vuole questo al posto di un identificatore di processo.
ATTACH_PARENT_PROCESS = -1


def serve_console(argomenti: list[str] | None = None) -> bool:
    """Questo avvio ha qualcosa da scrivere su una console?

    La regola e' la stessa che decide se partire in modalita' riga di comando:
    **un argomento qualsiasi**. Sta qui e `app.py` la **chiama**, invece di
    riscriverla: se fossero due copie, un domani se ne cambierebbe una sola, e
    si otterrebbe o una finestra nera per un avvio che non stampa niente, o un
    comando che stampa senza console -- cioe' muto.
    """
    argomenti = sys.argv[1:] if argomenti is None else argomenti
    return bool(argomenti)


def aggancia(argomenti: list[str] | None = None) -> str:
    """Aggancia la console del genitore se serve. Dice cosa ha fatto.

    Restituisce ``"niente"``, ``"genitore"``, ``"nuova"`` oppure
    ``"fallita"``. Il valore non serve al programma: serve a **poterlo
    provare**, perche' su questa funzione un test che guardasse solo
    «non ha sollevato» non distinguerebbe il caso in cui non ha fatto nulla.

    Fuori da Windows non fa niente e lo dice: li' `sys.stdout` c'e' sempre.
    """
    if sys.platform != "win32":
        return "niente"
    if not serve_console(argomenti):
        return "niente"

    import ctypes

    kernel32 = ctypes.windll.kernel32
    esito = "genitore"
    if not kernel32.AttachConsole(ATTACH_PARENT_PROCESS):
        # Nessun genitore con una console: e' il caso del file trascinato
        # sull'icona da Explorer. Se ne apre una nuova, che e' quello che
        # succedeva anche prima.
        if not kernel32.AllocConsole():
            return "fallita"
        esito = "nuova"

    # Adesso i flussi. **E qui `CONOUT$` da solo e' sbagliato**, ed e' un
    # errore che sembra funzionare.
    #
    # `CONOUT$` scrive sulla console e **scavalca la redirezione**: con
    # `MrRao.exe health > esito.txt`, o dentro una pipe, o lanciato da uno
    # script che ne cattura l'uscita, il testo finisce sulla finestra e il file
    # resta vuoto. Provato: la prima versione di questa funzione usava solo
    # `CONOUT$` e catturando l'output arrivavano **zero righe**.
    #
    # Quindi prima si guarda se un canale standard c'e' gia' -- redirezione,
    # pipe, o la console stessa -- e in quel caso si usa quello. `CONOUT$` resta
    # il ripiego per quando non c'e' proprio niente.
    if not _collega_flussi():
        return "fallita"
    return esito


#: I tre canali standard, come li chiama `GetStdHandle`.
_STD = {"stdin": -10, "stdout": -11, "stderr": -12}
_HANDLE_NON_VALIDO = -1


def _collega_flussi() -> bool:
    import ctypes
    import msvcrt
    import os

    kernel32 = ctypes.windll.kernel32
    kernel32.GetStdHandle.restype = ctypes.c_void_p

    def _da_handle(nome: str, scrittura: bool):
        grezzo = kernel32.GetStdHandle(_STD[nome])
        if not grezzo or grezzo == ctypes.c_void_p(_HANDLE_NON_VALIDO).value:
            return None
        try:
            fd = msvcrt.open_osfhandle(grezzo, 0 if scrittura else os.O_RDONLY)
            return os.fdopen(fd, "w" if scrittura else "r",
                             buffering=1 if scrittura else -1,
                             errors="replace")
        except OSError:
            return None

    try:
        sys.stdout = (_da_handle("stdout", True)
                      or open("CONOUT$", "w", buffering=1, errors="replace"))
        sys.stderr = (_da_handle("stderr", True)
                      or open("CONOUT$", "w", buffering=1, errors="replace"))
        sys.stdin = _da_handle("stdin", False) or open("CONIN$", "r")
    except OSError:
        # Meglio muti che in crash: il comando fa comunque il suo lavoro, e il
        # codice di uscita resta l'informazione affidabile.
        return False
    return True
