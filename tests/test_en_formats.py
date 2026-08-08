"""I validatori del pacchetto EN, e quanto valgono davvero.

I vettori stanno accanto alle funzioni, in `mr_rao/en_formats.py`: sono la
documentazione dell'algoritmo, non solo la sua prova. Qui li si esegue
sotto pytest, cosi' il gate se ne accorge insieme a tutto il resto.

La seconda meta' di questo file e' piu' importante della prima. Un
validatore si guarda per quello che **rifiuta**, non per quello che
accetta: `ssn_ok` supera ogni vettore scritto per lui e lascia comunque
passare quasi nove sequenze casuali di cifre su dieci, perche' il SSN non
ha alcun checksum. Chiamarlo «validatore» e usarlo come si usa il mod-97
dell'IBAN produrrebbe un motore che redige numeri di protocollo. I test
sulla capacita' di discriminare esistono per impedire che qualcuno --
compreso io fra sei mesi -- lo scambi per quello che non e'.
"""
from __future__ import annotations

import random

import pytest

from mr_rao import en_formats
from mr_rao.en_formats import BANCO


def _casi():
    for nome, funzione, vettori in BANCO:
        for valore, atteso, provenienza in vettori:
            yield pytest.param(
                funzione, valore, atteso, provenienza, id=f"{nome}-{valore}"
            )


@pytest.mark.parametrize("funzione,valore,atteso,provenienza", list(_casi()))
def test_vettore(funzione, valore, atteso, provenienza):
    assert funzione(valore) is atteso, provenienza


def test_ogni_validatore_ha_i_suoi_vettori():
    """Una funzione senza vettori passa il banco per il motivo sbagliato.

    Chi aggiunge un validatore e si dimentica i vettori non vedrebbe
    niente di rosso: semplicemente non verrebbe provato.
    """
    nel_banco = {nome for nome, _, _ in BANCO}
    pubbliche = {
        n for n in dir(en_formats)
        if n.endswith("_ok") and not n.startswith("_")
    }
    assert pubbliche == nel_banco, f"senza vettori: {sorted(pubbliche - nel_banco)}"


def test_ogni_validatore_ha_almeno_un_vettore_negativo():
    """Un banco di soli casi validi non dimostra che sappia dire di no."""
    for nome, _, vettori in BANCO:
        assert any(atteso is False for _, atteso, _ in vettori), nome


# ---------------------------------------------------------------------------
# Quanto discriminano davvero
# ---------------------------------------------------------------------------

# Percentuale massima di sequenze casuali che ogni funzione puo' accettare.
# I valori sono misurati, non desiderati: servono a fissare la differenza
# fra un validatore aritmetico e un filtro di forma, e a farla notare se
# qualcuno cambia un'implementazione credendo di correggerla.
SOGLIE = {
    "abn_ok": (9, 0.03),               # mod-89: il piu' selettivo
    "aba_routing_ok": (9, 0.08),       # 3-7-1 mod-10 piu' intervalli di prefisso
    "itin_ok": (9, 0.09),
    "sin_ok": (9, 0.13),               # Luhn su nove cifre
    "tfn_ok": (9, 0.14),
    "nhs_number_ok": (10, 0.14),       # mod-11: una su undici, piu' il resto 10
}

# Questi due **non sono validatori**, e il test lo mette nero su bianco.
# Sostituirci sopra senza una parola di contesto accanto vorrebbe dire
# redigere numeri di protocollo, codici articolo e riferimenti di fattura.
NON_VALIDATORI = {
    "ssn_ok": (9, 0.50),
    "nanp_phone_ok": (10, 0.30),
}


def _quota_accettata(funzione, cifre: int, campioni: int = 20000) -> float:
    # Seme fisso: un banco che cambia risposta a ogni esecuzione non serve
    # a decidere niente.
    rng = random.Random(20260808)
    passati = sum(
        1 for _ in range(campioni)
        if funzione("".join(rng.choice("0123456789") for _ in range(cifre)))
    )
    return passati / campioni


@pytest.mark.parametrize("nome,cifre,massimo", [(n, c, m) for n, (c, m) in SOGLIE.items()])
def test_i_validatori_veri_rifiutano_quasi_tutto(nome, cifre, massimo):
    quota = _quota_accettata(getattr(en_formats, nome), cifre)
    assert quota <= massimo, f"{nome} accetta il {quota:.1%} delle cifre casuali"


@pytest.mark.parametrize(
    "nome,cifre,minimo", [(n, c, m) for n, (c, m) in NON_VALIDATORI.items()]
)
def test_i_filtri_di_forma_non_sono_validatori(nome, cifre, minimo):
    """Test scritto al contrario, di proposito.

    Pretende che questi due lascino passare **molto**. Se un giorno uno di
    loro diventasse selettivo vorrebbe dire che qualcuno ha aggiunto una
    regola inventata: nessun ente ha pubblicato un checksum per il SSN o
    per i numeri NANP. Meglio che si rompa qui, dove c'e' scritto perche'.
    """
    quota = _quota_accettata(getattr(en_formats, nome), cifre)
    assert quota >= minimo, (
        f"{nome} ora accetta solo il {quota:.1%}: se e' stato aggiunto un "
        "controllo, verificare che esista davvero e non sia stato dedotto"
    )
