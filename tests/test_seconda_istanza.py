"""P0.3 — la seconda istanza non deve nascere.

Prima di questa voce l'app aveva **una sola** risposta alla porta occupata:
parti su un'altra porta. Verso un programma estraneo è giusta; verso un altro
Mr. Rao produce due server, due icone nella barra, e la scorciatoia degli
appunti che il secondo processo non ottiene (`RegisterHotKey` è esclusiva per
tutta la sessione di Windows) e perde senza dirlo.

Qui si prova la scelta, che è una funzione pura con le sonde iniettate, e poi
si prova il giro vero: un finto `/api/health` che dichiara la **nostra**
versione, e `app.py` lanciato davvero contro di lui.

**Il controllo dev'essere in grado di dire di no in entrambi i versi.** Una
regola «riusa sempre» passerebbe metà di questi test: per questo ci sono sia
i casi che devono decidere RIUSA sia quelli che devono rifiutarsi — versione
diversa, occupante estraneo, porta libera.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

import config
from mr_rao.portcheck import (
    PARTI,
    RINUNCIA,
    RIUSA,
    Occupante,
    decidi_avvio,
    identifica_occupante,
)

RADICE = Path(__file__).resolve().parent.parent
NOSTRA = "9.9.9"


def _sonde(*, occupata: bool, chi: Occupante | None, libera: int | None = 5001):
    """Le tre sonde di `decidi_avvio`, fissate a mano."""
    return {
        "occupata": lambda h, p: occupata,
        "chi_occupa": lambda h, p: chi,
        "porta_libera": lambda h, p: libera,
    }


# --- la scelta -------------------------------------------------------------

def test_porta_libera_si_parte_e_basta():
    d = decidi_avvio("127.0.0.1", 5000, NOSTRA, **_sonde(occupata=False, chi=None))
    assert d.azione == PARTI
    assert d.porta == 5000
    assert d.righe == (), "avvio normale: nessun rumore da leggere"


def test_stessa_versione_gia_in_ascolto_non_nasce_niente():
    """Il cuore di P0.3."""
    d = decidi_avvio(
        "127.0.0.1", 5000, NOSTRA,
        **_sonde(occupata=True, chi=Occupante("Mr. Rao", NOSTRA)),
    )
    assert d.azione == RIUSA, (
        "c'e' gia' la stessa versione in ascolto e si sta avviando una "
        "seconda istanza: e' esattamente il difetto di P0.3"
    )
    assert d.porta == 5000, "riusare significa la porta di prima, non un'altra"


def test_versione_diversa_non_si_riusa():
    """Il verso opposto, e la ragione per cui non basta «riusa sempre».

    Chi ha lanciato questo eseguibile ha scelto *questa* versione: mandarlo
    su un'altra senza dirlo sarebbe il difetto originale — l'app che mostra
    un programma diverso da quello che annuncia — ripetuto al contrario.
    """
    d = decidi_avvio(
        "127.0.0.1", 5000, NOSTRA,
        **_sonde(occupata=True, chi=Occupante("Mr. Rao", "1.0.0")),
    )
    assert d.azione == PARTI
    assert d.porta == 5001
    testo = " ".join(d.righe)
    assert "1.0.0" in testo and NOSTRA in testo, (
        "quando le versioni differiscono vanno detti entrambi i numeri, "
        f"altrimenti non si capisce cosa si sta guardando: {d.righe}"
    )


def test_occupante_estraneo_si_cambia_porta():
    d = decidi_avvio(
        "127.0.0.1", 5000, NOSTRA, **_sonde(occupata=True, chi=None)
    )
    assert d.azione == PARTI
    assert d.porta == 5001
    assert any("altro programma" in r for r in d.righe)


def test_nessuna_porta_libera_si_rinuncia():
    d = decidi_avvio(
        "127.0.0.1", 5000, NOSTRA,
        **_sonde(occupata=True, chi=None, libera=None),
    )
    assert d.azione == RINUNCIA
    assert d.porta is None


def test_riuso_solo_sulla_versione_identica_non_sul_nome():
    """Un altro programma che si chiamasse «Mr. Rao» non basta: conta il numero."""
    d = decidi_avvio(
        "127.0.0.1", 5000, NOSTRA,
        **_sonde(occupata=True, chi=Occupante("Mr. Rao", NOSTRA + "-dev")),
    )
    assert d.azione == PARTI


# --- l'identificazione -----------------------------------------------------

def _finto_health(payload: object) -> int:
    """Alza un server che risponde `payload` su /api/health. Torna la porta."""
    corpo = json.dumps(payload).encode()

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
    _APERTI.append(srv)
    return srv.server_address[1]


_APERTI: list[HTTPServer] = []


@pytest.fixture(autouse=True)
def _chiudi_i_finti_server():
    yield
    while _APERTI:
        s = _APERTI.pop()
        s.shutdown()
        s.server_close()


def test_identifica_nome_e_versione():
    porta = _finto_health({"app": "Mr. Rao", "version": "1.2.3"})
    chi = identifica_occupante("127.0.0.1", porta)
    assert chi == Occupante("Mr. Rao", "1.2.3")
    assert str(chi) == "Mr. Rao v1.2.3"


def test_health_che_non_e_un_oggetto_non_fa_esplodere_niente():
    """`json.loads` di una lista non ha `.get`: prima sarebbe stato un crash."""
    porta = _finto_health(["ok"])
    assert identifica_occupante("127.0.0.1", porta) is None


def test_health_senza_nome_non_e_uno_dei_nostri():
    porta = _finto_health({"status": "ok"})
    assert identifica_occupante("127.0.0.1", porta) is None


# --- il giro vero ----------------------------------------------------------

@pytest.mark.slow
def test_lanciando_app_py_contro_se_stesso_il_processo_esce_senza_servire():
    """La prova che conta: `app.py` lanciato davvero mentre «c'è già».

    Le prove sulle sonde iniettate dicono che la *decisione* è giusta; solo
    questa dice che l'avvio la rispetta. Senza, resterebbe possibile che
    `decidi_avvio` risponda RIUSA e `app.py` avvii comunque il server —
    che è precisamente il difetto, spostato di una funzione.
    """
    porta = _finto_health({"app": config.APP_NAME, "version": config.APP_VERSION})

    amb = dict(os.environ)
    amb.update({
        "MR_RAO_PORT": str(porta),
        "MR_RAO_TRAY": "0",
        "MR_RAO_OPEN_BROWSER": "0",
        "MR_RAO_SCORCIATOIA": "0",
        "PYTHONIOENCODING": "utf-8",
    })

    esito = subprocess.run(
        [sys.executable, str(RADICE / "app.py")],
        cwd=str(RADICE), env=amb, capture_output=True, text=True, timeout=180,
    )

    assert esito.returncode == 0, (
        f"uscita {esito.returncode}: trovare la finestra gia' aperta non e' "
        f"un errore.\n{esito.stdout}\n{esito.stderr}"
    )
    assert "seconda istanza" in esito.stdout, (
        f"l'utente non ha modo di sapere perche' non e' partito nulla:\n{esito.stdout}"
    )
    # E soprattutto: non deve aver preso una porta per sé.
    s = socket.socket()
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        s.bind(("127.0.0.1", porta + 1))
    except OSError:  # pragma: no cover
        pytest.fail(f"la porta {porta + 1} e' occupata: e' nata una seconda istanza")
    finally:
        s.close()
