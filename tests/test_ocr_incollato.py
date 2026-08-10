"""Quando l'OCR incolla il dato all'etichetta che lo precede.

Il difetto non e' stato immaginato: l'ha trovato il banco delle scansioni
(`scripts/bench_scansioni.py`), leggendo il testo che il motore OCR produce
davvero su carta degradata. Su quelle pagine il dato esce cosi':

    IBANIT60X0542811101000000123456      l'etichetta si attacca al valore
    Tel.02 1234567                       lo spazio dopo il punto sparisce
    ...3760000000000061                  i puntini di guida del modulo
    Carta di pagamento6011111111111174   di nuovo l'etichetta

In tutti questi casi il dato **passerebbe il proprio validatore** — il
mod-97 dell'IBAN e il Luhn della carta tornano, sono le stesse cifre di
prima — ma il riconoscitore non arriva nemmeno a proporlo: i lookbehind
`\\b`, `(?<![\\w.])` e `(?<![\\w.+])` lo rifiutano perche' e' preceduto da
una lettera o da un punto.

Il risultato e' la forma peggiore di errore per uno strumento che esiste
per non far uscire dati personali: il dato resta in chiaro, **e nessuno lo
dice**. Non una redazione mancata dichiarata, non un sospetto: silenzio.

La meta' che conta di questo file non sono i casi che ora funzionano, sono
i casi che devono continuare a non funzionare: qui sotto, dopo ogni
allentamento, c'e' il test che verifica che il dato debba comunque passare
la propria aritmetica. Il pattern propone, il validatore decide -- e se il
validatore smettesse di decidere, questi test diventerebbero rossi.
"""
from __future__ import annotations

import pytest

from aiuti import apply_privacy_filter  # segnaposto appiattiti: vedi tests/aiuti.py
from mr_rao.privacy import PrivacyOptions, only


# ---------------------------------------------------------------------------
# IBAN incollato all'etichetta
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "testo",
    [
        "IBANIT60X0542811101000000123456",
        "Il saldo va versato sul conto\nIBANIT52N0103003400000000777001",
        "Coordinate bancarieIT86O0200802016000000889977 per l'accredito",
        # la forma a gruppi di quattro, che le banche stampano cosi'
        "IBANIT98 U030 6901 6000 0001 2345 678",
    ],
)
def test_un_iban_incollato_a_una_parola_viene_sostituito(testo):
    out, report = apply_privacy_filter(testo, only("fiscal"))
    assert "{{IBAN}}" in out
    assert report.counts.get("iban", 0) == 1


def test_l_etichetta_resta_al_suo_posto():
    """Sparisce il dato, non la parola che lo introduce: un documento in cui
    sparisce anche «IBAN» non si legge piu'."""
    out, _ = apply_privacy_filter("IBANIT60X0542811101000000123456", only("fiscal"))
    assert out == "IBAN{{IBAN}}"


def test_un_iban_incollato_che_non_passa_il_mod97_resta():
    """Il presidio dell'allentamento.

    Se bastasse la forma, questo sparirebbe: ha la struttura giusta ed e'
    lungo giusto. A dire di no e' solo l'aritmetica. Se un giorno questo
    test diventasse verde, vorrebbe dire che il validatore non decide piu'.
    """
    testo = "IBANIT60X0542811101000000123457"
    out, report = apply_privacy_filter(testo, only("fiscal"))
    assert "{{IBAN}}" not in out
    assert report.counts.get("iban", 0) == 0


def test_un_iban_preceduto_da_cifre_non_viene_tagliato_a_meta():
    """Una lettera davanti e' un'etichetta incollata; una cifra davanti
    vuol dire che si sta entrando in mezzo a un numero piu' lungo, e la
    parte che si ritaglia non e' un campo."""
    testo = "Riferimento 99IT60X0542811101000000123456"
    out, report = apply_privacy_filter(testo, only("fiscal"))
    assert "{{IBAN}}" not in out
    assert report.counts.get("iban", 0) == 0


# ---------------------------------------------------------------------------
# Carta di pagamento: puntini di guida e etichetta incollata
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "testo",
    [
        "Carta di pagamento .....\n...3760000000000061",
        "Numero carta.........4539148803436467",
        "Carta di pagamento6011111111111174",
        "carta6011111111111174",
    ],
)
def test_una_carta_incollata_o_sui_puntini_viene_sostituita(testo):
    out, report = apply_privacy_filter(testo, only("fiscal"))
    assert "{{CARD}}" in out
    assert report.counts.get("cards", 0) == 1


def test_una_carta_che_non_passa_il_luhn_resta():
    out, report = apply_privacy_filter("...6011111111111175", only("fiscal"))
    assert "{{CARD}}" not in out
    assert report.counts.get("cards", 0) == 0


def test_la_coda_di_un_decimale_non_diventa_una_carta():
    """Il punto ammesso davanti alle cifre e' quello dei puntini di guida e
    delle abbreviazioni, non quello dei decimali: `123.4539148803436467`
    non e' una carta, e' la parte dopo la virgola di un numero."""
    testo = "Totale 123.4539148803436467 unita'"
    out, report = apply_privacy_filter(testo, only("fiscal"))
    assert "{{CARD}}" not in out
    assert report.counts.get("cards", 0) == 0


# ---------------------------------------------------------------------------
# Telefono attaccato al punto dell'abbreviazione
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "testo",
    [
        "Tel.02 1234567",
        "Tel...041 988776",
        "Cell.3391234567",
        "tel.02 1234567",
        "Fax.06 87654321",
    ],
)
def test_un_telefono_attaccato_all_abbreviazione_viene_sostituito(testo):
    out, report = apply_privacy_filter(testo, only("phones"))
    assert "{{PHONE}}" in out
    assert report.counts.get("phones", 0) == 1


def test_l_abbreviazione_resta_leggibile():
    out, _ = apply_privacy_filter("Tel.02 1234567", only("phones"))
    assert out == "Tel.{{PHONE}}"


def test_il_punto_e_ammesso_solo_dopo_una_parola_di_contatto():
    """Il telefono non ha un'aritmetica che lo confermi, quindi qui il
    lookbehind non e' stato allentato: e' stata aggiunta una regola che
    chiede **di piu'**, cioe' la parola di contatto prima del punto.

    Senza quella parola il punto resta un motivo per rifiutare, ed e'
    giusto: un punto davanti a delle cifre e' quasi sempre un decimale, una
    data o un numero di articolo.
    """
    for testo in (
        "Vedi art.02 1234567 del regolamento",
        "L'importo e' 1.234567 euro",
        "protocollo n.0212345670",
    ):
        out, report = apply_privacy_filter(testo, only("phones"))
        assert "{{PHONE}}" not in out, testo
        assert report.counts.get("phones", 0) == 0, testo


# ---------------------------------------------------------------------------
# L'invariante: rimettere lo spazio non deve cambiare niente
# ---------------------------------------------------------------------------

# A sinistra il testo come esce dall'OCR degradato, a destra lo stesso testo
# con lo spazio al posto suo. Sono la stessa pagina: la seconda e' cio' che
# il motore avrebbe visto se la scansione fosse stata buona.
INCOLLATO_E_STACCATO = [
    ("IBANIT60X0542811101000000123456", "IBAN IT60X0542811101000000123456"),
    ("IBANIT98 U030 6901 6000 0001 2345 678",
     "IBAN IT98 U030 6901 6000 0001 2345 678"),
    ("Carta di pagamento6011111111111174", "Carta di pagamento 6011111111111174"),
    ("Numero carta.........4539148803436467", "Numero carta 4539148803436467"),
    ("Tel.02 1234567", "Tel. 02 1234567"),
    ("Cell.3391234567", "Cell. 3391234567"),
    # E il contrario, che conta di piu': testo dove non c'e' niente da
    # togliere ne' attaccato ne' staccato.
    ("Protocollo n.0123456789", "Protocollo n. 0123456789"),
    ("Capitolo ...4004004004004004", "Capitolo 4004004004004004"),
    ("Delibera45 del Consiglio", "Delibera 45 del Consiglio"),
]


@pytest.mark.parametrize("incollato,staccato", INCOLLATO_E_STACCATO)
def test_incollato_non_e_mai_piu_permissivo_di_staccato(incollato, staccato):
    """Il metro dell'allentamento, e il modo in cui puo' dire di no.

    Lo spazio perso e' un difetto della scansione, non un'informazione: il
    motore deve arrivare **allo stesso esito** sulle due forme. Se la forma
    incollata sostituisse di piu' di quella staccata, vorrebbe dire che
    l'allentamento ha aperto una porta che sul testo pulito non esiste — ed
    e' esattamente cio' che questo test rende impossibile fare in silenzio.
    """
    opts = PrivacyOptions()
    _, rep_incollato = apply_privacy_filter(incollato, opts)
    _, rep_staccato = apply_privacy_filter(staccato, opts)
    assert rep_incollato.counts == rep_staccato.counts


# ---------------------------------------------------------------------------
# Il costo: i documenti dove non deve sparire niente
# ---------------------------------------------------------------------------

# Un modulo con dei puntini di guida, dei protocolli e degli importi: la
# popolazione su cui un lookbehind allentato si paga. Qui la risposta
# giusta e' zero.
MODULO_IN_BIANCO = """RICHIESTA DI RIMBORSO SPESE - MODULO R4

Protocollo n.0123456789 del 01.02.2024
Riferimento pratica .....2024118000000
Delibera 45, versione 3.10, quadro RN numero 1234567890123456
Importo complessivo 1.234567 (in migliaia)
Codice Identificativo Gara 1234567890AB
Capitolo di bilancio ...4004004004004004
"""


def test_un_modulo_in_bianco_non_perde_una_riga():
    out, report = apply_privacy_filter(MODULO_IN_BIANCO, PrivacyOptions())
    assert report.total == 0, report.to_dict()
    assert out == MODULO_IN_BIANCO
