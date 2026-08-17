# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Ogni modulo dev'essere importabile davvero, non solo compilabile.

`python -m compileall` guarda la **sintassi**: dice che il file e' scritto in
Python, non che funziona. Un import circolare, un nome che non esiste piu'
nel modulo da cui lo si prende, una riga a livello di modulo che solleva
un'eccezione — tutte cose che passano il compileall a occhi chiusi e rompono
l'applicazione al primo avvio. E' gia' successo di committarne uno rotto.

Qui i moduli si importano sul serio, uno per uno, e ognuno **da solo**:
fra un modulo e il successivo si svuotano da `sys.modules` tutti i moduli del
progetto. Sembra pignoleria e non lo e'. Un import circolare A<->B spesso
riesce se prima si importa A e fallisce se prima si importa B: importandoli
tutti in fila nello stesso interprete, il primo che passa nasconde gli altri
e il controllo direbbe verde su un impianto rotto. Le librerie di terze parti
restano invece in cache, che e' quello che rende questo controllo veloce.

Uso:  python scripts/check_import.py
"""
from __future__ import annotations

import importlib
import io
import pkgutil
import sys
import traceback
from contextlib import redirect_stdout
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

# Moduli fuori dal pacchetto che sono comunque parte dell'applicazione.
MODULI_SCIOLTI = ("config", "app")

# I moduli `__main__.py` sono un caso a parte, e vanno detto apertamente:
# il loro corpo *e'* il programma (`mr_rao/__main__.py` fa
# `raise SystemExit(main())`), quindi importarli lancia la riga di comando.
# Toglierli dall'elenco sarebbe comodo e sbagliato: e' proprio li' che vive
# l'import di `mr_rao.cli`, cioe' esattamente il tipo di riga che questo
# controllo esiste per sorvegliare.
#
# La soluzione: importarli con un `argv` che li fa uscire subito e senza
# toccare niente. `--version` costruisce il parser, stampa e termina con 0;
# se l'import in cima al file fosse rotto arriverebbe un ImportError molto
# prima di arrivare ad argparse, ed e' quello che ci interessa vedere.
ARGV_INNOCUO = {
    "mr_rao.__main__": ["mr-rao", "--version"],
}


def moduli_da_controllare() -> list[str]:
    import mr_rao

    nomi = list(MODULI_SCIOLTI)
    nomi += [m.name for m in pkgutil.walk_packages(mr_rao.__path__, "mr_rao.")]
    nomi.append("mr_rao")
    return sorted(set(nomi))


def _e_del_progetto(nome: str) -> bool:
    return nome == "mr_rao" or nome.startswith("mr_rao.") or nome in MODULI_SCIOLTI


def _svuota_moduli_del_progetto() -> None:
    for nome in [n for n in sys.modules if _e_del_progetto(n)]:
        del sys.modules[nome]


def _importa(nome: str) -> None:
    """Importa un modulo, gestendo gli entry point che escono da soli."""
    if nome in ARGV_INNOCUO:
        argv = sys.argv
        sys.argv = list(ARGV_INNOCUO[nome])
        try:
            # `--version` stampa: la si mette da parte, cosi' l'esito del
            # controllo resta l'unica cosa che si legge a schermo.
            with redirect_stdout(io.StringIO()):
                importlib.import_module(nome)
        except SystemExit as uscita:
            if uscita.code not in (0, None):
                raise RuntimeError(
                    f"l'entry point e' uscito con codice {uscita.code} "
                    f"invece di 0 con argv={ARGV_INNOCUO[nome]}"
                ) from uscita
        finally:
            sys.argv = argv
        return

    importlib.import_module(nome)


def controlla(nomi: list[str]) -> list[tuple[str, str]]:
    """Importa ogni modulo da solo e restituisce l'elenco dei guasti.

    Andare e venire da `sys.modules` e' il mestiere di questa funzione, ma
    lasciarlo cosi' com'e' capitato non lo e': chi la chiama da dentro un
    processo gia' avviato — i test — si ritroverebbe il proprio `mr_rao`
    sostituito da una copia reimportata, con gli oggetti-modulo diversi da
    quelli a cui il resto del programma tiene i riferimenti. E' successo:
    un test lontano, che non c'entrava niente, ha cominciato a fallire solo
    quando girava dopo questo controllo. Alla fine si rimette tutto dov'era.
    """
    istantanea = {
        n: m for n, m in sys.modules.items() if _e_del_progetto(n)
    }
    guasti: list[tuple[str, str]] = []
    try:
        for nome in nomi:
            _svuota_moduli_del_progetto()
            try:
                _importa(nome)
            except BaseException as e:  # anche SystemExit: un modulo non deve uscire
                guasti.append(
                    (nome, "".join(traceback.format_exception_only(type(e), e)).strip())
                )
    finally:
        _svuota_moduli_del_progetto()
        sys.modules.update(istantanea)
    return guasti


def main() -> int:
    nomi = moduli_da_controllare()

    # Un controllo che non puo' fallire non e' un controllo: se la scoperta
    # dei moduli si rompe (pacchetto rinominato, `__path__` vuoto) l'elenco
    # diventa corto e tutto passerebbe a vuoto.
    if len(nomi) < 10:
        print(
            f"Trovati solo {len(nomi)} moduli ({', '.join(nomi)}): la scoperta "
            f"e' rotta, non il codice.",
            file=sys.stderr,
        )
        return 1

    # Un `__main__.py` nuovo non deve passare inosservato: senza un argv
    # innocuo il suo import lancerebbe un programma vero dentro la CI.
    orfani = [
        n for n in nomi if n.rsplit(".", 1)[-1] == "__main__" and n not in ARGV_INNOCUO
    ]
    if orfani:
        print(
            f"Entry point senza argv innocuo: {orfani}. Aggiungili a "
            f"ARGV_INNOCUO in {Path(__file__).name}, non all'elenco delle "
            f"esclusioni.",
            file=sys.stderr,
        )
        return 1

    guasti = controlla(nomi)
    if not guasti:
        print(f"import: {len(nomi)} moduli importati senza errori")
        return 0

    print(f"{len(guasti)} moduli su {len(nomi)} non si importano:", file=sys.stderr)
    for nome, errore in guasti:
        print(f"  - {nome}: {errore}", file=sys.stderr)
    print(
        "\nUn modulo che non si importa passa il compileall e rompe "
        "l'applicazione all'avvio.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
