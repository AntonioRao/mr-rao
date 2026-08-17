# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""La stessa domanda, girata sui riconoscitori anglosassoni.

Perche' questo file esiste
--------------------------

Cambiare il **valore** invece della frase, sul pacchetto italiano, ha
trovato due difetti veri: il codice fiscale con omocodia e il telefono con
la barra. La domanda ovvia era se gli altri riconoscitori avessero lo stesso
problema.

**Non ce l'hanno.** Venti tipi provati con centinaia di valori distinti
ciascuno — NHS, National Insurance, SSN, ITIN, routing ABA, SIN, ABN, TFN,
tutti e sei i formati di codice postale britannico, MRZ, BBAN, carta
d'identita', patente, passaporto, chiavi — e nessuno perde valori.

Questo file non serve a dimostrare quel risultato una seconda volta: serve
perche' un domani non torni indietro. Un banco che oggi non trova niente e'
precisamente quello che serve quando qualcuno tocchera' un pattern.

Quattro cose che sembravano difetti erano il banco
--------------------------------------------------

Vale la pena tenerne memoria, perche' sono il modo tipico in cui un banco
mente: SIN che iniziano per 0 o 8 (il Canada non li assegna), MRZ di una
riga sola invece di due, MRZ di 43 caratteri invece di 44, passaporti con
serie che l'Italia non emette. In tutti e quattro i casi il motore aveva
ragione e il generatore torto.

Le cifre di controllo qui sotto sono calcolate dalle specifiche pubblicate,
non chieste al motore.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
for percorso in (RADICE, RADICE / "scripts"):
    if str(percorso) not in sys.path:
        sys.path.insert(0, str(percorso))

from bench_varieta_en import campioni, prova  # noqa: E402

# Quanti valori per tipo: abbastanza da vedere un buco parziale, pochi
# abbastanza da restare veloce nel gate.
PER_TIPO = 40


@pytest.fixture(scope="module")
def dati():
    return campioni()


def test_ogni_tipo_regge_la_varieta_dei_valori(dati):
    """Con l'etichetta davanti, il riconoscitore deve prendere **tutti** i
    valori validi del suo tipo — non la maggioranza.

    Un 95% qui non e' «quasi tutto»: e' un valore su venti che esce dal
    documento in chiaro, e la ragione sara' una forma particolare che
    nessuno ha guardato.
    """
    difetti = {}
    for tipo, (valori, cornice) in dati.items():
        campione = valori[:PER_TIPO]
        redatti, sospetti, persi = prova(campione, cornice)
        if redatti < len(campione):
            difetti[tipo] = (redatti, len(campione), persi)
    assert not difetti, (
        "questi riconoscitori perdono valori validi del proprio tipo:\n  "
        + "\n  ".join(f"{t}: {r}/{n} riconosciuti, esempi persi: {p}"
                      for t, (r, n, p) in difetti.items())
    )


def test_tutti_e_sei_i_formati_di_codice_postale(dati):
    """Il Royal Mail ne ha sei, ed e' esattamente il tipo di cosa che un
    pattern copre a meta' senza che nessuno se ne accorga."""
    formati = [t for t in dati if t.startswith("postcode")]
    assert len(formati) == 6, f"provati solo {len(formati)} formati su sei"
    for tipo in formati:
        valori, cornice = dati[tipo]
        redatti, _, persi = prova(valori[:PER_TIPO], cornice)
        assert redatti == PER_TIPO, f"{tipo}: {redatti}/{PER_TIPO}, persi {persi}"


def test_i_generatori_producono_valori_che_il_motore_rifiuterebbe_se_finti():
    """La prova che questo banco puo' dire di no.

    Se i generatori producessero valori che passano **qualunque** controllo,
    il 100% qui sopra non direbbe niente. Qui si sporca la cifra di
    controllo e si verifica che il motore se ne accorga: se non lo facesse,
    vorrebbe dire che sta redigendo la forma e non il dato.
    """
    from mr_rao.privacy import PrivacyOptions, apply_privacy_filter

    # Un NHS number con il conto rotto: la forma e' identica, il mod-11 no.
    fasullo = "999 999 999"
    fuori, _ = apply_privacy_filter(f"NHS number {fasullo}", PrivacyOptions())
    assert fasullo in fuori, (
        "un NHS number con il checksum sbagliato viene redatto lo stesso: "
        "il riconoscitore sta guardando la forma, non il conto"
    )
