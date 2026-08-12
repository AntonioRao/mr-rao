"""La scorciatoia da tastiera che redige gli appunti sul posto.

Copi il testo, premi la combinazione, incolli: quello che arriva e' gia'
redatto. Gli appunti **sono** il posto -- niente da aprire, caricare o
scaricare. Serve a togliere l'attrito che e' il vero motivo per cui un
documento finisce dentro una chat senza passare da qui.

Guida per chi usa il programma: `docs/SCORCIATOIA-APPUNTI.md`.

Perche' questo file e' diviso in tre strati
-------------------------------------------

Il pezzo che decide -- cosa succede al testo, cosa dice la notifica, cosa si
tiene per il ripristino -- non deve dipendere da Windows, altrimenti l'unico
modo di provarlo sarebbe premere i tasti a mano su questa macchina, che non
e' una prova ripetibile e non gira in CI.

Quindi:

* `redigi()` e `passa_dagli_appunti()` sono **puri**: ricevono le funzioni
  di lettura e scrittura dall'esterno. Sono quelli sotto test;
* `leggi_appunti()` / `scrivi_appunti()` parlano con Windows;
* `avvia_scorciatoia()` registra la combinazione e gira in un thread suo.

Perche' `RegisterHotKey` e non un gancio di tastiera
----------------------------------------------------

Windows offre due meccanismi, e la scelta fra i due e' l'intera differenza
fra questa funzione e un keylogger.

`SetWindowsHookEx(WH_KEYBOARD_LL)` consegna al programma **ogni tasto**
premuto sulla macchina. E' comodo (permette combinazioni arbitrarie, sequenze,
doppie pressioni) ed e' il meccanismo con cui si scrive un keylogger.
**Qui non si usa, e non si deve usare.**

`RegisterHotKey` dichiara al sistema **una sola combinazione**; e' Windows a
sorvegliarla, e recapita `WM_HOTKEY` soltanto quando quella viene premuta.
Gli altri tasti al programma non arrivano: non e' che li ignora, non li
riceve. E' una proprieta' del sistema operativo, non una promessa nostra, ed
e' verificabile leggendo queste righe.

Costa qualcosa: le combinazioni possibili sono meno, e se un altro programma
ha gia' preso quella scelta la registrazione fallisce. Fallisce **dicendolo**,
che e' meglio di una scorciatoia che non risponde e non si sa perche'.

Gli appunti, allo stesso modo, non vengono sorvegliati: nessun controllo
periodico del contenuto. Si aprono quando la combinazione scatta, si leggono
una volta, si riscrivono una volta e si richiudono.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter

# Modificatori di RegisterHotKey (WinUser.h).
_MOD = {"alt": 0x0001, "ctrl": 0x0002, "control": 0x0002,
        "shift": 0x0004, "win": 0x0008}
# Senza questo, tenere premuto ripete la scorciatoia decine di volte al
# secondo: la prima passata redige, le successive lavorano sul gia' redatto.
_MOD_NOREPEAT = 0x4000

_WM_HOTKEY = 0x0312
_CF_UNICODETEXT = 13
_GMEM_MOVEABLE = 0x0002


@dataclass
class Esito:
    """Cosa e' successo, in una forma che la notifica sa raccontare."""

    testo: str = ""
    redazioni: int = 0
    sospetti: int = 0
    cambiato: bool = False
    errore: str = ""

    def messaggio(self) -> str:
        if self.errore:
            return self.errore
        if not self.cambiato and not self.sospetti:
            return "Nessun dato personale trovato: gli appunti restano quelli."
        pezzi = [f"{self.redazioni} dat{'o' if self.redazioni == 1 else 'i'} redatt"
                 f"{'o' if self.redazioni == 1 else 'i'}"]
        if self.sospetti:
            # I sospetti NON sono stati tolti, ed e' la meta' del messaggio
            # che conta: chi incolla senza leggere incolla un dato ancora li'.
            pezzi.append(f"{self.sospetti} da controllare — non tolt"
                         f"{'o' if self.sospetti == 1 else 'i'}")
        return " · ".join(pezzi)


@dataclass
class Memoria:
    """L'originale, per il ripristino.

    **In memoria e mai su disco.** Sovrascrivere gli appunti distrugge
    l'originale, e senza una via di ritorno il primo caso in cui la redazione
    toglie qualcosa che serviva fa perdere il testo. Ma un file di ripristino
    sarebbe un file con dentro i dati personali in chiaro, cioe' esattamente
    cio' che questo programma esiste per non fare: vive nel processo e muore
    con lui.
    """

    originale: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def ricorda(self, testo: str) -> None:
        with self._lock:
            self.originale = testo

    def riprendi(self) -> str | None:
        with self._lock:
            return self.originale

    def dimentica(self) -> None:
        with self._lock:
            self.originale = None


def redigi(testo: str, opzioni: PrivacyOptions | None = None) -> Esito:
    """Lo stesso motore della conversione dei file, sullo stesso testo.

    Non c'e' una seconda implementazione: se ce ne fosse una, prima o poi
    divergerebbe, e in un motore di redazione una divergenza e' una fuga che
    non si vede.
    """
    if not testo or not testo.strip():
        return Esito(errore="Negli appunti non c'e' testo.")
    fuori, rapporto = apply_privacy_filter(testo, opzioni or PrivacyOptions())
    return Esito(
        testo=fuori,
        redazioni=sum(rapporto.counts.values()),
        sospetti=len(rapporto.suspects),
        cambiato=fuori != testo,
    )


def passa_dagli_appunti(
    leggi: Callable[[], str | None],
    scrivi: Callable[[str], None],
    opzioni: PrivacyOptions | None = None,
    memoria: Memoria | None = None,
) -> Esito:
    """Legge, redige, riscrive. Le due funzioni arrivano da fuori apposta.

    Se il testo non cambia **non si riscrive niente**: riscrivere appunti
    identici li toglierebbe comunque all'applicazione che li possiede (il
    formato ricco, l'immagine affiancata) senza nessun guadagno.
    """
    try:
        testo = leggi()
    except Exception as e:  # la clipboard puo' essere occupata da un altro
        return Esito(errore=f"Appunti non leggibili: {e}")

    if testo is None:
        return Esito(errore="Negli appunti non c'e' testo.")

    esito = redigi(testo, opzioni)
    if esito.errore or not esito.cambiato:
        return esito

    try:
        scrivi(esito.testo)
    except Exception as e:
        return Esito(errore=f"Appunti non scrivibili: {e}")

    if memoria is not None:
        memoria.ricorda(testo)
    return esito


def ripristina(
    scrivi: Callable[[str], None], memoria: Memoria
) -> Esito:
    """Rimette negli appunti l'originale tenuto in memoria."""
    originale = memoria.riprendi()
    if originale is None:
        return Esito(errore="Nessun originale da ripristinare.")
    try:
        scrivi(originale)
    except Exception as e:
        return Esito(errore=f"Appunti non scrivibili: {e}")
    return Esito(testo=originale, cambiato=True)


# ---------------------------------------------------------------------------
# La combinazione
# ---------------------------------------------------------------------------

def analizza_combinazione(testo: str) -> tuple[int, int, str]:
    """«ctrl+alt+r» -> (modificatori, codice del tasto, forma leggibile).

    Solleva ``ValueError`` con un messaggio comprensibile: una combinazione
    scritta male deve fermare l'avvio della scorciatoia dicendolo, non
    registrarne una diversa da quella che l'utente credeva.
    """
    pezzi = [p.strip().lower() for p in testo.split("+") if p.strip()]
    if not pezzi:
        raise ValueError("combinazione vuota")
    modificatori = 0
    tasto = None
    for p in pezzi:
        if p in _MOD:
            modificatori |= _MOD[p]
        elif tasto is None:
            tasto = p
        else:
            raise ValueError(f"due tasti nella stessa combinazione: {tasto!r} e {p!r}")
    if tasto is None:
        raise ValueError("manca il tasto: servono modificatori piu' un tasto")
    if not modificatori:
        raise ValueError(
            "serve almeno un modificatore (ctrl, alt, shift, win): una "
            "scorciatoia con il solo tasto scatterebbe mentre si scrive"
        )
    if len(tasto) == 1 and (tasto.isalpha() or tasto.isdigit()):
        codice = ord(tasto.upper())
    elif tasto.startswith("f") and tasto[1:].isdigit() and 1 <= int(tasto[1:]) <= 24:
        codice = 0x70 + int(tasto[1:]) - 1  # VK_F1 = 0x70
    else:
        raise ValueError(f"tasto non riconosciuto: {tasto!r} (lettere, cifre o F1-F24)")

    nomi = [n for n, v in (("Ctrl", 0x0002), ("Alt", 0x0001),
                           ("Shift", 0x0004), ("Win", 0x0008)) if modificatori & v]
    return modificatori | _MOD_NOREPEAT, codice, "+".join(nomi + [tasto.upper()])


# ---------------------------------------------------------------------------
# Windows: appunti e scorciatoia
# ---------------------------------------------------------------------------

def _user32_kernel32():
    """Le firme vanno **dichiarate**, non lasciate indovinare a ctypes.

    Senza `restype`, ctypes assume che una funzione torni un `int` a 32 bit.
    `GetClipboardData` torna un HANDLE, che su Windows a 64 bit e' un
    puntatore a 64: il valore arrivava **troncato**, `GlobalLock` su
    quell'handle mozzato falliva, e la lettura tornava `None`.

    E' successo davvero, ed e' istruttivo per come si e' presentato:
    ventuno test verdi e la funzione che non funzionava. I test coprono lo
    strato che decide, dove le funzioni di lettura e scrittura arrivano da
    fuori -- e quello e' giusto -- ma non potevano dire niente su questo,
    perche' qui non c'e' niente da decidere: c'e' da parlare con il sistema
    operativo nel modo esatto. L'ha trovato una prova dal vivo sugli appunti
    veri, ed e' il motivo per cui adesso ce n'e' una anche fra i test.
    """
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE

    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL
    return ctypes, user32, kernel32


def _apri_appunti(ctypes, user32, tentativi: int = 10):
    """La clipboard e' una risorsa a proprietario unico: se un altro programma
    la sta usando, `OpenClipboard` fallisce. Si riprova un attimo invece di
    dichiarare un errore che sparirebbe da solo."""
    import time

    for _ in range(tentativi):
        if user32.OpenClipboard(None):
            return True
        time.sleep(0.02)
    raise OSError("gli appunti sono occupati da un altro programma")


def leggi_appunti() -> str | None:
    """Solo testo Unicode. Se dentro c'e' altro -- un file, un'immagine --
    questa funzione dice di no invece di inventarsi una conversione."""
    ctypes, user32, kernel32 = _user32_kernel32()
    _apri_appunti(ctypes, user32)
    try:
        if not user32.IsClipboardFormatAvailable(_CF_UNICODETEXT):
            return None
        handle = user32.GetClipboardData(_CF_UNICODETEXT)
        if not handle:
            return None
        puntatore = kernel32.GlobalLock(handle)
        if not puntatore:
            return None
        try:
            return ctypes.c_wchar_p(puntatore).value
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def scrivi_appunti(testo: str) -> None:
    ctypes, user32, kernel32 = _user32_kernel32()
    dati = testo + "\0"
    byte = len(dati) * ctypes.sizeof(ctypes.c_wchar)
    _apri_appunti(ctypes, user32)
    try:
        user32.EmptyClipboard()
        blocco = kernel32.GlobalAlloc(_GMEM_MOVEABLE, byte)
        if not blocco:
            raise OSError("memoria non allocata per gli appunti")
        puntatore = kernel32.GlobalLock(blocco)
        if not puntatore:
            kernel32.GlobalFree(blocco)
            raise OSError("memoria non bloccata per gli appunti")
        ctypes.memmove(puntatore, ctypes.c_wchar_p(dati), byte)
        kernel32.GlobalUnlock(blocco)
        # Riuscendo, il blocco passa **al sistema** e non va liberato da noi.
        # Fallendo resta nostro, e senza questa GlobalFree sarebbe una perdita
        # di memoria con dentro il testo in chiaro.
        if not user32.SetClipboardData(_CF_UNICODETEXT, blocco):
            kernel32.GlobalFree(blocco)
            raise OSError("gli appunti hanno rifiutato il testo")
    finally:
        user32.CloseClipboard()


def avvia_scorciatoia(
    combinazione: str,
    quando_scatta: Callable[[], None],
    quando_fallisce: Callable[[str], None] | None = None,
) -> threading.Thread | None:
    """Registra la combinazione e resta in ascolto in un thread suo.

    `RegisterHotKey` consegna `WM_HOTKEY` **alla coda del thread che ha
    registrato**, quindi il ciclo dei messaggi deve stare qui dentro e non
    altrove: e' il motivo per cui questa funzione ha un thread proprio invece
    di appoggiarsi a quello del tray.
    """
    import sys

    if sys.platform != "win32":
        if quando_fallisce:
            quando_fallisce("la scorciatoia appunti esiste solo su Windows")
        return None
    try:
        modificatori, codice, leggibile = analizza_combinazione(combinazione)
    except ValueError as e:
        if quando_fallisce:
            quando_fallisce(f"combinazione «{combinazione}» non valida: {e}")
        return None

    def ciclo() -> None:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        if not user32.RegisterHotKey(None, 1, modificatori, codice):
            if quando_fallisce:
                quando_fallisce(
                    f"la combinazione {leggibile} e' gia' presa da un altro "
                    f"programma: la scorciatoia resta spenta"
                )
            return
        messaggio = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(messaggio), None, 0, 0) > 0:
                if messaggio.message == _WM_HOTKEY:
                    try:
                        quando_scatta()
                    except Exception as e:  # un errore non deve zittire la scorciatoia
                        if quando_fallisce:
                            quando_fallisce(str(e))
        finally:
            user32.UnregisterHotKey(None, 1)

    t = threading.Thread(target=ciclo, daemon=True, name="mr-rao-scorciatoia")
    t.start()
    return t
