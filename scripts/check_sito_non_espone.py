# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il sito pubblicato serve qualcosa che non e' il sito?

Nasce da un difetto del **22/08/2026**, e da come e' stato dichiarato chiuso
troppo presto.

Sul sito erano finiti due file che nessuno voleva pubblicare: `_rebuild.py` --
lo script che costruisce il sito -- e `test-results/.last-run.json`, un
residuo di Playwright. Sono stati tolti dalla cartella, ed e' stato aggiunto
un banco che verifica la cartella (`tests/test_landing_pubblicata.py`). Quel
banco era ed e' giusto, e continua a passare: **nella cartella non c'e'
niente di troppo**.

Ma il sito continuava a servirli. La verifica di allora aveva interrogato gli
indirizzi con un parametro di cache-busting -- `?cb=1234` -- e rispondevano
404. Con quel parametro si misura **il deploy**; senza, si misura **il
servizio**, ed e' quello che riceve una persona. Erano due domande diverse, e
ne era stata fatta una sola.

Quindi questo controllo interroga **come un visitatore**: nessun parametro,
nessuna intestazione che chieda di saltare la cache. Se un indirizzo che non
deve esistere risponde 200, lo dice -- non importa se il file non c'e' piu'
da nessuna parte: cio' che conta e' che qualcuno lo riceve.

Uso:  python scripts/check_sito_non_espone.py
      python scripts/check_sito_non_espone.py --host https://esempio/
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from typing import Callable, Iterable

HOST = "https://rao.valor-cyber.com"

# Gli indirizzi che non devono rispondere 200. Due famiglie, e la seconda e'
# quella che ha morso: non e' un elenco di cose «tipiche» da scanner, sono i
# file che sono davvero finiti online una volta.
VIETATI = (
    # cio' che il sito non e' -- la macchina che lo costruisce e i residui
    "/_rebuild.py",
    "/rigenera_pubblicato.py",
    "/test-results/.last-run.json",
    "/.assetsignore",
    # i classici, che qui non sono mai esistiti: servono a verificare che il
    # ripiego con la homepage non torni (prima del 22/08 rispondevano tutti
    # 200 con 52 KB di HTML)
    "/.git/HEAD",
    "/.env",
    "/wrangler.toml",
    "/package.json",
)

# Indirizzi che DEVONO rispondere: senza di loro un controllo che trova solo
# 404 sarebbe verde anche con il sito spento.
ATTESI = ("/", "/mobile/", "/robots.txt", "/.well-known/security.txt")

INTESTAZIONI = {
    "User-Agent": "mr-rao-check-non-espone/1.0 (+https://github.com/AntonioRao/mr-rao)",
}


def stato(url: str, timeout: float = 15.0) -> int:
    """Il codice di stato, senza chiedere niente alla cache.

    **Nessun `Cache-Control: no-cache` e nessun parametro di cache-busting**,
    ed e' il punto di tutto il file: quelli cambiano la chiave della cache e
    fanno arrivare la richiesta all'origine, cioe' rispondono a una domanda
    diversa da quella che si vuole fare qui.
    """
    richiesta = urllib.request.Request(url, headers=INTESTAZIONI, method="GET")
    try:
        with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
            return risposta.status
    except urllib.error.HTTPError as e:
        return e.code


def controlla(
    host: str = HOST, lettore: Callable[[str], int] = stato
) -> tuple[list[str], list[str]]:
    """Restituisce (esposti, spenti): due liste, non un booleano.

    Sono due guasti diversi -- «serve cio' che non deve» e «non serve cio'
    che deve» -- e un unico verdetto li confonderebbe.
    """
    esposti = [p for p in VIETATI if lettore(host + p) == 200]
    spenti = [p for p in ATTESI if lettore(host + p) != 200]
    return esposti, spenti


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Interroga il sito pubblicato COME UN VISITATORE (niente "
            "cache-busting) e dice se serve qualcosa che non e' il sito."
        )
    )
    parser.add_argument("--host", default=HOST)
    args = parser.parse_args(list(argv) if argv is not None else None)

    esposti, spenti = controlla(args.host)

    for p in esposti:
        print(f"  [esposto] {args.host}{p}: risponde 200 a chi lo chiede.", file=sys.stderr)
    for p in spenti:
        print(f"  [spento]  {args.host}{p}: non risponde 200.", file=sys.stderr)

    if esposti:
        print(
            "\nIl file puo' essere gia' sparito dal deploy e uscire lo stesso: "
            "una copia conservata al bordo viene servita prima. Si toglie con "
            "una purga della cache (pannello Cloudflare -> Caching -> Purge "
            "Cache), e la si verifica **rilanciando questo controllo**, non "
            "interrogando l'indirizzo con un `?cb=`.",
            file=sys.stderr,
        )
        return 1
    if spenti:
        return 2

    print(f"  il sito serve il sito: {len(VIETATI)} indirizzi vietati, tutti chiusi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
