# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Non una cornice diversa: un valore diverso.

Perche' questo file esiste
--------------------------

Il banco delle forme misurava lo **stesso dato** scritto in posti diversi, e
diceva 100%. Non era una buona notizia: usava un solo valore per tipo.
Dimostrava che le cornici funzionano, non che i riconoscitori reggano la
varieta' dei valori veri.

Girando l'altra manopola — centinaia di valori distinti per tipo, tutti
validi — sono usciti **due difetti** che nessun test vedeva, ed erano
entrambi casi italiani ordinari:

1. **Il codice fiscale con omocodia.** Quando due persone otterrebbero lo
   stesso codice, l'Agenzia delle Entrate sostituisce alcune cifre con le
   lettere L M N P Q R S T U V. Sono codici veri di persone vere, emessi
   regolarmente. Su 300 campioni: **zero riconosciuti**, il 40% perso in
   silenzio.

2. **Il telefono con la barra**, `Tel. 011/7323929`: la forma standard delle
   carte intestate italiane. Su 300 numeri: **zero riconosciuti**, mentre
   gli stessi numeri con lo spazio o il trattino venivano presi. Non era una
   scelta, era una dimenticanza nell'elenco dei separatori.

Il banco completo e' `scripts/bench_varieta.py`. Qui restano i casi che
devono restare verdi a ogni commit, e le due guardie sul costo.
"""
from __future__ import annotations

import random
import string
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from aiuti import apply_privacy_filter  # noqa: E402  (vedi tests/aiuti.py)
from mr_rao.privacy import (  # noqa: E402
    _RE_CF_OMOCODIA,
    PrivacyOptions,
    cf_check_char_ok,
    only,
)

# ---------------------------------------------------------------------------
# Il carattere di controllo, calcolato qui: chiedere al motore quale sia il
# valore giusto renderebbe impossibile scoprire che il motore sbaglia.
# ---------------------------------------------------------------------------

_DISPARI = dict(zip(
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    [1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 1, 0, 5, 7, 9, 13, 15, 17, 19, 21,
     2, 4, 18, 20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23]))
_PARI = dict(zip("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                 list(range(10)) + list(range(26))))
_OMOCODIA = dict(zip("0123456789", "LMNPQRSTUV"))


def cf_valido(base15: str) -> str:
    s = sum(_DISPARI[c] if i % 2 == 0 else _PARI[c]
            for i, c in enumerate(base15.upper()))
    return base15.upper() + chr(ord("A") + s % 26)


def con_omocodia(base15: str, quante: int) -> str:
    """Sostituisce le ultime `quante` cifre con le lettere dell'Agenzia."""
    posizioni = [i for i, c in enumerate(base15) if c.isdigit()]
    fuori = base15
    for i in reversed(posizioni[-quante:]):
        fuori = fuori[:i] + _OMOCODIA[fuori[i]] + fuori[i + 1:]
    return cf_valido(fuori)


@pytest.mark.parametrize("quante", [1, 2, 3, 5])
def test_il_codice_fiscale_con_omocodia_viene_tolto(quante):
    """Il caso per cui il pattern dell'omocodia esiste."""
    codice = con_omocodia("RSSMRA85T10A562", quante)
    testo = f"codice fiscale {codice} del contribuente"
    fuori, rep = apply_privacy_filter(testo, only("fiscal"))
    assert "{{CODICE_FISCALE}}" in fuori, f"{codice} non riconosciuto: {fuori}"
    assert codice not in fuori


def test_l_omocodia_pretende_che_il_conto_torni():
    """La differenza col pattern stretto, ed e' deliberata.

    Il riconoscitore normale sostituisce anche quando il carattere di
    controllo non torna: su un dato personale l'errore va fatto nella
    direzione prudente. Questo no. Ammettendo lettere dove il codice vuole
    cifre la forma diventa quasi una parola qualsiasi di sedici caratteri, e
    senza l'aritmetica a smentirla si redigerebbe mezzo documento.
    """
    buono = con_omocodia("RSSMRA85T10A562", 2)
    # Stessa forma, ultimo carattere cambiato: il conto non torna piu'.
    cattivo = buono[:-1] + ("B" if buono[-1] != "B" else "C")
    assert cf_check_char_ok(buono)
    assert not cf_check_char_ok(cattivo)

    fuori, _ = apply_privacy_filter(f"riferimento {cattivo} in atti", only("fiscal"))
    assert cattivo in fuori, "un codice con l'omocodia e il conto sbagliato non va toccato"


def test_il_filtro_aritmetico_respinge_quasi_tutto():
    """Quanto vale davvero il carattere di controllo, misurato.

    Il pattern dell'omocodia e' permissivo per costruzione: e' il conto a
    reggere il peso. Qui si generano token che hanno **gia'** la forma
    esatta — il caso peggiore possibile — e si guarda quanti ne passano.
    Il valore atteso e' 1 su 26, cioe' il 3,85%: se salisse molto sopra,
    qualcuno avrebbe indebolito il controllo senza accorgersene.
    """
    rng = random.Random(20260809)
    lettere = string.ascii_uppercase
    mesi = "ABCDEHLMPRST"
    om = "0123456789LMNPQRSTUV"
    n = 20000
    proposti = accettati = 0
    for _ in range(n):
        tok = ("".join(rng.choice(lettere) for _ in range(6))
               + "".join(rng.choice(om) for _ in range(2))
               + rng.choice(mesi)
               + "".join(rng.choice(om) for _ in range(2))
               + rng.choice(lettere)
               + "".join(rng.choice(om) for _ in range(3))
               + rng.choice(lettere))
        if _RE_CF_OMOCODIA.fullmatch(tok):
            proposti += 1
            if cf_check_char_ok(tok):
                accettati += 1
    assert proposti == n, "il generatore non sta producendo la forma giusta"
    quota = accettati / proposti
    assert 0.02 < quota < 0.07, (
        f"il conto accetta il {100*quota:.2f}% dei candidati: l'atteso e' "
        f"il 3,85% (1 su 26). Fuori da questa forbice, il controllo e' "
        f"cambiato"
    )


@pytest.mark.parametrize("testo", [
    "tel. 011/7323929",
    "Tel. 02/46276058",
    "centralino 0121/123456",
    "fax 06/12345678",
    "+39 011/7323929",
])
def test_il_telefono_con_la_barra_viene_tolto(testo):
    """La forma standard delle carte intestate italiane."""
    fuori, _ = apply_privacy_filter(testo, only("phones"))
    assert "{{PHONE}}" in fuori, fuori


@pytest.mark.parametrize("testo", [
    "punti 315 316 317 318 319 / Ritenuta operata",
    "Registrata il 01/02/2024 al protocollo",
    "il numero 011/7323929 senza parola davanti",
    "delibera 12/2024 del 3/4/2025",
])
def test_la_barra_da_sola_non_basta(testo):
    """Il prezzo dell'apertura, e la ragione per cui e' quello giusto.

    Un recapito non ha nessuna aritmetica che possa smentirne la forma —
    e' la stessa ragione per cui in P3.7 i telefoni non sono stati
    allentati come IBAN e carte. Quindi la barra costa una parola di
    contatto.

    Misurato: ammettendola senza condizioni, su 3,3 milioni di caratteri di
    moduli fiscali comparivano 2 sostituzioni sbagliate — numerazioni di
    colonne che la barra saldava in un numero unico. Con la parola di
    contatto il costo torna a zero.
    """
    fuori, _ = apply_privacy_filter(testo, only("phones"))
    assert "{{PHONE}}" not in fuori, fuori


def test_le_date_con_la_barra_restano_date():
    """`_RE_DATELIKE` e' stato esteso alla barra nella stessa passata.

    Non e' un di piu': `01/02/2024` e' la forma piu' comune di data in
    italiano, e ammettere la barra fra i separatori di un recapito senza
    ammetterla nella guardia avrebbe trasformato ogni data in un telefono.
    """
    testo = "tel. 011/7323929 — riunione del 01/02/2024 e del 15/03/2026"
    fuori, _ = apply_privacy_filter(testo, only("phones"))
    assert "01/02/2024" in fuori
    assert "15/03/2026" in fuori
    assert "{{PHONE}}" in fuori


def test_i_valori_diversi_dello_stesso_tipo_si_comportano_uguale():
    """La domanda che ha trovato i due difetti: cambia il valore, non la frase.

    Non e' una ripetizione dei test qui sopra: quelli guardano casi scelti,
    questo guarda che non ci sia un valore particolare che sfugge.
    """
    rng = random.Random(20260809)
    for _ in range(50):
        cin = rng.choice(string.ascii_uppercase)
        abi = f"{rng.randint(1, 99999):05d}"
        cab = f"{rng.randint(1, 99999):05d}"
        conto = f"{rng.randint(0, 10**12 - 1):012d}"
        bban = cin + abi + cab + conto
        num = "".join(str(ord(c) - 55) if c.isalpha() else c
                      for c in bban + "IT00")
        iban = f"IT{98 - int(num) % 97:02d}{bban}"
        fuori, _ = apply_privacy_filter(f"IBAN {iban}", only("fiscal"))
        assert "{{IBAN}}" in fuori, f"{iban} non riconosciuto"
