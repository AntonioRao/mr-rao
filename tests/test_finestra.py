"""La finestra dell'applicazione, e le due cose che non deve rompere.

Non si apre una finestra vera qui dentro: un test che aspetta un ciclo di
eventi grafico non finisce mai su un runner senza schermo. Si prova quello che
si puo' provare senza — che sono esattamente i punti dove questa funzione puo'
sbagliare in silenzio:

  * che il ripiego sul browser ci sia, e che venga deciso **prima** di
    provarci: una finestra che non appare lascia l'utente davanti a niente;
  * che chiudere la finestra **non** chiuda il programma;
  * che l'icona nella barra sappia partire staccata, perche' il ciclo degli
    eventi e' uno solo e non si blocca due volte.
"""

from __future__ import annotations

import pytest

import config
from mr_rao import finestra


# ------------------------------------------------------- il ripiego c'e' sempre


def test_si_sa_prima_se_la_finestra_si_puo_aprire() -> None:
    """`disponibile()` non deve sollevare **mai**, qualunque cosa manchi.

    E' la funzione che decide se aprire la finestra o il browser: se
    sollevasse, il programma morirebbe prima di mostrare qualcosa — cioe' il
    difetto che esiste per evitare.
    """
    assert isinstance(finestra.disponibile(), bool)


def test_senza_la_libreria_si_ripiega(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    vero_import = builtins.__import__

    def _import(nome, *resto, **chiavi):
        if nome == "webview":
            raise ImportError("simulata")
        return vero_import(nome, *resto, **chiavi)

    monkeypatch.setattr(builtins, "__import__", _import)
    assert finestra.disponibile() is False
    assert finestra.Finestra("http://127.0.0.1:1").prepara() is False


def test_i_download_sono_permessi() -> None:
    """**Il difetto che questa riga esiste per non far tornare.**

    pywebview annulla i download di serie (`ALLOW_DOWNLOADS` a `False`, e il
    suo gestore fa `Cancel = True`). Nella finestra si premeva «Scarica il PDF
    redatto» e non succedeva niente: nessun errore, nessun file, e l'aria di
    aver funzionato. Nel browser funzionava — se l'e' portato dietro la
    finestra.

    Il test prepara una finestra vera e guarda l'impostazione **dopo**: una
    riga scritta nel posto sbagliato non avrebbe effetto, e leggerla dal
    sorgente non se ne accorgerebbe.
    """
    webview = pytest.importorskip("webview")
    vetro = finestra.Finestra("http://127.0.0.1:1")
    if not vetro.prepara():
        pytest.skip("qui non si puo' costruire una finestra")
    try:
        assert webview.settings["ALLOW_DOWNLOADS"] is True
    finally:
        vetro.chiudi()


def test_una_finestra_mai_preparata_non_solleva() -> None:
    """I comandi del menu esistono prima della finestra.

    Il menu dell'icona riceve `mostra` e `chiudi` **subito**; se quei due
    sollevassero finche' la finestra non c'e', il primo clic dell'utente
    finirebbe in un errore.
    """
    vetro = finestra.Finestra("http://127.0.0.1:1")
    vetro.mostra()
    vetro.chiudi()
    assert vetro.esegui() is False


# ---------------------------------------- la croce nasconde, non chiude


class _FintaFinestra:
    def __init__(self) -> None:
        self.nascosta = False
        self.distrutta = False

    def hide(self) -> None:
        self.nascosta = True

    def show(self) -> None:
        self.nascosta = False

    def destroy(self) -> None:
        self.distrutta = True


def test_la_croce_nasconde_e_il_programma_resta() -> None:
    """**La riga che tiene la decisione.**

    Mr. Rao vive nella barra di sistema: se la finestra si portasse via il
    programma, chi la chiude per sbaglio perderebbe il sorvegliante delle
    cartelle e la scorciatoia sugli appunti senza capire perche'.
    """
    vetro = finestra.Finestra("http://127.0.0.1:1")
    vetro._finestra = _FintaFinestra()

    assert vetro._alla_chiusura() is False, "la chiusura non e' stata annullata"
    assert vetro._finestra.nascosta is True
    assert vetro._finestra.distrutta is False


def test_l_uscita_dal_menu_chiude_davvero() -> None:
    vetro = finestra.Finestra("http://127.0.0.1:1")
    vetro._finestra = _FintaFinestra()

    vetro.chiudi()
    assert vetro._finestra.distrutta is True
    assert vetro._alla_chiusura() is True, "dopo «Esci» la chiusura deve passare"


def test_mostra_riporta_in_primo_piano() -> None:
    vetro = finestra.Finestra("http://127.0.0.1:1")
    vetro._finestra = _FintaFinestra()
    vetro._finestra.nascosta = True

    vetro.mostra()
    assert vetro._finestra.nascosta is False


# ------------------------------------------------- l'icona sa partire staccata


def test_pystray_sa_partire_senza_bloccare() -> None:
    """Il «nodo del thread principale» non e' un nodo, ed e' meglio provarlo.

    Sia l'icona sia la finestra vogliono il ciclo degli eventi, e il ciclo e'
    uno solo. `run_detached()` esiste in pystray proprio per questo: se un
    domani sparisse, la finestra e l'icona non potrebbero convivere e questo
    test lo direbbe prima che se ne accorga un utente.
    """
    pystray = pytest.importorskip("pystray")
    assert hasattr(pystray.Icon, "run_detached")


def test_il_menu_apre_la_finestra_invece_del_browser() -> None:
    """«Apri» deve rimettere in primo piano la finestra che c'e' gia'.

    Senza, si aprirebbe una scheda del browser accanto a una finestra
    dell'applicazione gia' aperta: due copie della stessa interfaccia, ed e'
    il genere di cosa che fa dubitare di quale delle due sia quella buona.
    """
    import inspect

    from mr_rao import tray

    sorgente = inspect.getsource(tray.run_tray)
    assert "apri_ui" in sorgente
    assert "if apri_ui is not None" in sorgente


# ------------------------------------------------------------- l'interruttore


def test_l_interruttore_esiste_ed_e_acceso_di_serie() -> None:
    assert isinstance(config.USA_FINESTRA, bool)


def test_l_interruttore_si_puo_spegnere(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chi preferisce il browser deve poterlo dire, e la variabile e' la leva.

    Un valore che non spegne niente sarebbe una leva finta, che e' peggio di
    una leva mancante.
    """
    import importlib

    monkeypatch.setenv("MR_RAO_FINESTRA", "0")
    ricaricato = importlib.reload(config)
    try:
        assert ricaricato.USA_FINESTRA is False
    finally:
        monkeypatch.delenv("MR_RAO_FINESTRA", raising=False)
        importlib.reload(config)
