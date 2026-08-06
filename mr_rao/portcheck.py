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


def describe_occupant(host: str, port: int, timeout: float = 1.0) -> str | None:
    """Se chi occupa la porta è un Mr. Rao, dice quale versione."""
    url = f"http://{connect_host(host)}:{port}/api/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None
    app = data.get("app")
    if not app:
        return None
    return f"{app} v{data.get('version', '?')}"


def find_free_port(host: str, preferred: int, attempts: int = 20) -> int | None:
    for candidate in range(preferred, preferred + attempts):
        if not port_in_use(host, candidate):
            return candidate
    return None
