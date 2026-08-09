"""Installa (o toglie) il gate pre-commit di Mr. Rao.

L'hook e' **opzionale**: chi contribuisce decide se volerlo. Qui non si copia
niente dentro `.git/hooks`, si punta `core.hooksPath` a `.githooks/`. Due
ragioni:

- la copia invecchia. Un hook copiato resta la versione del giorno in cui e'
  stato installato, e nessuno se ne accorge: continua a girare e a dire verde
  mentre il controllo vero, nel repository, e' cambiato;
- si toglie con una riga (`git config --unset core.hooksPath`), che e' anche
  cio' che fa `--uninstall`. Reversibile davvero, non «cancella questi file».

Il prezzo di `core.hooksPath` e' che sostituisce **tutta** la cartella degli
hook, non solo il pre-commit: se in `.git/hooks` c'e' un hook vero,
installando si spegnerebbe in silenzio. Per questo lo si controlla prima e in
quel caso ci si ferma, invece di rompere qualcosa che non e' nostro.

Uso:
    python scripts/install_hooks.py --install
    python scripts/install_hooks.py --uninstall
    python scripts/install_hooks.py --status
"""
from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
PERCORSO_HOOK = ".githooks"
CARTELLA = RADICE / PERCORSO_HOOK
HOOK = CARTELLA / "pre-commit"


def _hook_attivi_in_git() -> list[str]:
    """Gli hook che git crea da solo finiscono in `.sample`: non contano."""
    cartella = RADICE / ".git" / "hooks"
    if not cartella.is_dir():
        return []
    return sorted(
        p.name for p in cartella.iterdir() if p.is_file() and p.suffix != ".sample"
    )


def _git(*argomenti: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *argomenti], cwd=RADICE, capture_output=True, text=True
    )


def _hooks_path_attuale() -> str:
    return _git("config", "--get", "core.hooksPath").stdout.strip()


def stato() -> int:
    attuale = _hooks_path_attuale()
    if attuale == PERCORSO_HOOK:
        print("gate pre-commit: INSTALLATO (core.hooksPath = .githooks)")
        return 0
    if attuale:
        print(f"gate pre-commit: non installato; core.hooksPath punta a '{attuale}'")
        return 0
    print("gate pre-commit: non installato")
    return 0


def installa() -> int:
    if not HOOK.is_file():
        print(f"manca {HOOK.relative_to(RADICE).as_posix()}", file=sys.stderr)
        return 1

    # Terminazioni CRLF: rompono o no a seconda del sistema, e la differenza
    # e' stata misurata invece che immaginata. Su Linux uno shebang
    # `#!/bin/sh\r` non parte affatto ("not found", exit 127); la `sh` di Git
    # for Windows il CR lo tollera. Quindi qui si rifiuta dove romperebbe
    # davvero e si avvisa dove no: bloccare l'installazione su Windows per un
    # guasto che su Windows non c'e' sarebbe un rosso per il motivo sbagliato,
    # e quelli insegnano a non leggere i messaggi.
    if b"\r\n" in HOOK.read_bytes():
        messaggio = (
            f"{HOOK.name} ha terminazioni CRLF. Con quelle lo script non parte "
            f"su Linux/macOS (shebang '#!/bin/sh\\r' -> 'not found'). "
            f".gitattributes impone LF, ma un file gia' in cache no: "
            f"riconvertilo."
        )
        if os.name != "nt":
            print(messaggio, file=sys.stderr)
            return 1
        print(f"attenzione: {messaggio}", file=sys.stderr)

    esistenti = _hook_attivi_in_git()
    if esistenti:
        print(
            f".git/hooks contiene gia' hook attivi: {', '.join(esistenti)}.\n"
            f"core.hooksPath li spegnerebbe tutti in silenzio. Spostali in "
            f".githooks/ oppure installa a mano solo cio' che ti serve.",
            file=sys.stderr,
        )
        return 1

    if os.name != "nt":
        # Su Windows git ignora il bit di esecuzione; altrove senza non parte.
        HOOK.chmod(HOOK.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    esito = _git("config", "core.hooksPath", PERCORSO_HOOK)
    if esito.returncode != 0:
        print(esito.stderr.strip() or "git config ha dato errore", file=sys.stderr)
        return 1

    print("gate pre-commit installato (core.hooksPath = .githooks).")
    print("  esegue compileall + scripts/check_import.py, circa mezzo secondo;")
    print("  MR_RAO_HOOK_FULL=1 aggiunge pytest;")
    print("  si toglie con: python scripts/install_hooks.py --uninstall")
    return 0


def disinstalla() -> int:
    attuale = _hooks_path_attuale()
    if not attuale:
        print("gate pre-commit: non era installato, niente da fare.")
        return 0
    if attuale != PERCORSO_HOOK:
        print(
            f"core.hooksPath vale '{attuale}', che non l'ha messo questo "
            f"script: non lo tocco.",
            file=sys.stderr,
        )
        return 1

    esito = _git("config", "--unset", "core.hooksPath")
    # `--unset` torna 5 quando la chiave non c'era: qui l'abbiamo appena letta,
    # ma se un altro processo l'ha tolta nel frattempo il risultato voluto c'e'.
    if esito.returncode not in (0, 5):
        print(esito.stderr.strip() or "git config ha dato errore", file=sys.stderr)
        return 1

    print("gate pre-commit rimosso.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="install_hooks",
        description="Installa o toglie il gate pre-commit (opzionale).",
    )
    gruppo = parser.add_mutually_exclusive_group(required=True)
    gruppo.add_argument("--install", action="store_true", help="attiva l'hook")
    gruppo.add_argument("--uninstall", action="store_true", help="toglie l'hook")
    gruppo.add_argument("--status", action="store_true", help="dice se e' attivo")
    args = parser.parse_args(argv)

    if args.install:
        return installa()
    if args.uninstall:
        return disinstalla()
    return stato()


if __name__ == "__main__":
    raise SystemExit(main())
