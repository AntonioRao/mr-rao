"""L'anello che i ventidue test della scorciatoia non toccavano.

`tests/test_scorciatoia_appunti.py` prova lo strato che **decide** (lettura e
scrittura iniettate) e lo strato che parla con gli **appunti** di Windows.
Restava fuori quello in mezzo: `avvia_scorciatoia` — la registrazione della
combinazione presso il sistema, il ciclo dei messaggi, il richiamo. Nessun
test lo eseguiva, e non l'aveva mai eseguito nemmeno una prova a mano: la
funzione e' stata spedita nella 1.18.0 senza che nessuno avesse mai premuto
quei tasti.

Qui la combinazione si registra per davvero e si preme per davvero, con
`SendInput`.

**Il banco ha mentito la prima volta, ed e' istruttivo come.** La struttura
`INPUT` a 64 bit va dimensionata sull'unione piu' grande (`MOUSEINPUT`, 40
byte in totale) e `dwExtraInfo` e' un `ULONG_PTR`, non un puntatore. La
prima versione ne dichiarava 32: `SendInput` non inseriva niente e tornava
`0`, il valore di ritorno non veniva controllato, e il banco concludeva «la
combinazione non scatta». Un controllo che diceva sempre di no — l'altra
faccia di quello che non puo' fallire, e altrettanto inutile.

Per questo il valore di ritorno di `SendInput` adesso e' un'asserzione, e
`sizeof(INPUT)` pure: se il banco non sa premere i tasti deve dirlo, invece
di accusare il prodotto.
"""
from __future__ import annotations

import ctypes
import sys
import time

import pytest

if sys.platform != "win32":  # pragma: no cover
    pytest.skip("la scorciatoia e' Windows", allow_module_level=True)

from ctypes import wintypes  # noqa: E402

from mr_rao import appunti as A  # noqa: E402

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong
VK_CONTROL, VK_MENU, VK_R = 0x11, 0x12, 0x52
KEYEVENTF_KEYUP = 0x0002


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)]


class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
_user32.SendInput.restype = wintypes.UINT


def test_il_banco_sa_premere_i_tasti():
    """La controprova, prima del test vero.

    Con una `INPUT` mal dimensionata `SendInput` torna 0 e non inserisce
    niente: senza questa asserzione il test sotto direbbe «non scatta»
    qualunque cosa faccia il prodotto.
    """
    atteso = 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28
    assert ctypes.sizeof(INPUT) == atteso, (
        f"sizeof(INPUT) = {ctypes.sizeof(INPUT)}, atteso {atteso}: "
        "l'unione va dimensionata su MOUSEINPUT"
    )


def _premi(vk: int, su: bool = False) -> None:
    i = INPUT(type=1)
    i.ki = KEYBDINPUT(wVk=vk, wScan=0,
                      dwFlags=KEYEVENTF_KEYUP if su else 0,
                      time=0, dwExtraInfo=0)
    inseriti = _user32.SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    assert inseriti == 1, (
        f"SendInput ha inserito {inseriti} eventi (errore "
        f"{ctypes.get_last_error()}): il banco non sa premere i tasti"
    )


def test_premendo_la_combinazione_gli_appunti_escono_redatti():
    """Il giro completo: Ctrl+Alt+R → motore → appunti.

    Rimette a posto gli appunti alla fine. La combinazione viene premuta
    **solo** se la registrazione e' riuscita: altrimenti quei tasti
    finirebbero nella finestra in primo piano di chi sta lavorando.
    """
    scattato, errori = [], []
    try:
        salvato = A.leggi_appunti()
    except OSError as e:
        pytest.skip(f"appunti non disponibili in questo ambiente: {e}")

    iban = "IT60X0542811101000000123456"
    A.scrivi_appunti(f"Bonifico a Giuseppe Moretti, IBAN {iban}")
    try:
        filo = A.avvia_scorciatoia(
            "ctrl+alt+r",
            lambda: scattato.append(
                A.passa_dagli_appunti(A.leggi_appunti, A.scrivi_appunti)),
            quando_fallisce=errori.append,
        )
        time.sleep(0.6)          # il thread deve arrivare a RegisterHotKey
        if filo is None or errori:
            pytest.skip(f"combinazione non registrabile qui: {errori}")

        for vk in (VK_CONTROL, VK_MENU, VK_R):
            _premi(vk)
        time.sleep(0.05)
        for vk in (VK_R, VK_MENU, VK_CONTROL):
            _premi(vk, su=True)

        for _ in range(40):
            if scattato:
                break
            time.sleep(0.05)

        assert scattato, (
            "la combinazione e' registrata e i tasti sono stati premuti, ma "
            "il richiamo non e' scattato: il ciclo dei messaggi non riceve "
            "WM_HOTKEY"
        )
        assert iban not in (A.leggi_appunti() or "")
        assert scattato[0].redazioni >= 2
    finally:
        if salvato is not None:
            A.scrivi_appunti(salvato)
