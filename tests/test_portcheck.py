# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Regressioni sul rilevamento della porta occupata.

Il sintomo pagato: su Windows Werkzeug imposta SO_REUSEADDR e il bind su una
porta già in uso RIESCE. L'app annunciava "in ascolto sulla 5000", apriva il
browser, e il browser parlava con l'altra istanza — una vecchia versione
installata — che mostrava un numero di versione diverso. Nessun errore.
"""
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from mr_rao.portcheck import connect_host, find_free_port, identifica_occupante, port_in_use


@pytest.fixture()
def porta_occupata():
    """Un socket in ascolto su una porta effimera."""
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    yield s.getsockname()[1]
    s.close()


def _porta_libera() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    porta = s.getsockname()[1]
    s.close()
    return porta


@pytest.mark.parametrize(
    ("ascolto", "connessione"),
    [("0.0.0.0", "127.0.0.1"), ("", "127.0.0.1"), ("::", "::1"), ("127.0.0.1", "127.0.0.1")],
)
def test_indirizzo_di_ascolto_tradotto_per_connessione(ascolto, connessione):
    """0.0.0.0 è un indirizzo di bind, non di connessione."""
    assert connect_host(ascolto) == connessione


def test_porta_occupata_rilevata(porta_occupata):
    assert port_in_use("127.0.0.1", porta_occupata) is True


def test_porta_libera_non_segnalata():
    assert port_in_use("127.0.0.1", _porta_libera()) is False


def test_rileva_anche_dove_il_bind_ingenuo_riesce(porta_occupata):
    """Il cuore del bug: su Windows un bind con SO_REUSEADDR sulla porta già
    occupata RIESCE (è quello che fa Werkzeug). Il rilevamento deve dire
    'occupata' comunque."""
    ingenuo = socket.socket()
    ingenuo.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        ingenuo.bind(("127.0.0.1", porta_occupata))
        bind_ingenuo_riuscito = True
    except OSError:
        bind_ingenuo_riuscito = False   # comportamento POSIX
    finally:
        ingenuo.close()

    assert port_in_use("127.0.0.1", porta_occupata) is True, (
        "porta occupata non rilevata"
        + (" (e il bind ingenuo riesce: sovrapposizione silenziosa)" if bind_ingenuo_riuscito else "")
    )


def test_rilevamento_immediato():
    """Non deve costare un timeout di rete: veniva chiamato a ogni avvio.
    Una connect() di prova verso una porta chiusa aspetta il timeout pieno
    perché il firewall scarta il SYN."""
    import time

    libera = _porta_libera()
    inizio = time.perf_counter()
    for _ in range(20):
        port_in_use("127.0.0.1", libera)
    durata = time.perf_counter() - inizio
    assert durata < 0.5, f"20 controlli in {durata:.2f}s: troppo lento per l'avvio"


def test_find_free_port_salta_quella_occupata(porta_occupata):
    scelta = find_free_port("127.0.0.1", porta_occupata)
    assert scelta is not None
    assert scelta != porta_occupata
    assert port_in_use("127.0.0.1", scelta) is False


def test_find_free_port_restituisce_la_preferita_se_libera():
    libera = _porta_libera()
    assert find_free_port("127.0.0.1", libera) == libera


@pytest.fixture()
def finto_server():
    """Server che imita /api/health di una vecchia istanza."""
    corpo = json.dumps({"app": "Mr. Rao", "version": "1.0.0", "status": "ok"}).encode()

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/api/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)
            else:
                self.send_error(404)

        def log_message(self, *_a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    # shutdown() ferma il ciclo ma NON chiude il socket in ascolto: pytest
    # lo segnalava come ResourceWarning a fine sessione. Un solo avviso
    # innocuo in coda alla suite e' comunque un avviso, e conviene che la
    # riga finale resti pulita: e' quella che si guarda quando qualcosa
    # inizia davvero a rompersi.
    srv.shutdown()
    srv.server_close()


def test_riconosce_l_istanza_che_occupa_la_porta(finto_server):
    """È l'informazione che serviva: chi c'è e che versione ha."""
    assert str(identifica_occupante("127.0.0.1", finto_server)) == "Mr. Rao v1.0.0"


def test_occupante_sconosciuto(porta_occupata):
    """Un socket che non parla HTTP non deve far esplodere nulla."""
    assert identifica_occupante("127.0.0.1", porta_occupata, timeout=0.5) is None


def test_porta_libera_nessun_occupante():
    assert identifica_occupante("127.0.0.1", _porta_libera(), timeout=0.5) is None
