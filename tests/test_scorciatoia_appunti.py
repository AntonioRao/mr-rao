# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""La scorciatoia che redige gli appunti sul posto.

Il pezzo che decide -- cosa succede al testo, cosa dice la notifica, cosa si
tiene per il ripristino -- non tocca Windows: `passa_dagli_appunti()` riceve
le funzioni di lettura e scrittura dall'esterno. E' quello che permette di
provarlo qui invece di premere i tasti a mano su una macchina sola, che non
sarebbe una prova ripetibile e non girerebbe in CI.

Quello che questi test devono proteggere non e' «funziona»: e' che **non
faccia peggio del non usarlo**. Le tre cose che rovinerebbero la funzione
sono tutte silenziose — riscrivere appunti che non sono cambiati, perdere
l'originale senza via di ritorno, e dire «fatto» quando e' rimasto dentro un
sospetto.
"""
from __future__ import annotations

import pytest

from mr_rao.appunti import (
    Esito,
    Memoria,
    analizza_combinazione,
    passa_dagli_appunti,
    redigi,
    ripristina,
)


class Finti:
    """Appunti finti: registrano cosa gli e' stato scritto, e quante volte."""

    def __init__(self, contenuto: str | None = None):
        self.contenuto = contenuto
        self.scritture: list[str] = []

    def leggi(self) -> str | None:
        return self.contenuto

    def scrivi(self, testo: str) -> None:
        self.contenuto = testo
        self.scritture.append(testo)


# --- il mestiere -------------------------------------------------------------

def test_il_testo_negli_appunti_esce_redatto():
    a = Finti("Il contratto con Giuseppe Moretti, IBAN IT60X0542811101000000123456.")
    esito = passa_dagli_appunti(a.leggi, a.scrivi)
    assert esito.cambiato
    assert "IT60X0542811101000000123456" not in a.contenuto
    assert "Moretti" not in a.contenuto
    assert esito.redazioni >= 2


def test_e_lo_stesso_motore_della_conversione():
    """Se un giorno qui nascesse una seconda implementazione, divergerebbe —
    e in un motore di redazione una divergenza e' una fuga che non si vede."""
    from mr_rao.privacy import PrivacyOptions, apply_privacy_filter

    testo = "Scrivi a g.moretti@studio.it oppure allo 011/7323929."
    atteso, _ = apply_privacy_filter(testo, PrivacyOptions())
    assert redigi(testo).testo == atteso


# --- le tre cose che rovinerebbero la funzione -------------------------------

def test_se_non_cambia_niente_gli_appunti_non_vengono_riscritti():
    """Riscrivere appunti identici li toglierebbe comunque all'applicazione
    che li possiede — il formato ricco, l'immagine affiancata — senza nessun
    guadagno."""
    a = Finti("Il preventivo e' pronto, ci sentiamo domani.")
    esito = passa_dagli_appunti(a.leggi, a.scrivi)
    assert not esito.cambiato
    assert a.scritture == [], "ha riscritto gli appunti senza motivo"


def test_l_originale_resta_recuperabile():
    """Sovrascrivere gli appunti distrugge l'originale: senza via di ritorno,
    il primo caso in cui la redazione toglie qualcosa che serviva fa perdere
    il testo."""
    originale = "Bonifico a Giuseppe Moretti, IBAN IT60X0542811101000000123456."
    a = Finti(originale)
    m = Memoria()
    passa_dagli_appunti(a.leggi, a.scrivi, memoria=m)
    assert a.contenuto != originale

    ripristina(a.scrivi, m)
    assert a.contenuto == originale


def test_la_notifica_dice_che_i_sospetti_non_sono_stati_tolti():
    """E' la meta' del messaggio che conta: un «da controllare» maggiore di
    zero vuol dire che negli appunti e' rimasto qualcosa. Un messaggio che
    dicesse solo «9 redatti» inviterebbe a incollare senza guardare."""
    messaggio = Esito(redazioni=9, sospetti=2, cambiato=True).messaggio()
    assert "9" in messaggio and "2" in messaggio
    assert "non tolt" in messaggio, messaggio


def test_la_notifica_compare_anche_quando_non_trova_niente():
    """Senza messaggio non si distingue «ha funzionato» da «non e' partito»."""
    assert Esito(cambiato=False).messaggio().strip()
    assert "Nessun dato" in Esito(cambiato=False).messaggio()


# --- i modi in cui puo' andare storto ---------------------------------------

@pytest.mark.parametrize("dentro", [None, "", "   \n  "])
def test_appunti_senza_testo(dentro):
    """Un'immagine, un file, niente: si dice, non si inventa una conversione."""
    a = Finti(dentro)
    esito = passa_dagli_appunti(a.leggi, a.scrivi)
    assert esito.errore
    assert a.scritture == []


def test_appunti_occupati_da_un_altro_programma():
    def leggi():
        raise OSError("gli appunti sono occupati da un altro programma")

    esito = passa_dagli_appunti(leggi, lambda t: None)
    assert "occupati" in esito.errore


def test_se_la_scrittura_fallisce_non_si_dice_fatto():
    def scrivi(_):
        raise OSError("rifiutati")

    a = Finti("IBAN IT60X0542811101000000123456")
    esito = passa_dagli_appunti(a.leggi, scrivi)
    assert esito.errore and not esito.cambiato


def test_senza_originale_il_ripristino_lo_dice():
    a = Finti("qualcosa")
    esito = ripristina(a.scrivi, Memoria())
    assert esito.errore
    assert a.scritture == []


# --- la combinazione ---------------------------------------------------------

def test_una_combinazione_valida_si_legge():
    modificatori, codice, leggibile = analizza_combinazione("ctrl+alt+r")
    assert modificatori & 0x0002 and modificatori & 0x0001
    assert modificatori & 0x4000, "manca NOREPEAT: tenendo premuto si ripete"
    assert codice == ord("R")
    assert leggibile == "Ctrl+Alt+R"


@pytest.mark.parametrize("brutta,perche", [
    ("r", "modificatore"),
    ("ctrl+alt", "tasto"),
    ("ctrl+alt+r+m", "due tasti"),
    ("ctrl+alt+invio", "non riconosciuto"),
    ("", "vuota"),
])
def test_una_combinazione_scritta_male_si_ferma_dicendolo(brutta, perche):
    """Registrarne una diversa da quella che l'utente credeva sarebbe il modo
    peggiore: la scorciatoia «non funziona» e non si capisce perche'."""
    with pytest.raises(ValueError) as e:
        analizza_combinazione(brutta)
    assert perche in str(e.value), str(e.value)


def test_il_solo_tasto_non_basta():
    """Una scorciatoia senza modificatori scatterebbe mentre si scrive."""
    with pytest.raises(ValueError):
        analizza_combinazione("f5x")


# --- la promessa che va tenuta ----------------------------------------------

def test_niente_finisce_su_disco(tmp_path, monkeypatch):
    """L'originale vive nel processo e muore con lui. Un file di ripristino
    sarebbe un file con dentro i dati personali in chiaro, cioe' esattamente
    cio' che questo programma esiste per non fare."""
    monkeypatch.chdir(tmp_path)
    prima = set(tmp_path.rglob("*"))
    a = Finti("Giuseppe Moretti, IBAN IT60X0542811101000000123456")
    m = Memoria()
    passa_dagli_appunti(a.leggi, a.scrivi, memoria=m)
    ripristina(a.scrivi, m)
    assert set(tmp_path.rglob("*")) == prima


def test_gli_appunti_veri_di_windows():
    """Il test che serviva, e che i ventuno qui sopra non potevano essere.

    Quelli provano lo strato che **decide**, dove lettura e scrittura arrivano
    da fuori. E' giusto che sia cosi', ma vuol dire che non guardano lo strato
    che parla con il sistema operativo — dove non c'e' niente da decidere e
    tutto da sbagliare.

    E si e' sbagliato: senza dichiarare `restype`, ctypes assumeva che
    `GetClipboardData` tornasse un intero a 32 bit invece di un HANDLE a 64.
    L'handle arrivava troncato, `GlobalLock` falliva, la lettura tornava
    `None` — con ventuno test verdi e la funzione che non funzionava. L'ha
    trovato una prova dal vivo, e questa e' quella prova messa dove non si
    dimentica.

    Salva il contenuto degli appunti e lo rimette a posto alla fine.
    """
    import sys

    if sys.platform != "win32":
        pytest.skip("gli appunti di Windows esistono solo su Windows")

    from mr_rao.appunti import leggi_appunti, scrivi_appunti

    # Sonda: se in questo ambiente gli appunti non ci sono proprio, si salta.
    # Da qui in poi ogni problema e' un guasto, non un ambiente diverso.
    try:
        salvato = leggi_appunti()
    except OSError as e:
        pytest.skip(f"appunti non disponibili in questo ambiente: {e}")

    try:
        iban = "IT60X0542811101000000123456"
        scrivi_appunti(f"Bonifico su IBAN {iban}")
        assert leggi_appunti() == f"Bonifico su IBAN {iban}", (
            "scritto e riletto non coincidono: e' esattamente il difetto degli "
            "handle troncati"
        )
        esito = passa_dagli_appunti(leggi_appunti, scrivi_appunti)
        assert esito.cambiato and esito.redazioni >= 1
        assert iban not in leggi_appunti()
    finally:
        if salvato is not None:
            scrivi_appunti(salvato)


def test_non_si_usa_il_gancio_di_tastiera():
    """La differenza fra questa funzione e un keylogger sta in quale
    meccanismo di Windows si chiede.

    `SetWindowsHookEx(WH_KEYBOARD_LL)` consegna **ogni** tasto premuto sulla
    macchina; `RegisterHotKey` ne dichiara **una** e Windows recapita solo
    quella. Se un domani qualcuno cambiasse meccanismo per avere combinazioni
    piu' libere, questo test lo ferma — ed e' una promessa scritta in
    `docs/SCORCIATOIA-APPUNTI.md`, quindi non e' pignoleria: e' un documento
    pubblicato che smetterebbe di essere vero.
    """
    from pathlib import Path

    sorgente = Path(__file__).resolve().parents[1] / "mr_rao" / "appunti.py"
    testo = sorgente.read_text(encoding="utf-8")
    righe_di_codice = [
        r for r in testo.splitlines()
        if "SetWindowsHookEx" in r and not r.lstrip().startswith("#")
        and "`" not in r
    ]
    assert not righe_di_codice, righe_di_codice
    assert "RegisterHotKey" in testo


def test_fuori_da_windows_la_scorciatoia_non_parte():
    """Su macOS/Linux `ctypes.WinDLL` non esiste: avviare la scorciatoia
    deve tornare None, non cadere. È il vincolo del pacchetto Mac."""
    import sys

    from mr_rao.appunti import avvia_scorciatoia

    if sys.platform == "win32":
        import config

        assert config.SCORCIATOIA_ATTIVA in (True, False)
        return
    import config

    assert config.SCORCIATOIA_ATTIVA is False
    assert avvia_scorciatoia("ctrl+alt+r", lambda: None) is None
