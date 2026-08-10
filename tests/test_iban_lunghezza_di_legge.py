"""L'IBAN si taglia dove dice il registro, non dove finisce di indovinare.

Il difetto che questo test blocca
---------------------------------

Il pattern degli IBAN spaziati non sa dove finisce il numero: conta gruppi.
Pretendeva **almeno due caratteri per gruppo**, e un IBAN si stampa a gruppi
di quattro -- quindi quando la lunghezza non e' divisibile per quattro
l'ultimo gruppo puo' essere di un carattere solo:

    PT92 DO9G MNU7 7VTU UJ59 6LGU A

Su quella forma non veniva riconosciuto **niente**. Non un troncamento: un
silenzio. Il rapporto diceva zero IBAN su un documento che ne conteneva uno,
e chi lo rileggeva non aveva modo di accorgersene. Colpiva tutti i Paesi la
cui lunghezza da' resto 1 -- Portogallo e Svizzera (25 e 21), Croazia,
Brasile, Ucraina, Qatar, Palestina, Sao Tome.

La correzione, e perche' e' sicura
-----------------------------------

Il pattern ora ammette gruppi da un carattere, quindi e' piu' goloso. Va
bene **perche' adesso c'e' chi lo taglia**: `_prefisso_a_norma` riduce il
candidato alla lunghezza che il registro ISO 13616 prescrive per il suo
Paese, e il di piu' torna al testo. La lunghezza di un IBAN non e'
un'opinione, quindi la golosita' non costa niente.

Cosa misura questo file
-----------------------

**Tutti** i Paesi del registro, con IBAN costruiti qui -- corpo casuale e
cifre di controllo calcolate -- e non un elenco di esempi scelti a mano.
Un elenco scritto a mano avrebbe contenuto l'Italia, la Germania e la
Francia, cioe' proprio i Paesi in cui il difetto non si vedeva.

Il testo intorno e' fatto di caratteri **non alfanumerici** apposta: con
una frase normale, l'ultimo gruppo di un carattere («A») comparirebbe per
caso dentro una parola qualsiasi, e il controllo direbbe «coda in chiaro»
su un motore che ha funzionato. E' successo mentre scrivevo questo test.
"""

from __future__ import annotations

import random
import string

import pytest

from mr_rao.privacy import (
    _IBAN_LUNGHEZZE,
    PrivacyOptions,
    apply_privacy_filter,
    iban_checksum_ok,
    senza_numeri,
)

ALFABETO = string.digits + string.ascii_uppercase
SEMI = (1, 7, 42, 99, 2024)


def iban_valido(paese: str, generatore: random.Random) -> str:
    """Un IBAN di quel Paese, con le cifre di controllo calcolate.

    Costruito e non copiato: un IBAN vero preso da un documento sarebbe un
    dato bancario reale, e in questo progetto non entrano.
    """
    corpo = "".join(generatore.choice(ALFABETO) for _ in range(_IBAN_LUNGHEZZE[paese] - 4))
    grezzo = paese + "00" + corpo
    numerico = "".join(str(int(c, 36)) for c in (grezzo[4:] + grezzo[:4]))
    return paese + f"{98 - int(numerico) % 97:02d}" + corpo


def a_gruppi(iban: str) -> str:
    return " ".join(iban[i : i + 4] for i in range(0, len(iban), 4))


@pytest.mark.parametrize("paese", sorted(_IBAN_LUNGHEZZE))
@pytest.mark.parametrize("seme", SEMI)
def test_ogni_paese_riconosciuto_per_intero(paese: str, seme: int) -> None:
    iban = iban_valido(paese, random.Random(f"{paese}{seme}"))
    assert iban_checksum_ok(iban), "il generatore di questo test e' rotto, non il motore"
    # Delimitatori non alfanumerici: vedi il perche' nella docstring.
    fuori, _ = apply_privacy_filter(f"<<< {a_gruppi(iban)} >>>", PrivacyOptions())
    assert senza_numeri(fuori) == "<<< {{IBAN}} >>>", (
        f"IBAN {paese} di {_IBAN_LUNGHEZZE[paese]} caratteri "
        f"(resto {_IBAN_LUNGHEZZE[paese] % 4} diviso 4): il segnaposto non ha "
        f"coperto tutto il numero"
    )


def test_l_ultimo_gruppo_di_un_carattere_e_il_caso_che_rompeva() -> None:
    """La forma esatta del difetto, scritta per esteso.

    Il test parametrico sopra la copre gia', ma copre anche 74 Paesi in cui
    non c'era niente da rompere: se un giorno qualcuno restringe di nuovo il
    pattern, questo dice in una riga cosa e' andato perduto.
    """
    a_resto_uno = [p for p, L in _IBAN_LUNGHEZZE.items() if L % 4 == 1]
    assert a_resto_uno, "il registro non ha piu' Paesi con lunghezza a resto 1?"
    for paese in a_resto_uno:
        iban = iban_valido(paese, random.Random(paese))
        gruppi = a_gruppi(iban).split()
        assert len(gruppi[-1]) == 1, f"{paese}: l'ultimo gruppo dovrebbe essere di 1 carattere"
        fuori, rapporto = apply_privacy_filter(f"<<< {a_gruppi(iban)} >>>", PrivacyOptions())
        assert senza_numeri(fuori) == "<<< {{IBAN}} >>>", f"{paese} non riconosciuto"
        assert rapporto.to_dict()["counts"].get("iban") == 1


def test_quello_che_il_pattern_prende_in_piu_torna_al_testo() -> None:
    """Il taglio a norma non deve mangiarsi la parola dopo.

    E' l'altra meta' della correzione: il pattern e' goloso apposta, quindi
    va provato che cio' che prende oltre la lunghezza di legge venga
    restituito invece di sparire dentro il segnaposto.
    """
    casi = [
        ("IBAN IT60 X054 2811 1010 0000 0123 456 SWIFT BCITITMM",
         "IBAN {{IBAN}} SWIFT BCITITMM"),
        ("Conto DE89 3704 0044 0532 0130 00 presso Deutsche Bank",
         "Conto {{IBAN}} presso Deutsche Bank"),
    ]
    for dentro, atteso in casi:
        assert senza_numeri(apply_privacy_filter(dentro, PrivacyOptions())[0]) == atteso


def test_i_separatori_ammessi_dal_pattern_li_conosce_anche_il_validatore() -> None:
    """Il difetto che nasce quando due punti del motore non sono d'accordo.

    `_RE_IBAN_SPAZIATO` accetta spazio, trattino e un a-capo. Fino alla
    1.20.0 `iban_checksum_ok` toglieva **il solo spazio**: un IBAN scritto
    col trattino arrivava fino al mod-97 con i trattini dentro, la lunghezza
    non tornava, e veniva scartato in silenzio -- il rapporto diceva zero
    IBAN su un documento che ne conteneva uno.

    Non e' un caso di scuola: il trattino era ammesso dal pattern **da
    sempre**, quindi quella forma non ha mai funzionato e nessun test se ne
    era accorto, perche' tutti usavano gli spazi.
    """
    iban = iban_valido("IT", random.Random("separatori"))
    gruppi = a_gruppi(iban).split()
    forme = {
        "spazio": " ".join(gruppi),
        "trattino": "-".join(gruppi),
        "misto": gruppi[0] + " " + "-".join(gruppi[1:]),
        # L'a-capo dell'estrattore: su una carta intestata o una fattura
        # l'IBAN viene mandato a capo come qualunque altra riga.
        "a-capo": " ".join(gruppi[:3]) + "\n" + " ".join(gruppi[3:]),
    }
    for nome, forma in forme.items():
        fuori, _ = apply_privacy_filter(f"<<< {forma} >>>", PrivacyOptions())
        assert senza_numeri(fuori) == "<<< {{IBAN}} >>>", f"forma «{nome}»: {fuori!r}"


def test_due_a_capo_sono_una_colonna_di_tabella_non_un_iban() -> None:
    """Il limite che tiene onesta la concessione qui sopra.

    Un IBAN va a capo una volta; una colonna di codici in tabella va a capo
    a ogni cella. Con l'a-capo libero, due codici diversi su due righe
    diventerebbero un candidato solo: il mod-97 lo boccia, e l'IBAN vero
    resta in chiaro. La solita sconfitta silenziosa, presa dal verso
    sbagliato.
    """
    iban = iban_valido("IT", random.Random("colonna"))
    gruppi = a_gruppi(iban).split()
    spezzato = " ".join(gruppi[:2]) + "\n" + " ".join(gruppi[2:4]) + "\n" + " ".join(gruppi[4:])
    fuori, _ = apply_privacy_filter(spezzato, PrivacyOptions())
    assert "{{IBAN" not in fuori


def test_un_codice_paese_inventato_non_e_un_iban() -> None:
    """`_prefisso_a_norma` rifiuta prima del mod-97, e deve restare cosi'.

    Un codice Paese fuori registro non e' un IBAN: dirlo senza aritmetica
    e' piu' economico **e** piu' sicuro, perche' il mod-97 su una lunghezza
    sbagliata e' una lotteria a 1 su 97.
    """
    frase = "<<< ZZ00 1234 5678 9012 3456 7890 >>>"
    assert apply_privacy_filter(frase, PrivacyOptions())[0] == frase
