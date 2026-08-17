# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Rilevamento porta occupata.

Su Windows Werkzeug imposta SO_REUSEADDR e il bind su una porta già in uso
**riesce**: due server restano legati alla stessa porta e le connessioni
finiscono a uno dei due in modo imprevedibile. Il risultato è che l'app dice
"sto servendo sulla 5000", apre il browser e l'utente vede il *vecchio*
server ancora attivo, senza un solo messaggio di errore.

Quindi non si chiede "riesco a fare bind?" ma "c'è già qualcuno che risponde?".
"""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable


def connect_host(host: str) -> str:
    """0.0.0.0 e :: sono indirizzi di ascolto, non di connessione."""
    if host in ("0.0.0.0", ""):
        return "127.0.0.1"
    if host == "::":
        return "::1"
    return host


def port_in_use(host: str, port: int) -> bool:
    """Chiede al sistema operativo, non alla rete.

    Due trappole, entrambe misurate su Windows:
    - un bind normale usa SO_REUSEADDR e RIESCE anche se la porta è già
      occupata: è proprio il modo in cui Werkzeug si sovrappone in silenzio.
      SO_EXCLUSIVEADDRUSE fa fallire il bind quando qualcun altro è legato.
    - una connect() di prova non è un'alternativa: verso una porta chiusa il
      firewall scarta il SYN e si aspetta il timeout pieno (~0.5 s) proprio
      nel caso normale, quello della porta libera.
    Fuori da Windows un bind senza SO_REUSEADDR fallisce già con EADDRINUSE.
    """
    # CodeQL py/bind-socket-all-network-interfaces (alert 11): il bind largo
    # e' reale, ma questo socket non serve niente a nessuno -- apre, guarda se
    # la porta e' libera e chiude subito (vedi il finally). L'unico modo di
    # arrivarci con host largo e' aver scelto MR_RAO_HOST=0.0.0.0, che e'
    # l'opzione di esposizione: da 1.7.0 quella scelta non spegne piu' la
    # difesa anti DNS-rebinding, l'allow-list resta sugli indirizzi veri.
    bind_host = "" if host in ("0.0.0.0", "") else host
    family = socket.AF_INET6 if ":" in bind_host else socket.AF_INET
    s = socket.socket(family, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):  # Windows
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        s.bind((bind_host, port))
        return False
    except OSError:
        return True
    finally:
        s.close()


@dataclass(frozen=True)
class Occupante:
    """Chi risponde già su quella porta, quando è uno dei nostri."""

    app: str
    versione: str

    def __str__(self) -> str:
        return f"{self.app} v{self.versione}"


def identifica_occupante(host: str, port: int, timeout: float = 1.0) -> Occupante | None:
    """Interroga `/api/health` e restituisce nome e versione, o None.

    None copre due casi che *per la decisione* si comportano allo stesso
    modo — «non è un Mr. Rao» e «non risponde HTTP» — ma non allo stesso modo
    per l'utente: in entrambi la porta resta occupata da un estraneo, e
    riusarla significherebbe mandarci il browser alla cieca.
    """
    url = f"http://{connect_host(host)}:{port}/api/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    app = data.get("app")
    if not app:
        return None
    return Occupante(app=str(app), versione=str(data.get("version", "?")))


def find_free_port(host: str, preferred: int, attempts: int = 20) -> int | None:
    for candidate in range(preferred, preferred + attempts):
        if not port_in_use(host, candidate):
            return candidate
    return None


# --- P0.3: che cosa fare quando la porta è già occupata --------------------
#
# Prima di questa voce la risposta era una sola per tutti i casi: **parti su
# un'altra porta**. Verso un programma estraneo è la risposta giusta; verso
# un altro Mr. Rao è precisamente la «seconda istanza cieca» che il backlog
# chiede di evitare da undici release. Costa più di quanto sembri:
#
#   - due icone nella barra, e nessuna delle due dice quale sta servendo cosa;
#   - la scorciatoia degli appunti è **una sola** per tutta la sessione di
#     Windows (`RegisterHotKey` è esclusiva): la seconda istanza non la
#     ottiene, e la perde in silenzio;
#   - il browser si apre sulla porta nuova, mentre eventuali segnalibri e la
#     finestra già aperta continuano a parlare con la vecchia.
#
# Chi lancia due volte non sta chiedendo due server: sta chiedendo *la
# finestra*. Quindi quando dall'altra parte c'è già la stessa versione, non
# nasce nessun processo — si apre il browser su quella e si esce.
#
# La versione **diversa** è il caso in cui non si riusa. L'utente ha appena
# lanciato un eseguibile preciso: mandarlo su una versione differente senza
# dirlo sarebbe il difetto originale (l'app che mostra un altro programma)
# ripetuto al contrario. Lì si parte su un'altra porta e si dicono entrambi
# i numeri.

RIUSA = "riusa"
PARTI = "parti"
RINUNCIA = "rinuncia"


@dataclass(frozen=True)
class Decisione:
    """Cosa fare all'avvio, e cosa dire mentre lo si fa."""

    azione: str
    porta: int | None
    righe: tuple[str, ...] = field(default=())


def decidi_avvio(
    host: str,
    porta: int,
    versione: str,
    *,
    occupata: Callable[[str, int], bool] = port_in_use,
    chi_occupa: Callable[[str, int], "Occupante | None"] = identifica_occupante,
    porta_libera: Callable[[str, int], "int | None"] = find_free_port,
) -> Decisione:
    """Decide, senza toccare nulla: è una funzione pura con le sonde iniettate.

    Sta qui e non in `app.py` per una ragione sola: in `app.py` il modulo
    costruisce l'applicazione Flask all'import, e un test che volesse provare
    questa scelta si porterebbe dietro tutto il server. Una decisione che non
    si può provare a buon mercato finisce per non essere provata.
    """
    if not occupata(host, porta):
        return Decisione(PARTI, porta)

    chi = chi_occupa(host, porta)

    if chi is not None and chi.versione == versione:
        return Decisione(
            RIUSA,
            porta,
            (
                f"{chi} e' gia' in ascolto sulla porta {porta}.",
                "-> Apro quella finestra invece di aprire una seconda istanza.",
            ),
        )

    libera = porta_libera(host, porta + 1)
    if libera is None:
        return Decisione(
            RINUNCIA,
            None,
            (
                f"!! La porta {porta} e' occupata da: {chi or 'un altro programma'}",
                "!! Nessuna porta libera trovata. Chiudi l'altra istanza e riprova.",
            ),
        )

    if chi is not None:
        righe = (
            f"!! Sulla porta {porta} risponde {chi}, ma questo eseguibile e'"
            f" la v{versione}.",
            "!! Non riuso quella finestra: mostrerebbe un programma diverso"
            " da quello che hai lanciato.",
            f"-> Questa istanza parte sulla porta {libera}.",
        )
    else:
        righe = (
            f"!! La porta {porta} e' gia' occupata da: un altro programma",
            "!! Se volevi usare quella, chiudi prima l'altra istanza.",
            f"-> Questa istanza parte sulla porta {libera}.",
        )
    return Decisione(PARTI, libera, righe)
