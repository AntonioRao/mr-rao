# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Il confronto prima/dopo deve rimpicciolirsi sugli schermi bassi.

`renderDiff()` scriveva l'aspetto del confronto dentro l'attributo `style`:
uno stile in linea batte qualsiasi media query, quindi il riquadro del testo
originale restava alto 240px anche a schermo basso -- proprio nella scheda
che secondo i nostri documenti e' «il controllo che conta».

Misurato su Chrome a 812x375 (telefono girato) prima della correzione: il
riquadro che contiene tutto il confronto era alto 232.6px e il solo testo
originale ne chiedeva 240, cioe' piu' della scatola che lo conteneva.

Qui non si controlla l'aspetto -- quello si guarda -- ma il meccanismo: che
l'aspetto stia in CSS e che il media query lo possa ancora cambiare. Un
`style=` rimesso in `renderDiff()` non lo vedrebbe nessuno finche' qualcuno
non apre la pagina su uno schermo basso.
"""

from __future__ import annotations

import re
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
JS = (RADICE / "static" / "js" / "app.js").read_text(encoding="utf-8")
CSS = (RADICE / "static" / "css" / "app.css").read_text(encoding="utf-8")


def corpo(nome: str) -> str:
    """Il corpo della funzione JS `nome`, contando le graffe."""
    inizio = JS.index(f"function {nome}(")
    apertura = JS.index("{", inizio)
    livello = 0
    for i in range(apertura, len(JS)):
        if JS[i] == "{":
            livello += 1
        elif JS[i] == "}":
            livello -= 1
            if livello == 0:
                return JS[apertura : i + 1]
    raise AssertionError(f"graffe sbilanciate in {nome}()")


def blocco_media(condizione: str) -> tuple[str, int]:
    """Il contenuto del blocco `@media <condizione>` e dove comincia."""
    testa = f"@media {condizione}"
    inizio = CSS.index(testa)
    apertura = CSS.index("{", inizio)
    livello = 0
    for i in range(apertura, len(CSS)):
        if CSS[i] == "{":
            livello += 1
        elif CSS[i] == "}":
            livello -= 1
            if livello == 0:
                return CSS[apertura : i + 1], inizio
    raise AssertionError(f"graffe sbilanciate in {testa}")


def test_render_diff_non_scrive_stili_in_linea():
    corpo_diff = corpo("renderDiff")
    assert "class=" in corpo_diff, "il confronto non usa piu' classi: controllo morto"
    assert 'style="' not in corpo_diff, (
        "renderDiff() e' tornata a scrivere stili in linea: vincono sui media "
        "query e il confronto non si adatta piu' agli schermi bassi"
    )


def test_nessuno_stile_in_linea_nel_js_della_pagina():
    """Gli stili in linea rimasti sono solo quelli calcolati a runtime
    (`element.style.left = ...`), che in CSS non si possono scrivere."""
    assert 'style="' not in JS, "in app.js e' ricomparso un attributo style="


def regola_base() -> re.Match[str]:
    """La regola fuori dai media query che fissa l'altezza dell'originale."""
    trovata = re.search(r"\.diff-originale\s*\{[^}]*max-height:\s*240px[^}]*\}", CSS)
    assert trovata, "manca la regola .diff-originale con max-height: 240px"
    return trovata


def test_il_testo_originale_ha_la_sua_classe_e_la_sua_altezza():
    assert 'class="diff-originale"' in JS, "il <pre> originale ha perso la classe"
    # 240px e' l'altezza che aveva quando stava in linea: a viewport normale
    # la pagina deve restare quella di prima.
    regola_base()


def test_lo_schermo_basso_puo_rimpicciolire_l_originale():
    blocco, dove_media = blocco_media("(max-height: 640px)")
    assert ".diff-originale" in blocco, (
        "a schermo basso il testo originale resta alto quanto a schermo intero: "
        "dentro un riquadro da 62vh si mangia lo spazio del testo ripulito"
    )
    riga = re.search(r"\.diff-originale\s*\{([^}]*)\}", blocco)
    assert riga and "max-height" in riga.group(1)

    # Stessa specificita': vince chi viene dopo. Se la regola base scivolasse
    # in fondo al foglio il media query smetterebbe di contare, in silenzio.
    assert regola_base().start() < dove_media, (
        "la regola base di .diff-originale sta dopo il media query: lo annulla"
    )
    assert "!important" not in blocco, "se serve !important, l'ordine e' sbagliato"
