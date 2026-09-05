# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Quanti cognomi dice la documentazione, contro quanti ce ne sono davvero.

Trovato il 05/09/2026 controllando la landing di Impresa: diceva «2 181
cognomi», e `mr_rao.it_names.SURNAMES` ne contiene 2266. Il commit
`ce431a5` («Ottantacinque cognomi composti in piu' negli elenchi») aveva
aggiunto 85 voci -- 2181 + 85 = 2266, il conto torna -- e nessun documento
lo sapeva: non e' un tema che il gate di `check_docs.py` guarda, perche'
quello confronta versioni e conteggi di test, non le dimensioni degli
elenchi linguistici.

`docs/MR-RAO-PLUS.md` diceva lo stesso numero vecchio, con lo stesso motivo:
e' descritto come limite dell'estensione, che porta una copia dell'elenco.

Questo file non copre quella copia -- vive in un altro repository -- ma
tiene allineate le **due** citazioni che stanno qui.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from mr_rao.it_names import SURNAMES  # noqa: E402

# Un numero con un separatore delle migliaia -- spazio, NBSP o l'entita'
# `&nbsp;` scritta a mano -- diventa un numero solo quando il separatore sta
# **fra due cifre**: cosi' non si rischia di fondere un numero con quello di
# una frase precedente che finisce per caso appena prima.
_RE_SEPARATORE_MIGLIAIA = re.compile(r"(?<=\d)(?:&nbsp;| |\s)+(?=\d)")
_RE_COGNOMI = re.compile(r"(\d+)\s*cognomi")

FILE = (
    RADICE / "docs" / "MR-RAO-PLUS.md",
    RADICE / "docs" / "landing" / "publish" / "impresa" / "index.html",
)


def test_i_cognomi_dichiarati_sono_quelli_veri():
    reale = len(SURNAMES)
    sbagliati: list[str] = []
    for percorso in FILE:
        testo = _RE_SEPARATORE_MIGLIAIA.sub("", percorso.read_text(encoding="utf-8"))
        trovati = _RE_COGNOMI.findall(testo)
        if not trovati:
            sbagliati.append(
                f"{percorso.relative_to(RADICE).as_posix()}: non parla piu' di "
                "cognomi. Se la frase e' cambiata aggiorna questo controllo, "
                "altrimenti non puo' piu' fallire"
            )
            continue
        sbagliati += [
            f"{percorso.relative_to(RADICE).as_posix()}: dice {n} cognomi, ma "
            f"SURNAMES ne ha {reale}"
            for n in trovati
            if n != str(reale)
        ]
    assert sbagliati == [], "\n  " + "\n  ".join(sbagliati)
