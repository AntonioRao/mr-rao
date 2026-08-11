"""Una finestra sua, invece di una scheda del browser.

Cosa cambia per chi usa il programma
------------------------------------

L'interfaccia e' la stessa, identica: le stesse pagine servite dallo stesso
server locale. Cambia il contorno — niente barra degli indirizzi, niente
schede, niente preferiti — e cambia cio' che si vede nella barra delle
applicazioni: un'applicazione, non una scheda di browser fra le altre venti.

Sotto c'e' il motore di rendering **gia' presente nel sistema operativo**
(WebView2 su Windows): non ci si porta dentro un browser, si punta a
`http://127.0.0.1:porta` come faceva il browser prima.

La chiusura della finestra **non chiude il programma**
------------------------------------------------------

E' la decisione che tiene insieme le due cose. Mr. Rao vive nella barra di
sistema, e la pagina si apre e si chiude a piacere; se la finestra si portasse
via il programma, chi la chiude per sbaglio perderebbe il sorvegliante delle
cartelle e la scorciatoia sugli appunti senza capire perche'.

Quindi la croce **nasconde**, e il programma resta dov'era: si riapre dal menu
dell'icona, e si esce da li' — come prima.

Il nodo del thread principale, e perche' non e' un nodo
--------------------------------------------------------

Sia l'icona nella barra sia questa finestra vogliono il ciclo degli eventi, e
il ciclo e' uno solo. Sembra un'architettura da decidere e non lo e':
`pystray.Icon.run_detached()` esiste apposta — la sua documentazione dice che
«consente di integrare pystray con altre librerie che richiedono un mainloop»
— quindi l'icona parte staccata e la finestra tiene il thread principale.

Quando non si puo'
------------------

Si torna al browser, che e' il comportamento di sempre. Non e' un ripiego
vergognoso: e' l'unica cosa onesta su una macchina dove il motore di rendering
di sistema manca o e' troppo vecchio. `disponibile()` lo dice **prima** di
provarci, cosi' chi chiama sceglie invece di scoprirlo con una finestra che
non appare.
"""
from __future__ import annotations

import config

#: Misure d'esordio. Non sono un vincolo: la finestra si ridimensiona, e la
#: pagina e' gia' responsive perche' doveva stare in una scheda stretta.
LARGHEZZA = 1180
ALTEZZA = 820
#: Sotto questa larghezza il pannello delle opzioni si accavalla: e' la stessa
#: soglia a cui il foglio di stile passa alla disposizione stretta.
MINIME = (760, 560)


def disponibile() -> bool:
    """C'e' di che aprire una finestra su questa macchina?

    Si guarda **prima** di provarci, invece di catturare l'errore dopo: una
    finestra che non appare lascia l'utente davanti a niente, mentre saperlo
    prima permette di aprire il browser e far funzionare il programma lo
    stesso.
    """
    try:
        import webview  # noqa: F401
    except Exception:
        return False
    return True


class Finestra:
    """La finestra dell'applicazione, e i due comandi che servono al menu.

    Si usa in tre tempi, e l'ordine conta: `prepara()` costruisce la finestra
    **senza** bloccare, cosi' l'icona nella barra puo' ricevere `mostra` e
    `chiudi` gia' collegati; poi `esegui()` prende il thread principale.

    Costruirla dentro `esegui()` avrebbe voluto dire consegnare al menu due
    comandi che per un istante non puntano a niente — e quell'istante e'
    proprio quello in cui l'utente clicca.
    """

    def __init__(self, url: str, titolo: str | None = None) -> None:
        self.url = url
        self.titolo = titolo or config.APP_NAME
        self._finestra = None
        self._chiusura_vera = False

    def prepara(self) -> bool:
        try:
            import webview
        except Exception:
            return False

        # **I download vanno permessi esplicitamente, e senza questa riga non
        # succede niente.**
        #
        # pywebview registra un gestore su `DownloadStarting` che, con
        # `ALLOW_DOWNLOADS` a `False` — il valore di serie — fa `Cancel = True`.
        # Il risultato e' il difetto peggiore che ci sia: si preme «Scarica il
        # PDF redatto», la pagina non dice niente, non compare nessun errore, e
        # il file non esiste da nessuna parte. Sembra riuscito.
        #
        # E' una cosa che la finestra ha portato con se': nel browser i
        # download funzionavano. Con il permesso, WebView2 apre un «salva con
        # nome» — che per un documento redatto e' meglio della cartella
        # Download, perche' chi lo salva decide dove finisce.
        webview.settings["ALLOW_DOWNLOADS"] = True

        try:
            self._finestra = webview.create_window(
                self.titolo,
                self.url,
                width=LARGHEZZA,
                height=ALTEZZA,
                min_size=MINIME,
                text_select=True,
            )
            self._finestra.events.closing += self._alla_chiusura
        except Exception:
            self._finestra = None
            return False
        return True

    def _alla_chiusura(self):
        """La croce nasconde, non chiude.

        Restituire `False` annulla la chiusura — e' cosi' che pywebview
        permette di intercettarla. Solo `chiudi()` alza la bandierina che la
        fa passare davvero.
        """
        if self._chiusura_vera:
            return True
        self.mostra_o_nascondi(nascondi=True)
        return False

    def mostra_o_nascondi(self, nascondi: bool = False) -> None:
        if self._finestra is None:
            return
        try:
            self._finestra.hide() if nascondi else self._finestra.show()
        except Exception:
            # Una finestra gia' distrutta non e' un errore da propagare: il
            # menu dell'icona resta utilizzabile e l'uscita funziona lo stesso.
            pass

    def mostra(self) -> None:
        self.mostra_o_nascondi(nascondi=False)

    def chiudi(self) -> None:
        """Chiude per davvero. E' la voce «Esci» del menu dell'icona."""
        self._chiusura_vera = True
        if self._finestra is None:
            return
        try:
            self._finestra.destroy()
        except Exception:
            pass

    def esegui(self) -> bool:
        """Blocca sul ciclo degli eventi finche' la finestra non e' distrutta.

        `False` vuol dire «non ho potuto»: chi chiama deve aprire il browser,
        perche' altrimenti non resta niente di visibile.
        """
        if self._finestra is None:
            return False
        try:
            import webview

            webview.start()
        except Exception:
            return False
        return True
