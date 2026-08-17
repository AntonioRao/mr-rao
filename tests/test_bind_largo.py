# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il conto che permette di spegnere una regola di CodeQL.

`.github/codeql/codeql-config.yml` esclude
`py/bind-socket-all-network-interfaces`, perche' l'alert su
`mr_rao/portcheck.py` e' legato alla posizione della riga e torna a ogni
refactor: e' stato archiviato due volte (#11 e #33) con la stessa
motivazione, e ri-archiviarlo a mano non e' un presidio, e' manutenzione.

**Ma `query-filters` in CodeQL non si puo' restringere a un percorso**: vale
per tutto il repository. Quindi quella riga non silenzia l'alert solo dove
la conosciamo, lo silenzia anche nel file che ancora non esiste — cioe'
esattamente dove servirebbe.

Su questo progetto vale la regola che **si allenta solo dove c'e' un conto
che possa dire di no**. Questo e' il conto: un bind su tutte le interfacce
puo' stare in `mr_rao/portcheck.py` e in nessun altro file Python del
programma. E' piu' stretto della regola che sostituisce — CodeQL guarda una
volta a settimana, questo a ogni commit — e vive dove la ragione e' gia'
scritta.

La ragione, per intero: quel socket non serve niente a nessuno. Apre, guarda
se la porta e' libera e chiude subito. Non ascolta, non accetta connessioni,
non legge. L'unico modo di arrivarci con host largo e' aver scelto
`MR_RAO_HOST=0.0.0.0`, che e' l'opzione di esposizione dichiarata; e dalla
1.7.0 quella scelta non spegne piu' la difesa anti DNS-rebinding.
"""
from __future__ import annotations

import re
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent

#: L'unico file a cui e' concesso, e il motivo sta nel suo sorgente.
CONCESSO = "mr_rao/portcheck.py"

#: Le cartelle del programma. Fuori da queste non c'e' codice che gira.
CARTELLE = ("mr_rao", "scripts", ".")

#: `bind(("", n))` e `bind(("0.0.0.0", n))`: le due forme che significano
#: «tutte le interfacce». La seconda e' esplicita, la prima e' quella che
#: sfugge leggendo in fretta, perche' sembra un indirizzo vuoto.
_RE_BIND_LARGO = re.compile(
    r"""\.bind\(\s*\(\s*(?P<host>["']0\.0\.0\.0["']|["']["']|["']::["'])""",
)


def sorgenti_python() -> list[Path]:
    trovati: list[Path] = []
    for cartella in CARTELLE:
        base = RADICE / cartella
        if not base.is_dir():
            continue
        for f in base.glob("*.py" if cartella == "." else "**/*.py"):
            if "venv" in f.parts or "__pycache__" in f.parts:
                continue
            trovati.append(f)
    return trovati


def test_ci_sono_sorgenti_da_guardare():
    """Senza questo, il controllo sotto passerebbe su un elenco vuoto.

    E' il modo in cui questa prova diventerebbe verde per non aver guardato
    niente: basta che una cartella cambi nome.
    """
    file = sorgenti_python()
    assert len(file) >= 20, f"solo {len(file)} sorgenti trovati"
    assert any(f.as_posix().endswith(CONCESSO) for f in file), (
        f"{CONCESSO} non e' nell'elenco: il controllo sta guardando altrove"
    )


def test_il_bind_largo_sta_solo_dove_e_motivato():
    colpevoli: list[str] = []
    for f in sorgenti_python():
        relativo = f.relative_to(RADICE).as_posix()
        if relativo == CONCESSO:
            continue
        testo = f.read_text(encoding="utf-8", errors="replace")
        for m in _RE_BIND_LARGO.finditer(testo):
            riga = testo[: m.start()].count("\n") + 1
            colpevoli.append(f"{relativo}:{riga}")

    assert not colpevoli, (
        "bind su tutte le interfacce fuori da "
        f"{CONCESSO}: {colpevoli}.\n"
        "La regola CodeQL che lo segnalava e' esclusa in "
        "`.github/codeql/codeql-config.yml`, e quell'esclusione vale per "
        "tutto il repository: questo test e' cio' che la rende accettabile. "
        "Se il bind largo qui e' voluto, la decisione va presa e scritta, "
        "non fatta passare in silenzio."
    )


def test_il_controllo_sa_riconoscere_le_forme_che_cerca():
    """Un controllo che non trova mai niente non e' distinguibile da uno rotto.

    Qui si verifica sulle stringhe, non sui file: che le due forme del bind
    largo vengano riconosciute, e che quelle strette no.
    """
    for largo in [
        's.bind(("", porta))',
        's.bind(("0.0.0.0", 5000))',
        "s.bind(('::', 5000))",
        's.bind( ( "0.0.0.0" , 5000 ) )',
    ]:
        assert _RE_BIND_LARGO.search(largo), f"non riconosciuto: {largo}"

    for stretto in [
        's.bind(("127.0.0.1", 5000))',
        's.bind(("localhost", 5000))',
        "s.bind((host, porta))",
    ]:
        assert not _RE_BIND_LARGO.search(stretto), f"falso allarme su: {stretto}"
